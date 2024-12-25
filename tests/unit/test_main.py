"""Unit tests for the main module."""

import json
import signal
import sys
from pathlib import Path
from types import FrameType
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Import the module to ensure coverage is tracked
from mcp_server_neurolorap.__main__ import (
    ClinesConfig,
    configure_cline,
    handle_shutdown,
    main,
    main_entry,
)


@pytest.fixture
def mock_config_path(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary config path."""
    config_path = tmp_path / "cline_mcp_settings.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    mock_home = Mock()
    mock_home.return_value = tmp_path.parent
    with patch("mcp_server_neurolorap.__main__.Path.home", mock_home):
        yield config_path


@pytest.fixture
def mock_project_root(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary project root."""
    project_path = tmp_path / "src" / "mcp_server_neurolorap"
    project_path.mkdir(parents=True, exist_ok=True)
    main_file = project_path / "__main__.py"
    main_file.touch()

    def mock_path_factory(*args: str, **kwargs: str) -> MagicMock:
        mock_instance = MagicMock(spec=Path)
        mock_instance.resolve.return_value = main_file
        mock_instance.parent.parent.parent = tmp_path
        # Configure __str__ as a property
        mock_instance.configure_mock(**{"__str__": str(main_file)})
        return mock_instance

    mock_path = MagicMock()
    mock_path.side_effect = mock_path_factory

    with patch("mcp_server_neurolorap.__main__.Path", mock_path):
        yield tmp_path


def test_handle_shutdown() -> None:
    """Test shutdown signal handler."""
    frame = Mock(spec=FrameType)
    # Reset shutdown_requested before test
    import mcp_server_neurolorap.__main__

    mcp_server_neurolorap.__main__.shutdown_requested = False
    handle_shutdown(signal.SIGTERM, frame)
    assert mcp_server_neurolorap.__main__.shutdown_requested is True


def test_configure_cline_new_config(
    mock_config_path: Path, mock_project_root: Path
) -> None:
    """Test creating new Cline configuration."""
    configure_cline(mock_config_path)

    assert mock_config_path.exists()
    config = json.loads(mock_config_path.read_text())
    assert "mcpServers" in config
    assert "aindreyway-mcp-neurolorap" in config["mcpServers"]

    server_config = config["mcpServers"]["aindreyway-mcp-neurolorap"]
    assert server_config["command"] == sys.executable
    assert server_config["args"] == ["-m", "mcp_server_neurolorap"]
    assert server_config["disabled"] is False
    assert server_config["env"]["PYTHONPATH"] == str(mock_project_root)


def test_configure_cline_update_config(
    mock_config_path: Path, mock_project_root: Path
) -> None:
    """Test updating existing Cline configuration."""
    # Create initial config
    initial_config: ClinesConfig = {
        "mcpServers": {
            "aindreyway-mcp-neurolorap": {
                "command": "old_command",
                "args": ["old_arg"],
                "disabled": True,
                "alwaysAllow": [],
                "env": {"OLD_VAR": "old_value"},
            }
        }
    }
    mock_config_path.write_text(json.dumps(initial_config))

    configure_cline(mock_config_path)

    config = json.loads(mock_config_path.read_text())
    server_config = config["mcpServers"]["aindreyway-mcp-neurolorap"]
    assert server_config["command"] == sys.executable
    assert server_config["args"] == ["-m", "mcp_server_neurolorap"]
    assert server_config["disabled"] is False
    assert server_config["env"]["PYTHONPATH"] == str(mock_project_root)


def test_configure_cline_no_change(
    mock_config_path: Path, mock_project_root: Path
) -> None:
    """Test configuration when no changes needed."""
    # Create config with current values
    current_config: ClinesConfig = {
        "mcpServers": {
            "aindreyway-mcp-neurolorap": {
                "command": sys.executable,
                "args": ["-m", "mcp_server_neurolorap"],
                "disabled": False,
                "alwaysAllow": [],
                "env": {
                    "PYTHONPATH": str(mock_project_root),
                    "PYTHONUNBUFFERED": "1",
                    "MCP_PROJECT_ROOT": str(mock_project_root),
                },
            }
        }
    }
    mock_config_path.write_text(json.dumps(current_config))

    with patch("mcp_server_neurolorap.__main__.logger") as mock_logger:
        configure_cline(mock_config_path)
        mock_logger.info.assert_called_with(
            "Server already configured in Cline"
        )


def test_configure_cline_error() -> None:
    """Test error handling in configure_cline."""
    with patch(
        "mcp_server_neurolorap.__main__.Path.home",
        side_effect=Exception("Test error"),
    ), patch("mcp_server_neurolorap.__main__.logger") as mock_logger:
        configure_cline()
        mock_logger.warning.assert_called_with(
            "Failed to configure Cline: Test error"
        )


def test_main_dev_mode() -> None:
    """Test running server in developer mode."""
    mock_dev_mode = AsyncMock()
    with patch("sys.argv", ["script.py", "--dev"]), patch(
        "mcp_server_neurolorap.__main__.run_dev_mode",
        return_value=mock_dev_mode(),
    ), patch("mcp_server_neurolorap.__main__.asyncio.run") as mock_run:
        main()
        mock_run.assert_called_once()


def test_main_normal_mode() -> None:
    """Test running server in normal mode."""
    mock_server = MagicMock()
    with patch("sys.argv", ["script.py"]), patch(
        "mcp_server_neurolorap.__main__.create_server",
        return_value=mock_server,
    ), patch(
        "mcp_server_neurolorap.__main__.configure_cline"
    ) as mock_configure:
        main()
        mock_configure.assert_called_once()
        mock_server.run.assert_called_once()


def test_main_error() -> None:
    """Test error handling in main."""
    with patch(
        "mcp_server_neurolorap.__main__.create_server",
        side_effect=Exception("Test error"),
    ), patch("mcp_server_neurolorap.__main__.logger") as mock_logger:
        with pytest.raises(SystemExit) as exc_info:
            main()
            assert exc_info.value.code == 1
            mock_logger.exception.assert_called()


def test_main_entry_keyboard_interrupt() -> None:
    """Test handling keyboard interrupt in main_entry."""
    with patch(
        "mcp_server_neurolorap.__main__.main",
        side_effect=KeyboardInterrupt,
    ), patch("mcp_server_neurolorap.__main__.logger") as mock_logger:
        main_entry()
        mock_logger.info.assert_called_with("Server stopped by user")


def test_main_entry_error() -> None:
    """Test error handling in main_entry."""
    with patch(
        "mcp_server_neurolorap.__main__.main",
        side_effect=Exception("Test error"),
    ), patch("mcp_server_neurolorap.__main__.logger") as mock_logger:
        with pytest.raises(SystemExit) as exc_info:
            main_entry()
            assert exc_info.value.code == 1
            mock_logger.exception.assert_called_with("Server error")
