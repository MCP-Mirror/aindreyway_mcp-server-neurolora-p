"""Unit tests for terminal functionality."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type
from unittest.mock import patch

import pytest

from mcpneurolora.terminal import JsonRpcTerminal


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a temporary project root directory."""
    return tmp_path


@pytest.fixture
def terminal(project_root: Path) -> JsonRpcTerminal:
    """Create a JsonRpcTerminal instance."""
    return JsonRpcTerminal(project_root=str(project_root))


@pytest.fixture
def terminal_with_root(project_root: Path) -> JsonRpcTerminal:
    """Create a JsonRpcTerminal instance with project root."""
    return JsonRpcTerminal(project_root=str(project_root))


def test_init_basic(terminal: JsonRpcTerminal) -> None:
    """Test basic terminal initialization."""
    assert terminal is not None
    assert isinstance(terminal.project_root, Path)
    assert set(terminal.commands.keys()) == {
        "help",
        "list_tools",
        "collect",
        "showtree",
        "exit",
    }


def test_init_with_project_root(
    terminal_with_root: JsonRpcTerminal,
    project_root: Path,
) -> None:
    """Test terminal initialization with project root."""
    assert isinstance(terminal_with_root.project_root, Path)
    assert terminal_with_root.project_root.samefile(project_root)


def test_parse_request_valid(terminal: JsonRpcTerminal) -> None:
    """Test parsing valid requests."""
    test_cases: List[Tuple[str, str, List[str]]] = [
        ("help", "help", []),
        ("collect src", "collect", ["src"]),
        ("collect src test-sub", "collect", ["src", "test-sub"]),
        ("list_tools", "list_tools", []),
        ("exit", "exit", []),
    ]

    for input_str, expected_method, expected_params in test_cases:
        request = terminal.parse_request(input_str)
        assert request is not None
        assert request["method"] == expected_method
        assert request["params"] == expected_params


def test_parse_request_invalid(terminal: JsonRpcTerminal) -> None:
    """Test parsing invalid requests."""
    invalid_inputs: List[Optional[str]] = [
        "",  # Empty string
        "   ",  # Only spaces
        "invalid\x00command",  # Invalid characters
        None,  # None input
    ]

    for input_str in invalid_inputs:
        if input_str is not None:
            assert terminal.parse_request(input_str) is None


def test_format_response_success(terminal: JsonRpcTerminal) -> None:
    """Test formatting successful responses."""
    result = "Test result"
    response = terminal.format_response(result)
    assert response["jsonrpc"] == "2.0"
    assert "id" in response
    assert response["result"] == result


def test_format_response_error(terminal: JsonRpcTerminal) -> None:
    """Test formatting error responses."""
    error: Dict[str, Any] = {"code": -32000, "message": "Test error"}
    response = terminal.format_response(None, error)
    assert response["jsonrpc"] == "2.0"
    assert "id" in response
    assert "error" in response
    assert response["error"] == error


def test_format_response_different_errors(terminal: JsonRpcTerminal) -> None:
    """Test formatting different error types."""
    error_codes: Dict[int, str] = {
        -32700: "Parse error",
        -32600: "Invalid Request",
        -32601: "Method not found",
        -32602: "Invalid params",
        -32603: "Internal error",
        -32000: "Server error",
    }

    for code, message in error_codes.items():
        error: Dict[str, Any] = {"code": code, "message": message}
        response = terminal.format_response(None, error)
        assert response["error"]["code"] == code
        assert message in response["error"]["message"]


def test_format_response_different_types(terminal: JsonRpcTerminal) -> None:
    """Test formatting responses with different result types."""
    test_cases: List[Tuple[Any, Type[Any]]] = [
        ("string result", str),
        (123, int),
        (True, bool),
        (None, type(None)),
        ({"key": "value"}, dict),
        (["item1", "item2"], list),
    ]

    for value, expected_type in test_cases:
        response = terminal.format_response(value)
        assert isinstance(response["result"], expected_type)


@pytest.mark.asyncio
async def test_cmd_help(terminal: JsonRpcTerminal) -> None:
    """Test help command."""
    result = await terminal.cmd_help([])
    assert isinstance(result, str)
    assert "Available Commands" in result


@pytest.mark.asyncio
async def test_cmd_list_tools(terminal: JsonRpcTerminal) -> None:
    """Test list_tools command."""
    result = await terminal.cmd_list_tools([])
    assert isinstance(result, list)
    assert "collect" in result


@pytest.mark.asyncio
async def test_cmd_exit(terminal: JsonRpcTerminal) -> None:
    """Test exit command."""
    result = await terminal.cmd_exit([])
    assert isinstance(result, str)
    assert "Goodbye!" in result


@pytest.mark.asyncio
async def test_handle_command_unknown(terminal: JsonRpcTerminal) -> None:
    """Test handling unknown command."""
    request: Dict[str, Any] = {"jsonrpc": "2.0", "method": "unknown", "id": 1}
    response = await terminal.handle_command(request)
    assert "error" in response
    assert "Method 'unknown' not found" in response["error"]["message"]


@pytest.mark.asyncio
async def test_handle_command_error(terminal: JsonRpcTerminal) -> None:
    """Test handling command error."""
    request: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "method": "showtree",
        "params": ["extra", "params"],  # showtree takes no parameters
        "id": 1,
    }
    response = await terminal.handle_command(request)
    assert "error" in response
    assert "Invalid parameter" in response["error"]["message"]


@pytest.mark.asyncio
async def test_handle_command_invalid_params(terminal: JsonRpcTerminal) -> None:
    """Test handling invalid parameters."""
    request: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "method": "showtree",
        "params": ["extra", "params"],  # showtree takes no parameters
        "id": 0,
    }
    response = await terminal.handle_command(request)
    assert "error" in response
    assert "Invalid parameter" in response["error"]["message"]


@pytest.mark.asyncio
async def test_cmd_collect_success(
    terminal_with_root: JsonRpcTerminal,
    project_root: Path,
) -> None:
    """Test successful code collection."""
    # Create test file
    test_file = project_root / "test.py"
    test_file.write_text("print('test')")

    try:
        result = await terminal_with_root.cmd_collect([str(test_file)])
        assert isinstance(result, Dict)
        assert "result" in result
        assert isinstance(result["result"], str)
        assert result["result"].endswith(".md")
    finally:
        # Cleanup
        test_file.unlink()


@pytest.mark.asyncio
async def test_cmd_collect_no_params(terminal: JsonRpcTerminal) -> None:
    """Test code collection with no parameters."""
    result = await terminal.cmd_collect([])
    assert isinstance(result, Dict)
    assert "result" in result
    assert "No files found to process" in result["result"]


@pytest.mark.asyncio
async def test_cmd_collect_invalid_executor_creation(
    terminal: JsonRpcTerminal,
) -> None:
    """Test code collection with invalid executor creation."""
    with patch("mcpneurolora.terminal.ToolExecutor") as mock_executor:
        mock_executor.side_effect = ValueError("Invalid configuration")
        result = await terminal.cmd_collect(["test.py"])
        assert isinstance(result, Dict)
        assert "result" in result
        assert "No files found to process" in result["result"]


@pytest.mark.parametrize(
    "path_input",
    [
        "src/",  # Directory path
        "./src",  # Relative path
        "'quoted/path'",  # Quoted path
        '"double/quoted/path"',  # Double quoted path
        "path with spaces",  # Path with spaces
        "multiple/path/segments",  # Multiple segments
    ],
)
@pytest.mark.asyncio
async def test_cmd_collect_path_formats(
    terminal_with_root: JsonRpcTerminal,
    project_root: Path,
    path_input: str,
) -> None:
    """Test code collection with different path formats."""
    # Create test file
    test_dir = project_root / "test_dir"
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / "test.py"
    test_file.write_text("print('test')")

    try:
        # Replace path segments in input with actual test directory
        actual_path = str(test_dir)
        if path_input.startswith(("'", '"')):
            actual_path = f"{path_input[0]}{test_dir}{path_input[0]}"

        result = await terminal_with_root.cmd_collect([actual_path])
        assert isinstance(result, Dict)
        assert "result" in result
        assert isinstance(result["result"], str)
        assert result["result"].endswith(".md")
    finally:
        # Cleanup
        test_file.unlink()
        test_dir.rmdir()


@pytest.mark.asyncio
async def test_cmd_collect_with_subproject(
    terminal_with_root: JsonRpcTerminal,
    project_root: Path,
) -> None:
    """Test code collection with subproject ID."""
    # Create test file
    test_file = project_root / "test.py"
    test_file.write_text("print('test')")

    try:
        result = await terminal_with_root.cmd_collect(
            [str(test_file), "test-sub"],
        )
        assert isinstance(result, Dict)
        assert "result" in result
        assert isinstance(result["result"], str)
        assert result["result"].endswith(".md")
    finally:
        # Cleanup
        test_file.unlink()


@pytest.mark.asyncio
async def test_cmd_collect_no_files(
    terminal_with_root: JsonRpcTerminal,
) -> None:
    """Test code collection with no files."""
    result = await terminal_with_root.cmd_collect(["nonexistent"])
    assert isinstance(result, Dict)
    assert "result" in result
    assert "No files found to process" in result["result"]


@pytest.mark.asyncio
async def test_command_execution_flow(terminal: JsonRpcTerminal) -> None:
    """Test complete command execution flow."""
    # Test help command
    request: Dict[str, Any] = {"jsonrpc": "2.0", "method": "help", "id": 1}
    response = await terminal.handle_command(request)
    assert "Available Commands" in response["result"]

    # Test list_tools command
    request = {"jsonrpc": "2.0", "method": "list_tools", "id": 2}
    response = await terminal.handle_command(request)
    assert isinstance(response["result"], list)

    # Test exit command
    request = {"jsonrpc": "2.0", "method": "exit", "id": 3}
    response = await terminal.handle_command(request)
    assert "Goodbye!" in response["result"]
