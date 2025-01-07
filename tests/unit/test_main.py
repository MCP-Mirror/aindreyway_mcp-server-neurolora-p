"""Unit tests for the main module."""

import json
import signal
from pathlib import Path
from types import FrameType
from typing import Generator, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pytest import FixtureRequest

from mcpneurolora.__main__ import (
    ClinesConfig,
    configure_cline,
    handle_shutdown,
    main,
    main_entry,
)


@pytest.fixture
def mock_config_paths(
    request: FixtureRequest, tmp_path: Path
) -> Generator[List[Path], None, None]:
    """Create temporary config paths.

    Args:
        request: Pytest fixture request
        tmp_path: Temporary directory path

    Yields:
        List of temporary config paths
    """
    config_paths = [
        tmp_path / "claude-dev" / "settings" / "cline_mcp_settings.json",
        tmp_path / "roo-cline" / "settings" / "cline_mcp_settings.json",
    ]
    for path in config_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
    mock_home = Mock()
    mock_home.return_value = tmp_path.parent
    with patch("mcpneurolora.__main__.Path.home", mock_home):
        yield config_paths


@pytest.fixture
def mock_project_root(
    request: FixtureRequest, tmp_path: Path
) -> Generator[Path, None, None]:
    """Create a temporary project root.

    Args:
        request: Pytest fixture request
        tmp_path: Temporary directory path

    Yields:
        Path to temporary project root
    """
    project_path = tmp_path / "src" / "mcp_server_neurolora"
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

    with patch("mcpneurolora.__main__.Path", mock_path):
        yield tmp_path


def test_handle_shutdown() -> None:
    """Test shutdown signal handler."""
    frame = Mock(spec=FrameType)
    # Reset shutdown_requested before test
    import mcpneurolora.__main__

    mcpneurolora.__main__.shutdown_requested = False
    handle_shutdown(signal.SIGTERM, frame)
    assert mcpneurolora.__main__.shutdown_requested is True


def test_configure_cline_new_config(
    mock_config_paths: List[Path], mock_project_root: Path
) -> None:
    """Test creating new Cline configuration."""
    configure_cline(mock_config_paths)

    for config_path in mock_config_paths:
        assert config_path.exists()
        config = json.loads(config_path.read_text())
        assert "mcpServers" in config
        assert "aindreyway-neurolora" in config["mcpServers"]

        server_config = config["mcpServers"]["aindreyway-neurolora"]
        assert server_config["command"] == "uvx"
        assert server_config["args"] == ["mcp-server-neurolora"]
        assert server_config["disabled"] is False
        assert server_config["env"]["PYTHONUNBUFFERED"] == "1"


def test_configure_cline_update_config(
    mock_config_paths: List[Path], mock_project_root: Path
) -> None:
    """Test updating existing Cline configuration."""
    # Create initial config
    initial_config: ClinesConfig = {
        "mcpServers": {
            "aindreyway-neurolora": {
                "command": "old_command",
                "args": ["old_arg"],
                "disabled": True,
                "alwaysAllow": [],
                "env": {"OLD_VAR": "old_value"},
            }
        }
    }
    for config_path in mock_config_paths:
        config_path.write_text(json.dumps(initial_config))

    configure_cline(mock_config_paths)

    for config_path in mock_config_paths:
        config = json.loads(config_path.read_text())
        server_config = config["mcpServers"]["aindreyway-neurolora"]
        assert server_config["command"] == "uvx"
        assert server_config["args"] == ["mcp-server-neurolora"]
        # These values should not be changed
        assert server_config["disabled"] is True
        assert server_config["env"]["OLD_VAR"] == "old_value"


def test_configure_cline_no_change(
    mock_config_paths: List[Path], mock_project_root: Path
) -> None:
    """Test configuration when no changes needed."""
    # Create config with current values
    current_config: ClinesConfig = {
        "mcpServers": {
            "aindreyway-neurolora": {
                "command": "uvx",
                "args": ["mcp-server-neurolora"],
                "disabled": False,
                "alwaysAllow": [],
                "env": {"PYTHONUNBUFFERED": "1"},
            }
        }
    }
    for config_path in mock_config_paths:
        config_path.write_text(json.dumps(current_config))

    with patch("mcpneurolora.__main__.logger") as mock_logger:
        configure_cline(mock_config_paths)
        assert mock_logger.info.call_count == len(mock_config_paths)
        for config_path in mock_config_paths:
            mock_logger.info.assert_any_call(
                f"Server already configured in Cline at {config_path}"
            )


def test_configure_cline_error() -> None:
    """Test error handling in configure_cline."""
    with patch(
        "mcpneurolora.__main__.get_config_paths",
        side_effect=Exception("Test error"),
    ), patch("mcpneurolora.__main__.logger") as mock_logger:
        configure_cline()
        mock_logger.exception.assert_called_with(
            "Critical error configuring None: Test error. "
            "This is likely a bug that should be reported."
        )


def test_main_terminal_mode() -> None:
    """Test running server in terminal mode."""
    mock_terminal = AsyncMock()
    with patch("sys.argv", ["script.py", "--dev"]), patch(
        "mcpneurolora.__main__.run_terminal_server",
        return_value=mock_terminal(),
    ), patch("mcpneurolora.__main__.asyncio.run") as mock_run:
        main()
        mock_run.assert_called_once()


def test_main_production_mode() -> None:
    """Test running server in production mode."""
    mock_server = AsyncMock()
    mock_server.return_value = None  # Ensure coroutine returns None
    with patch("sys.argv", ["script.py"]), patch(
        "mcpneurolora.__main__.run_mcp_server",
        return_value=mock_server(),
    ), patch("mcpneurolora.__main__.configure_cline") as mock_configure, patch(
        "mcpneurolora.__main__.asyncio.run"
    ) as mock_run:
        main()
        mock_configure.assert_called_once()
        mock_run.assert_called_once()


def test_main_error() -> None:
    """Test error handling in main."""
    with patch(
        "mcpneurolora.__main__.run_mcp_server",
        side_effect=Exception("Test error"),
    ), patch("mcpneurolora.__main__.logger") as mock_logger:
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        mock_logger.exception.assert_called()


def test_main_entry_keyboard_interrupt() -> None:
    """Test handling keyboard interrupt in main_entry."""
    with patch(
        "mcpneurolora.__main__.main",
        side_effect=KeyboardInterrupt,
    ), patch("mcpneurolora.__main__.logger") as mock_logger:
        main_entry()
        mock_logger.info.assert_called_with("Server stopped by user")


def test_main_entry_error() -> None:
    """Test error handling in main_entry."""
    with patch(
        "mcpneurolora.__main__.main",
        side_effect=Exception("Test error"),
    ), patch("mcpneurolora.__main__.logger") as mock_logger:
        with pytest.raises(SystemExit) as exc:
            main_entry()
        assert exc.value.code == 1
        mock_logger.exception.assert_called_with(
            "Unexpected server error: Test error. "
            "This is likely a bug that should be reported."
        )
