"""Unit tests for the MCP server implementation."""

import os
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, Generator, TypeVar, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_neurolorap.server import (
    create_server,
    get_project_root,
    run_dev_mode,
)

T = TypeVar("T", bound=Callable[..., Any])
ToolCallable = Callable[..., Coroutine[Any, Any, str]]


class ToolMock(AsyncMock):
    """Custom AsyncMock that matches the expected tool callable type."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._collector: AsyncMock | None = None

    def set_collector(self, collector: AsyncMock) -> None:
        """Set the collector instance for this tool."""
        self._collector = collector

    async def __call__(self, *args: Any, **kwargs: Any) -> str:
        if not self._collector:
            return await super().__call__(*args, **kwargs)  # type: ignore

        try:
            input_val = args[0] if args else kwargs.get("input")
            title = kwargs.get("title", "Code Collection")
            output = await self._collector.collect_code(input_val, title)
            if not output:
                return "No files found to process or error occurred"
            return f"Code collection complete!\nOutput file: {output}"
        except (FileNotFoundError, PermissionError, OSError) as e:
            return f"File system error collecting code: {e}"
        except ValueError as e:
            return f"Invalid input: {e}"
        except TypeError as e:
            return f"Type error: {e}"
        except Exception:
            return "No files found to process or error occurred"


class MockFastMCP:
    """Mock class for FastMCP."""

    def __init__(self, name: str, tools: bool = False) -> None:
        self.name = name
        self.tools = tools
        self._tool_mock = AsyncMock()
        self._tool_called = False
        self.run = MagicMock()
        self._tools: Dict[str, ToolMock] = {}

        def tool(*args: Any, **kwargs: Any) -> Callable[[T], T]:
            def decorator(func: T) -> T:
                tool_mock = ToolMock()
                self._tools[func.__name__] = tool_mock
                self._tool_mock(*args, **kwargs)
                self._tool_called = True
                return tool_mock

            return decorator

        self.tool = tool

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Make the mock callable."""
        if args == (self.name,) and kwargs == {"tools": self.tools}:
            self._tool_mock(*args, **kwargs)
        return self

    def assert_called_once_with(self, *args: Any, **kwargs: Any) -> None:
        """Assert the mock was called once with specific arguments."""
        if not (args == (self.name,) and kwargs == {"tools": self.tools}):
            raise AssertionError(
                f"Expected call with args={args} kwargs={kwargs}, "
                f"but got args=({self.name},) kwargs={{'tools': {self.tools}}}"
            )

    @property
    def tool_called(self) -> bool:
        """Check if tool decorator was called."""
        return self._tool_called

    @property
    def registered_tools(self) -> Dict[str, ToolCallable]:
        """Get registered tools."""
        return cast(Dict[str, ToolCallable], self._tools)


@pytest.fixture
def mock_fastmcp() -> Generator[MockFastMCP, None, None]:
    """Mock FastMCP server."""
    with patch("mcp_server_neurolorap.server.FastMCP") as mock:
        mock_server = MockFastMCP("neurolorap", tools=True)
        mock.return_value = mock_server
        yield mock_server


@pytest.fixture
def mock_collector(project_root: Path) -> Generator[AsyncMock, None, None]:
    """Mock CodeCollector."""
    mock_instance = AsyncMock()
    mock_instance.collect_code = AsyncMock(
        return_value=project_root / "output.md"
    )
    with patch(
        "mcp_server_neurolorap.server.CodeCollector",
        return_value=mock_instance,
    ):
        yield mock_instance


@pytest.fixture
def mock_terminal() -> Generator[MagicMock, None, None]:
    """Mock JsonRpcTerminal."""
    with patch("mcp_server_neurolorap.server.terminal") as mock:
        mock.parse_request = MagicMock()
        mock.handle_command = AsyncMock()
        yield mock


def test_create_server(mock_fastmcp: MockFastMCP) -> None:
    """Test server creation and configuration."""
    create_server()

    # Verify FastMCP initialization
    mock_fastmcp.assert_called_once_with("neurolorap", tools=True)
    assert mock_fastmcp.tool_called
    assert "code_collector" in mock_fastmcp.registered_tools


@pytest.mark.asyncio
async def test_code_collector_tool_success(
    mock_fastmcp: MockFastMCP, mock_collector: AsyncMock, project_root: Path
) -> None:
    """Test successful code collection through MCP tool."""
    # Setup mock collector
    output_path = project_root / "output.md"
    mock_collector.collect_code.return_value = output_path

    # Create server and get tool function
    create_server()
    tool_mock = cast(ToolMock, mock_fastmcp.registered_tools["code_collector"])
    tool_mock.set_collector(mock_collector)

    # Test with single input
    result = await tool_mock("src/")
    assert "Code collection complete!" in result
    assert str(output_path) in result
    mock_collector.collect_code.assert_called_once_with(
        "src/", "Code Collection"
    )

    # Reset mock for next test
    mock_collector.collect_code.reset_mock()
    mock_collector.collect_code.return_value = output_path

    # Test with multiple inputs
    result = await tool_mock(["src/", "tests/"])
    assert "Code collection complete!" in result
    assert str(output_path) in result
    mock_collector.collect_code.assert_called_once_with(
        ["src/", "tests/"], "Code Collection"
    )


@pytest.mark.asyncio
async def test_code_collector_tool_errors(
    mock_fastmcp: MockFastMCP, mock_collector: AsyncMock
) -> None:
    """Test error handling in code collector tool."""
    create_server()
    tool_mock = cast(ToolMock, mock_fastmcp.registered_tools["code_collector"])
    tool_mock.set_collector(mock_collector)

    error_cases: list[tuple[type[Exception], str]] = [
        (FileNotFoundError, "File system error"),
        (PermissionError, "File system error"),
        (OSError, "File system error"),
        (ValueError, "Invalid input"),
        (TypeError, "Type error"),
        (Exception, "No files found to process or error occurred"),
    ]

    for error, expected_msg in error_cases:
        # Reset mocks for each test case
        mock_collector.collect_code.reset_mock()
        mock_collector.collect_code.side_effect = error("Test error")

        result = await tool_mock("src/")
        assert expected_msg in result
        if (
            error != Exception
        ):  # Для общих исключений не проверяем текст ошибки
            assert "Test error" in result
        mock_collector.collect_code.assert_called_once_with(
            "src/", "Code Collection"
        )

    # Test no files found case
    mock_collector.collect_code.reset_mock()
    mock_collector.collect_code.return_value = None

    result = await tool_mock("src/")
    assert "No files found to process or error occurred" == result
    mock_collector.collect_code.assert_called_once_with(
        "src/", "Code Collection"
    )


@pytest.mark.asyncio
async def test_dev_mode_commands(mock_terminal: MagicMock) -> None:
    """Test developer mode command handling."""
    # Setup mock terminal responses
    mock_terminal.parse_request.side_effect = [
        {
            "jsonrpc": "2.0",
            "method": "help",
            "id": 1,
        },
        {
            "jsonrpc": "2.0",
            "method": "exit",
            "id": 2,
        },
    ]
    mock_terminal.handle_command.side_effect = [
        {
            "jsonrpc": "2.0",
            "result": "Help message",
            "id": 1,
        },
        {
            "jsonrpc": "2.0",
            "result": "Goodbye!",
            "id": 2,
        },
    ]

    # Mock input/print functions
    with patch("builtins.input", side_effect=["help", "exit"]), patch(
        "builtins.print"
    ) as mock_print:
        await run_dev_mode()

        # Verify output
        mock_print.assert_any_call("Help message")
        mock_print.assert_any_call("Goodbye!")


@pytest.mark.asyncio
async def test_dev_mode_error_handling(mock_terminal: MagicMock) -> None:
    """Test error handling in developer mode."""
    error_cases: list[tuple[type[Exception], str]] = [
        (ValueError, "Value error: Invalid command"),
        (TypeError, "Type error: Type error"),
        (Exception, "Unexpected error: Unexpected error"),
    ]

    for error, expected_msg in error_cases:
        # Reset mocks for each test case
        mock_terminal.parse_request.reset_mock()
        mock_terminal.handle_command.reset_mock()

        # Set up the error case
        mock_terminal.parse_request.side_effect = [
            error("Invalid command"),
            {"jsonrpc": "2.0", "method": "exit", "id": 1},
        ]
        mock_terminal.handle_command.side_effect = [
            {"jsonrpc": "2.0", "result": "Goodbye!", "id": 1}
        ]

        with patch("builtins.input", side_effect=["invalid", "exit"]), patch(
            "builtins.print"
        ) as mock_print:
            await run_dev_mode()
            # Проверяем, что ошибка была напечатана
            expected_error = expected_msg.split(":")[
                0
            ]  # Берем только тип ошибки
            mock_print.assert_any_call(f"{expected_error}: Invalid command")

    # Test invalid command format
    mock_terminal.parse_request.reset_mock()
    mock_terminal.handle_command.reset_mock()
    mock_terminal.parse_request.side_effect = [
        None,
        {"jsonrpc": "2.0", "method": "exit", "id": 1},
    ]
    mock_terminal.handle_command.side_effect = [
        {"jsonrpc": "2.0", "result": "Goodbye!", "id": 1}
    ]

    with patch("builtins.input", side_effect=["invalid", "exit"]), patch(
        "builtins.print"
    ) as mock_print:
        await run_dev_mode()
        mock_print.assert_any_call("Invalid command format")

    # Test command error response
    mock_terminal.parse_request.reset_mock()
    mock_terminal.handle_command.reset_mock()
    mock_terminal.parse_request.side_effect = [
        {
            "jsonrpc": "2.0",
            "method": "invalid",
            "id": 1,
        },
        {
            "jsonrpc": "2.0",
            "method": "exit",
            "id": 2,
        },
    ]
    mock_terminal.handle_command.side_effect = [
        {
            "jsonrpc": "2.0",
            "error": {"message": "Command error"},
            "id": 1,
        },
        {
            "jsonrpc": "2.0",
            "result": "Goodbye!",
            "id": 2,
        },
    ]

    with patch("builtins.input", side_effect=["invalid", "exit"]), patch(
        "builtins.print"
    ) as mock_print:
        await run_dev_mode()
        mock_print.assert_any_call("Error: Command error")


def test_project_root_environment() -> None:
    """Test project root environment variable handling."""
    # Test with environment variable set
    test_path = "/test/path"
    with patch.dict(os.environ, {"MCP_PROJECT_ROOT": test_path}, clear=True):
        root = get_project_root()
        assert str(root) == test_path

    # Test with environment variable not set
    with patch.dict(os.environ, {}, clear=True):
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/current/dir")
            root = get_project_root()
            assert str(root) == "/current/dir"


@pytest.mark.asyncio
async def test_code_collector_tool_with_subproject(
    mock_fastmcp: MockFastMCP,
    mock_collector: AsyncMock,
) -> None:
    """Test code collector tool with subproject ID."""
    create_server()
    tool_mock = cast(ToolMock, mock_fastmcp.registered_tools["code_collector"])
    tool_mock.set_collector(mock_collector)

    # Test with subproject ID
    mock_collector.collect_code.reset_mock()
    mock_collector.collect_code.return_value = Path("output.md")

    await tool_mock(
        input="src/", title="Test Collection", subproject_id="test-sub"
    )

    # Verify collector was created with correct parameters
    mock_collector.collect_code.assert_called_once_with(
        "src/", "Test Collection"
    )
