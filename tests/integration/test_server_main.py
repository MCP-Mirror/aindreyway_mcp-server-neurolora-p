import json
import signal
import sys
from pathlib import Path
from types import FrameType
from typing import Any, List
from unittest.mock import ANY, AsyncMock, MagicMock, Mock, patch

import pytest
from mcp.types import Resource, ResourceTemplate, TextContent, Tool

from mcpneurolora.__main__ import (
    ClinesConfig,
    configure_cline,
    handle_shutdown,
    main,
    main_entry,
)
from mcpneurolora.server import run_mcp_server, run_terminal_server


@pytest.fixture
def mock_config_paths(tmp_path: Path) -> list[Path]:
    config_paths = [
        tmp_path / "claude-dev" / "settings" / "cline_mcp_settings.json",
        tmp_path / "roo-cline" / "settings" / "cline_mcp_settings.json",
    ]
    for path in config_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
    return config_paths


def test_handle_shutdown() -> None:
    frame = Mock(spec=FrameType)
    import mcpneurolora.__main__

    mcpneurolora.__main__.shutdown_requested = False

    handle_shutdown(signal.SIGTERM, frame)
    assert mcpneurolora.__main__.shutdown_requested is True


def test_configure_cline_new_config(mock_config_paths: list[Path]) -> None:
    configure_cline(mock_config_paths)
    for config_path in mock_config_paths:
        assert config_path.exists()
        config_data = json.loads(config_path.read_text())
        server_cfg = config_data["mcpServers"]["aindreyway-neurolora"]
        assert server_cfg["command"] == "uvx"
        assert server_cfg["args"] == ["mcp-server-neurolora"]
        assert server_cfg["env"]["PYTHONUNBUFFERED"] == "1"
        assert server_cfg["disabled"] is False


def test_configure_cline_existing_config_update(mock_config_paths: list[Path]) -> None:
    initial_conf: ClinesConfig = {
        "mcpServers": {
            "aindreyway-neurolora": {
                "command": "old_command",
                "args": ["old_arg"],
                "disabled": True,
                "alwaysAllow": [],
                "env": {"SOME_VAR": "old_value"},
            }
        }
    }
    for p in mock_config_paths:
        p.write_text(json.dumps(initial_conf), encoding="utf-8")

    configure_cline(mock_config_paths)

    for config_path in mock_config_paths:
        config_data = json.loads(config_path.read_text())
        server_cfg = config_data["mcpServers"]["aindreyway-neurolora"]
        # Only command and args should be updated
        assert server_cfg["command"] == "uvx"
        assert server_cfg["args"] == ["mcp-server-neurolora"]
        # env and disabled should remain unchanged
        assert server_cfg["env"] == {"SOME_VAR": "old_value"}
        assert server_cfg["disabled"] is True


def test_configure_cline_no_change_needed(mock_config_paths: list[Path]) -> None:
    correct_conf: ClinesConfig = {
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
    for path in mock_config_paths:
        path.write_text(json.dumps(correct_conf), encoding="utf-8")

    with patch("mcpneurolora.__main__.logger") as mock_logger:
        configure_cline(mock_config_paths)
        called_infos = [c.args[0] for c in mock_logger.info.call_args_list]
        assert any(
            "Server already configured in Cline at" in msg for msg in called_infos
        )


@pytest.mark.parametrize(
    "command_line",
    [
        ["script.py", "--dev"],
        ["script.py", "--dev", "some-other-arg"],
    ],
)
def test_main_terminal_mode(command_line: List[str]) -> None:
    terminal_server_mock: AsyncMock = AsyncMock()

    with patch.object(sys, "argv", command_line), patch(
        "mcpneurolora.__main__.run_terminal_server", terminal_server_mock
    ), patch("mcpneurolora.__main__.asyncio.run") as mock_run:
        main()
        terminal_server_mock.assert_called_once()
        mock_run.assert_called_once_with(ANY)


def test_main_production_mode() -> None:
    mcp_server_mock: AsyncMock = AsyncMock()

    with patch.object(sys, "argv", ["script.py"]), patch(
        "mcpneurolora.__main__.run_mcp_server", mcp_server_mock
    ), patch("mcpneurolora.__main__.configure_cline") as mock_conf, patch(
        "mcpneurolora.__main__.asyncio.run"
    ) as mock_run:
        main()
        mock_conf.assert_called_once()
        mcp_server_mock.assert_called_once()
        mock_run.assert_called_once_with(ANY)


def test_main_entry_keyboard_interrupt() -> None:
    with patch("mcpneurolora.__main__.main", side_effect=KeyboardInterrupt), patch(
        "mcpneurolora.__main__.logger"
    ) as mock_logger:
        main_entry()
        mock_logger.info.assert_any_call("Server stopped by user")


def test_main_entry_error() -> None:
    with patch(
        "mcpneurolora.__main__.main", side_effect=Exception("Test error")
    ), patch("mcpneurolora.__main__.logger") as mock_logger, pytest.raises(
        SystemExit
    ) as exc_info:
        main_entry()
    assert exc_info.value.code == 1
    mock_logger.exception.assert_called()


@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_run_mcp_server_happy_path() -> None:
    mock_server_instance = AsyncMock()

    # Create mock server methods
    def list_tools(self: Any) -> List[Tool]:
        return []

    def call_tool(self: Any, *args: Any, **kwargs: Any) -> List[TextContent]:
        return []

    def list_resources(self: Any) -> List[Resource]:
        return []

    def list_resource_templates(self: Any) -> List[ResourceTemplate]:
        return []

    def read_resource(self: Any, *args: Any) -> str:
        return ""

    # Mock server methods
    mock_server_instance.list_tools = Mock(return_value=list_tools)
    mock_server_instance.call_tool = Mock(return_value=call_tool)
    mock_server_instance.list_resources = Mock(return_value=list_resources)
    mock_server_instance.list_resource_templates = Mock(
        return_value=list_resource_templates
    )
    mock_server_instance.read_resource = Mock(return_value=read_resource)
    mock_server_instance.run = AsyncMock()

    with patch("mcpneurolora.server.Server", return_value=mock_server_instance), patch(
        "mcpneurolora.server.stdio_server"
    ) as mock_stdio, patch("mcpneurolora.server.os.environ", {"AI_TIMEOUT_MS": "1000"}):
        # Mock stdin and stdout
        mock_stdin = AsyncMock()
        mock_stdout = AsyncMock()
        mock_stdio.return_value.__aenter__.return_value = (mock_stdin, mock_stdout)
        mock_stdio.return_value.__aexit__ = AsyncMock()

        # Mock sys.stdin/stdout
        with patch("sys.stdin") as mock_sys_stdin, patch("sys.stdout"), patch(
            "sys.stderr"
        ):
            mock_sys_stdin.readline.return_value = ""
            mock_sys_stdin.buffer = MagicMock()
            mock_sys_stdin.buffer.read = AsyncMock(return_value=b"")

            await run_mcp_server()

            # Verify server was run
            mock_server_instance.run.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_run_terminal_server_happy_path() -> None:
    mock_terminal_instance = MagicMock()
    mock_terminal_instance.parse_request = AsyncMock(
        side_effect=[
            {"jsonrpc": "2.0", "method": "exit", "id": 1},
            {"jsonrpc": "2.0", "method": "exit", "id": 2},
        ]
    )
    mock_terminal_instance.handle_command = AsyncMock(
        return_value={"jsonrpc": "2.0", "result": "Goodbye!", "id": 1}
    )

    with patch(
        "mcpneurolora.server.JsonRpcTerminal", return_value=mock_terminal_instance
    ), patch("mcpneurolora.terminal_server.logger") as mock_logger:
        # Mock stdin/stdout
        with patch("sys.stdin") as mock_stdin, patch("sys.stdout"), patch("sys.stderr"):
            mock_stdin.readline.side_effect = ["exit\n", ""]
            mock_stdin.buffer = MagicMock()
            mock_stdin.buffer.read = AsyncMock(return_value=b"")

            # Run server
            await run_terminal_server()

            # Verify interactions
            assert mock_terminal_instance.parse_request.call_count >= 1
            assert mock_terminal_instance.handle_command.call_count >= 1
            mock_logger.info.assert_any_call("Starting terminal server...")
            mock_logger.info.assert_any_call("Terminal server stopped")


def test_shutdown_requested_flag_reset() -> None:
    """Test that shutdown_requested flag can be reset."""
    import mcpneurolora.__main__

    # Save initial state
    initial_state = mcpneurolora.__main__.shutdown_requested

    try:
        # Set flag to True
        mcpneurolora.__main__.shutdown_requested = True
        assert mcpneurolora.__main__.shutdown_requested is True

        # Reset flag to False
        mcpneurolora.__main__.shutdown_requested = False
        assert mcpneurolora.__main__.shutdown_requested is False

    finally:
        # Restore initial state
        mcpneurolora.__main__.shutdown_requested = initial_state
