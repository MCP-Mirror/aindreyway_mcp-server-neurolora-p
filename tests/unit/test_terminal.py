"""Unit tests for the JsonRpcTerminal class."""

from pathlib import Path
import pytest
from unittest.mock import MagicMock

from mcp_server_neurolorap.terminal import JsonRpcTerminal


@pytest.fixture
def terminal() -> JsonRpcTerminal:
    """Create a JsonRpcTerminal instance for testing."""
    return JsonRpcTerminal()


@pytest.fixture
def terminal_with_root(project_root: Path) -> JsonRpcTerminal:
    """Create a JsonRpcTerminal instance with project root."""
    return JsonRpcTerminal(project_root=str(project_root))


def test_init_basic(terminal: JsonRpcTerminal) -> None:
    """Test basic initialization of JsonRpcTerminal."""
    assert terminal.project_root is None
    assert terminal.collector is not None
    assert set(terminal.commands.keys()) == {
        "help",
        "list_tools",
        "collect",
        "exit",
    }


def test_init_with_project_root(
    terminal_with_root: JsonRpcTerminal, project_root: Path
) -> None:
    """Test initialization with project root."""
    assert terminal_with_root.project_root == project_root
    assert terminal_with_root.collector.project_root == project_root


@pytest.mark.parametrize(
    "input_line,expected_method,expected_params",
    [
        ("help", "help", []),
        ("collect src", "collect", ["src"]),
        ("collect src test-sub", "collect", ["src", "test-sub"]),
        ("list_tools", "list_tools", []),
        ("exit", "exit", []),
    ],
)
def test_parse_request_valid(
    terminal: JsonRpcTerminal,
    input_line: str,
    expected_method: str,
    expected_params: list[str],
) -> None:
    """Test parsing valid requests."""
    request = terminal.parse_request(input_line)
    assert request is not None
    assert request["jsonrpc"] == "2.0"
    assert request["method"] == expected_method
    assert request["params"] == expected_params
    assert isinstance(request["id"], int)


@pytest.mark.parametrize(
    "input_line",
    [
        "",  # Empty line
        "   ",  # Whitespace only
        "\n",  # Newline only
    ],
)
def test_parse_request_invalid(
    terminal: JsonRpcTerminal, input_line: str
) -> None:
    """Test parsing invalid requests."""
    assert terminal.parse_request(input_line) is None


def test_format_response_success(terminal: JsonRpcTerminal) -> None:
    """Test formatting successful responses."""
    result = "test result"
    response = terminal.format_response(result)
    assert response["jsonrpc"] == "2.0"
    assert response["result"] == result
    assert isinstance(response["id"], int)
    assert "error" not in response


def test_format_response_error(terminal: JsonRpcTerminal) -> None:
    """Test formatting error responses."""
    error = {"code": -32000, "message": "Test error"}
    response = terminal.format_response(None, error)
    assert response["jsonrpc"] == "2.0"
    assert response["error"] == error
    assert isinstance(response["id"], int)
    assert "result" not in response


@pytest.mark.asyncio
async def test_handle_command_unknown(terminal: JsonRpcTerminal) -> None:
    """Test handling unknown commands."""
    request = {"jsonrpc": "2.0", "method": "unknown", "id": 1}
    response = await terminal.handle_command(request)
    assert "error" in response
    assert response["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_handle_command_error(terminal: JsonRpcTerminal) -> None:
    """Test handling command execution errors."""
    # Mock collect command to raise an error
    terminal.commands["collect"] = MagicMock(
        side_effect=ValueError("Test error")
    )

    request = {"jsonrpc": "2.0", "method": "collect", "id": 1}
    response = await terminal.handle_command(request)
    assert "error" in response
    assert "Test error" in response["error"]["message"]


@pytest.mark.asyncio
async def test_cmd_help(terminal: JsonRpcTerminal) -> None:
    """Test help command."""
    result = await terminal.cmd_help([])
    assert isinstance(result, str)
    assert "Available commands" in result
    assert "help" in result
    assert "list_tools" in result
    assert "collect" in result
    assert "exit" in result


@pytest.mark.asyncio
async def test_cmd_list_tools(terminal: JsonRpcTerminal) -> None:
    """Test list_tools command."""
    result = await terminal.cmd_list_tools([])
    assert isinstance(result, list)
    assert "code-collector" in result


@pytest.mark.asyncio
async def test_cmd_collect_no_params(terminal: JsonRpcTerminal) -> None:
    """Test collect command without parameters."""
    with pytest.raises(ValueError, match="Path parameter required"):
        await terminal.cmd_collect([])


@pytest.mark.asyncio
async def test_cmd_collect_success(
    terminal_with_root: JsonRpcTerminal, project_root: Path
) -> None:
    """Test successful code collection."""
    # Create test file
    test_file = project_root / "test.py"
    test_file.write_text("print('test')")

    try:
        result = await terminal_with_root.cmd_collect([str(test_file)])
        assert isinstance(result, dict)
        assert "Code collection complete!" in result["result"]
        assert "Output file:" in result["result"]
    finally:
        # Cleanup
        test_file.unlink()


@pytest.mark.asyncio
async def test_cmd_collect_with_subproject(
    terminal_with_root: JsonRpcTerminal, project_root: Path
) -> None:
    """Test code collection with subproject ID."""
    # Create test file
    test_file = project_root / "test.py"
    test_file.write_text("print('test')")

    try:
        result = await terminal_with_root.cmd_collect(
            [str(test_file), "test-sub"]
        )
        assert isinstance(result, dict)
        assert "Code collection complete!" in result["result"]
        assert "Subproject ID: test-sub" in result["result"]
    finally:
        # Cleanup
        test_file.unlink()


@pytest.mark.asyncio
async def test_cmd_collect_no_files(
    terminal_with_root: JsonRpcTerminal,
) -> None:
    """Test code collection with no files."""
    with pytest.raises(
        ValueError, match="Failed to collect code or no files found"
    ):
        await terminal_with_root.cmd_collect(["nonexistent"])


@pytest.mark.asyncio
async def test_cmd_exit(terminal: JsonRpcTerminal) -> None:
    """Test exit command."""
    result = await terminal.cmd_exit([])
    assert result == "Goodbye!"


@pytest.mark.asyncio
async def test_command_execution_flow(terminal: JsonRpcTerminal) -> None:
    """Test complete command execution flow."""
    # Test help command
    request = terminal.parse_request("help")
    assert request is not None
    response = await terminal.handle_command(request)
    assert "result" in response
    assert isinstance(response["result"], str)
    assert "Available commands" in response["result"]

    # Test list_tools command
    request = terminal.parse_request("list_tools")
    assert request is not None
    response = await terminal.handle_command(request)
    assert "result" in response
    assert isinstance(response["result"], list)
    assert "code-collector" in response["result"]

    # Test exit command
    request = terminal.parse_request("exit")
    assert request is not None
    response = await terminal.handle_command(request)
    assert "result" in response
    assert response["result"] == "Goodbye!"
