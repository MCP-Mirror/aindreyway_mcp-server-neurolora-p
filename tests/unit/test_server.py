"""Unit tests for the MCP server implementation."""

import os
from pathlib import Path
from typing import Any, Callable, Generator, Protocol, runtime_checkable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_neurolorap.server import create_server, run_dev_mode


@runtime_checkable
class FastMCPProtocol(Protocol):
    """Protocol defining FastMCP interface for testing."""

    def __init__(self, name: str, tools: bool = False) -> None: ...
    def tool(self) -> Callable[..., Any]: ...
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


class MockFastMCP:
    """Mock class for FastMCP."""

    def __init__(self, name: str, tools: bool = False) -> None:
        self._tool_mock = AsyncMock()
        self.tool = MagicMock(return_value=lambda x: x)
        self.code_collector = self._tool_mock

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Make the mock callable."""
        return self


@pytest.fixture
def mock_fastmcp() -> Generator[MockFastMCP, None, None]:
    """Mock FastMCP server."""
    with patch("mcp_server_neurolorap.server.FastMCP") as mock:
        mock_server = MockFastMCP("neurolorap", tools=True)
        mock.return_value = mock_server
        yield mock_server


@pytest.fixture
def mock_collector() -> Generator[MagicMock, None, None]:
    """Mock CodeCollector."""
    with patch("mcp_server_neurolorap.server.CodeCollector") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_terminal() -> Generator[MagicMock, None, None]:
    """Mock JsonRpcTerminal."""
    with patch("mcp_server_neurolorap.server.JsonRpcTerminal") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


def test_create_server(mock_fastmcp: MockFastMCP) -> None:
    """Test server creation and configuration."""
    create_server()

    # Verify FastMCP initialization
    mock_fastmcp.assert_called_once_with("neurolorap", tools=True)


@pytest.mark.asyncio
async def test_code_collector_tool_success(
    mock_collector: MagicMock, project_root: Path
) -> None:
    """Test successful code collection through MCP tool."""
    # Setup mock collector
    mock_collector.collect_code.return_value = project_root / "output.md"

    # Create server and get tool function
    server = create_server()
    tool_func = server.code_collector

    # Test with single input
    result = await tool_func("src/")
    assert "Code collection complete!" in result
    assert "output.md" in result

    # Test with multiple inputs
    result = await tool_func(["src/", "tests/"])
    assert "Code collection complete!" in result
    assert "output.md" in result

    # Verify collector calls
    mock_collector.collect_code.assert_called()


@pytest.mark.asyncio
async def test_code_collector_tool_errors(mock_collector: MagicMock) -> None:
    """Test error handling in code collector tool."""
    server = create_server()
    tool_func = server.code_collector

    # Test file not found error
    mock_collector.collect_code.side_effect = FileNotFoundError("Test error")
    result = await tool_func("nonexistent/")
    assert "File system error" in result

    # Test permission error
    mock_collector.collect_code.side_effect = PermissionError("Test error")
    result = await tool_func("src/")
    assert "File system error" in result

    # Test value error
    mock_collector.collect_code.side_effect = ValueError("Test error")
    result = await tool_func("src/")
    assert "Invalid input" in result

    # Test unexpected error
    mock_collector.collect_code.side_effect = Exception("Test error")
    result = await tool_func("src/")
    assert "An unexpected error occurred" in result


@pytest.mark.asyncio
async def test_dev_mode_commands(mock_terminal: MagicMock) -> None:
    """Test developer mode command handling."""
    # Setup mock terminal responses
    mock_terminal.parse_request.return_value = {
        "jsonrpc": "2.0",
        "method": "help",
        "id": 1,
    }
    mock_terminal.handle_command = AsyncMock(
        return_value={"jsonrpc": "2.0", "result": "Help message", "id": 1}
    )

    # Mock input/print functions
    with patch("builtins.input", side_effect=["help", "exit"]), patch(
        "builtins.print"
    ) as mock_print:
        await run_dev_mode()

        # Verify terminal interactions
        mock_terminal.parse_request.assert_called()
        mock_terminal.handle_command.assert_called()

        # Verify output
        mock_print.assert_any_call("Help message")


@pytest.mark.asyncio
async def test_dev_mode_error_handling(mock_terminal: MagicMock) -> None:
    """Test error handling in developer mode."""
    # Setup mock terminal to raise errors
    mock_terminal.parse_request.side_effect = ValueError("Invalid command")

    # Mock input/print functions
    with patch("builtins.input", side_effect=["invalid", "exit"]), patch(
        "builtins.print"
    ) as mock_print:
        await run_dev_mode()

        # Verify error handling
        mock_print.assert_any_call("Value error: Invalid command")


def test_project_root_environment() -> None:
    """Test project root environment variable handling."""
    # Test with environment variable set
    test_path = "/test/path"
    with patch.dict(os.environ, {"MCP_PROJECT_ROOT": test_path}):
        create_server()
        assert os.environ["MCP_PROJECT_ROOT"] == test_path

    # Test with environment variable not set
    with patch.dict(os.environ, clear=True):
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/current/dir")
            create_server()
            assert os.environ["MCP_PROJECT_ROOT"] == "/current/dir"


@pytest.mark.asyncio
async def test_code_collector_tool_with_subproject(
    mock_collector: MagicMock,
) -> None:
    """Test code collector tool with subproject ID."""
    server = create_server()
    tool_func = server.code_collector

    # Test with subproject ID
    await tool_func(
        input="src/", title="Test Collection", subproject_id="test-sub"
    )

    # Verify collector was created with subproject ID
    mock_collector.assert_called_with(
        project_root=Path(os.environ["MCP_PROJECT_ROOT"]),
        subproject_id="test-sub",
    )


@pytest.mark.asyncio
async def test_dev_mode_keyboard_interrupt(mock_terminal: MagicMock) -> None:
    """Test handling of keyboard interrupt in developer mode."""
    # Mock input to raise KeyboardInterrupt
    with patch("builtins.input", side_effect=KeyboardInterrupt), patch(
        "builtins.print"
    ) as mock_print:
        await run_dev_mode()

        # Verify graceful exit
        mock_print.assert_called_with("\nExiting developer mode")


def test_server_tool_registration(mock_fastmcp: MockFastMCP) -> None:
    """Test that tools are properly registered with the server."""
    create_server()

    # Verify tool decorator was called
    assert mock_fastmcp.tool.called
