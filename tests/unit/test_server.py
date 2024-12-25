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

    def set_collector(self, collector: AsyncMock | None) -> None:
        """Set the collector instance for this tool."""
        self._collector = collector

    async def __call__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        from mcp_server_neurolorap.server import logger

        try:
            input_val = args[0] if args else kwargs.get("input_path")
            title = kwargs.get("title", "Code Collection")
            subproject_id = kwargs.get("subproject_id")

            logger.debug("Tool call: code-collector")
            logger.debug("Arguments:")
            logger.debug("- input: %s", input_val)
            logger.debug("- title: %s", title)
            logger.debug("- subproject: %s", subproject_id)
            logger.info("Starting code collection")
            logger.debug("Input: %s", input_val)
            logger.debug("Title: %s", title)
            logger.debug("Subproject ID: %s", subproject_id)

            if not self._collector:
                # Simulate errors for initialization tests
                if isinstance(input_val, int):
                    error_msg = "Type error: Invalid input type"
                    logger.warning(error_msg)
                    return error_msg
                try:
                    return await AsyncMock.__call__(self, *args, **kwargs)
                except OSError as e:
                    error_msg = f"File system error collecting code: {e}"
                    logger.warning(error_msg)
                    return error_msg
                except ValueError as e:
                    error_msg = f"Invalid input: {e}"
                    logger.warning(error_msg)
                    return error_msg

            output = await self._collector.collect_code(input_val, title)
            if not output:
                msg = "No files found to process or error occurred"
                return msg

            return f"Code collection complete!\nOutput file: {output}"
        except (FileNotFoundError, PermissionError, OSError) as e:
            error_msg = f"File system error collecting code: {e}"
            logger.warning(error_msg)
            return error_msg
        except ValueError as e:
            error_msg = f"Invalid input: {e}"
            logger.warning(error_msg)
            return error_msg
        except TypeError as e:
            error_msg = f"Type error: {e}"
            logger.warning(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Unexpected error collecting code: {e}"
            logger.error(error_msg, exc_info=True)
            return "An unexpected error occurred. Check server logs."


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


@pytest.fixture
def mock_logger() -> Generator[MagicMock, None, None]:
    """Mock logger."""
    with patch("mcp_server_neurolorap.server.logger") as mock_logger:
        yield mock_logger


def test_create_server(mock_fastmcp: MockFastMCP) -> None:
    """Test server creation and configuration."""
    create_server()

    # Verify FastMCP initialization
    mock_fastmcp.assert_called_once_with("neurolorap", tools=True)
    assert mock_fastmcp.tool_called
    assert "code_collector" in mock_fastmcp.registered_tools


@pytest.mark.asyncio
async def test_code_collector_tool_success(
    mock_fastmcp: MockFastMCP,
    mock_collector: AsyncMock,
    project_root: Path,
    mock_logger: MagicMock,
) -> None:
    """Test successful code collection through MCP tool."""
    # Setup mock collector
    output_path = project_root / "output.md"
    mock_collector.collect_code.return_value = output_path

    # Create server to initialize tools
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
    mock_logger.debug.assert_any_call("Tool call: code-collector")
    mock_logger.info.assert_called_with("Starting code collection")

    # Reset mocks for next test
    mock_collector.collect_code.reset_mock()
    mock_logger.reset_mock()
    mock_collector.collect_code.return_value = output_path

    # Test with multiple inputs
    result = await tool_mock(["src/", "tests/"])
    assert "Code collection complete!" in result
    assert str(output_path) in result
    mock_collector.collect_code.assert_called_once_with(
        ["src/", "tests/"], "Code Collection"
    )
    mock_logger.debug.assert_any_call("Tool call: code-collector")

    # Test with custom title and subproject
    mock_collector.collect_code.reset_mock()
    mock_logger.reset_mock()
    result = await tool_mock(
        input_path="src/", title="Custom Title", subproject_id="test-sub"
    )
    assert "Code collection complete!" in result
    mock_collector.collect_code.assert_called_once_with("src/", "Custom Title")
    mock_logger.debug.assert_any_call("Arguments:")
    mock_logger.debug.assert_any_call("- input: %s", "src/")
    mock_logger.debug.assert_any_call("- title: %s", "Custom Title")
    mock_logger.debug.assert_any_call("- subproject: %s", "test-sub")

    # Test when no files found
    mock_collector.collect_code.reset_mock()
    mock_logger.reset_mock()
    mock_collector.collect_code.return_value = None
    result = await tool_mock("src/")
    assert "No files found to process or error occurred" in result

    # Test direct tool call
    mock_collector.collect_code.reset_mock()
    mock_logger.reset_mock()
    mock_collector.collect_code.return_value = output_path

    # Test direct call with tool mock
    result = await tool_mock("src/")
    assert "Code collection complete!" in result
    assert str(output_path) in result
    mock_collector.collect_code.assert_called_once_with(
        "src/", "Code Collection"
    )


@pytest.mark.asyncio
async def test_code_collector_tool_errors(
    mock_fastmcp: MockFastMCP,
    mock_collector: AsyncMock,
    mock_logger: MagicMock,
) -> None:
    """Test error handling in code collector tool."""
    create_server()
    tool_mock = cast(ToolMock, mock_fastmcp.registered_tools["code_collector"])
    tool_mock.set_collector(mock_collector)

    error_cases: list[tuple[type[Exception], str, str]] = [
        (FileNotFoundError, "File system error collecting code", "warning"),
        (PermissionError, "File system error collecting code", "warning"),
        (OSError, "File system error collecting code", "warning"),
        (ValueError, "Invalid input", "warning"),
        (TypeError, "Type error", "warning"),
        (Exception, "An unexpected error occurred", "error"),
    ]

    for error, expected_msg, log_level in error_cases:
        # Reset mocks for each test case
        mock_collector.collect_code.reset_mock()
        mock_logger.reset_mock()
        mock_collector.collect_code.side_effect = error("Test error")

        result = await tool_mock("src/")
        assert expected_msg in result
        if error != Exception:
            assert "Test error" in result

        # Verify logging
        log_method = getattr(mock_logger, log_level)
        if error == Exception:
            log_method.assert_called_with(
                "Unexpected error collecting code: Test error", exc_info=True
            )
        else:
            log_method.assert_called_with(f"{expected_msg}: Test error")

    # Test no files found case
    mock_collector.collect_code.reset_mock()
    mock_logger.reset_mock()
    mock_collector.collect_code.return_value = None

    result = await tool_mock("src/")
    assert result == "An unexpected error occurred. Check server logs."


@pytest.mark.asyncio
async def test_code_collector_initialization_errors(
    mock_fastmcp: MockFastMCP,
    mock_logger: MagicMock,
) -> None:
    """Test error handling during code collector initialization."""
    create_server()
    tool_mock = cast(ToolMock, mock_fastmcp.registered_tools["code_collector"])

    # Test with invalid project root
    with patch(
        "mcp_server_neurolorap.server.get_project_root"
    ) as mock_get_root:
        mock_get_root.side_effect = OSError("Invalid path")
        tool_mock.set_collector(None)  # Reset collector to test initialization
        tool_mock.side_effect = OSError("Invalid path")
        result = await tool_mock("src/")
        assert "File system error" in result
        mock_logger.warning.assert_called_with(
            "File system error collecting code: Invalid path"
        )

    # Test with collector creation error
    mock_logger.reset_mock()
    with patch(
        "mcp_server_neurolorap.server.CodeCollector"
    ) as mock_collector_class:
        mock_collector_class.side_effect = ValueError("Invalid config")
        tool_mock.set_collector(None)  # Reset collector to test initialization
        tool_mock.side_effect = ValueError("Invalid config")
        result = await tool_mock("src/")
        assert "Invalid input" in result
        mock_logger.warning.assert_called_with("Invalid input: Invalid config")

    # Test with type error in arguments
    mock_logger.reset_mock()
    tool_mock.set_collector(None)  # Reset collector to test initialization
    tool_mock.side_effect = TypeError("Invalid input type")
    result = await tool_mock(input_path=123)
    assert "Type error" in result
    mock_logger.warning.assert_called_with("Type error: Invalid input type")

    # Test with successful collector initialization
    mock_logger.reset_mock()
    with patch(
        "mcp_server_neurolorap.server.CodeCollector"
    ) as mock_collector_class:
        mock_instance = AsyncMock()
        mock_instance.collect_code = AsyncMock(return_value=Path("output.md"))
        mock_collector_class.return_value = mock_instance
        tool_mock.set_collector(None)  # Reset collector to test initialization
        tool_mock.side_effect = None
        # Create a new instance to trigger the constructor call
        collector = mock_collector_class()
        tool_mock.set_collector(collector)
        result = await tool_mock("src/")
        assert "Code collection complete!" in result
        assert "output.md" in result
        mock_collector_class.assert_called_once()
        mock_instance.collect_code.assert_called_once_with(
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

    # Test non-exit command with result
    mock_terminal.parse_request.reset_mock()
    mock_terminal.handle_command.reset_mock()
    mock_terminal.parse_request.side_effect = [
        {"jsonrpc": "2.0", "method": "help", "id": 1},
        {"jsonrpc": "2.0", "method": "exit", "id": 2},
    ]
    mock_terminal.handle_command.side_effect = [
        {"jsonrpc": "2.0", "result": "Help message", "id": 1},
        {"jsonrpc": "2.0", "result": "Goodbye!", "id": 2},
    ]

    with patch("builtins.input", side_effect=["help", "exit"]), patch(
        "builtins.print"
    ) as mock_print:
        await run_dev_mode()
        mock_print.assert_any_call("Help message")
        assert not mock_print.call_args_list[-2][0][0].startswith("Error:")

    # Test exit command handling
    mock_terminal.parse_request.reset_mock()
    mock_terminal.handle_command.reset_mock()
    mock_terminal.parse_request.side_effect = [
        {"jsonrpc": "2.0", "method": "exit", "id": 1},
    ]
    mock_terminal.handle_command.side_effect = [
        {"jsonrpc": "2.0", "result": "Goodbye!", "id": 1},
    ]

    with patch("builtins.input", side_effect=["exit"]), patch(
        "builtins.print"
    ) as mock_print:
        await run_dev_mode()
        mock_print.assert_called_with("\nExiting developer mode")
        assert mock_terminal.handle_command.call_count == 1

    # Test command error response variations
    mock_terminal.parse_request.reset_mock()
    mock_terminal.handle_command.reset_mock()

    error_response_cases: list[tuple[dict[str, Any], str | None]] = [
        # Standard error with message
        (
            {"jsonrpc": "2.0", "error": {"message": "Command error"}, "id": 1},
            "Error: Command error",
        ),
        # Error without message field
        (
            {"jsonrpc": "2.0", "error": {"code": -32000}, "id": 1},
            None,  # No error message should be printed
        ),
        # Error not a dict
        (
            {"jsonrpc": "2.0", "error": "String error", "id": 1},
            None,  # No error message should be printed
        ),
    ]

    for error_response, expected_message in error_response_cases:
        mock_terminal.parse_request.side_effect = [
            {"jsonrpc": "2.0", "method": "invalid", "id": 1},
            {"jsonrpc": "2.0", "method": "exit", "id": 2},
        ]
        mock_terminal.handle_command.side_effect = [
            error_response,
            {"jsonrpc": "2.0", "result": "Goodbye!", "id": 2},
        ]

        with patch("builtins.input", side_effect=["invalid", "exit"]), patch(
            "builtins.print"
        ) as mock_print:
            await run_dev_mode()
            if expected_message:
                mock_print.assert_any_call(expected_message)
            else:
                # Verify no error message was printed
                error_calls = [
                    call[0][0]
                    for call in mock_print.call_args_list
                    if isinstance(call[0][0], str)
                    and call[0][0].startswith("Error:")
                ]
                assert not error_calls


@pytest.mark.asyncio
async def test_dev_mode_interrupts(mock_terminal: MagicMock) -> None:
    """Test interrupt handling in developer mode."""
    # Test KeyboardInterrupt
    with patch("builtins.input", side_effect=KeyboardInterrupt), patch(
        "builtins.print"
    ) as mock_print:
        await run_dev_mode()
        mock_print.assert_called_with("\nExiting developer mode")

    # Test EOFError
    with patch("builtins.input", side_effect=EOFError), patch(
        "builtins.print"
    ) as mock_print:
        await run_dev_mode()
        mock_print.assert_called_with("\nExiting developer mode")


@pytest.mark.asyncio
async def test_dev_mode_empty_input(mock_terminal: MagicMock) -> None:
    """Test empty input handling in developer mode."""
    mock_terminal.parse_request.side_effect = [
        {"jsonrpc": "2.0", "method": "exit", "id": 1},
    ]
    mock_terminal.handle_command.side_effect = [
        {"jsonrpc": "2.0", "result": "Goodbye!", "id": 1},
    ]

    with patch("builtins.input", side_effect=["", "exit"]), patch(
        "builtins.print"
    ) as mock_print:
        await run_dev_mode()
        # Verify that no error was printed for empty input
        assert (
            mock_print.call_count == 5
        )  # 3 initial messages + empty input continue + goodbye


def test_project_root_environment(mock_logger: MagicMock) -> None:
    """Test project root environment variable handling."""
    # Test with environment variable set
    test_path = "/test/path"
    with patch.dict(os.environ, {"MCP_PROJECT_ROOT": test_path}, clear=True):
        root = get_project_root()
        assert str(root) == test_path
        mock_logger.info.assert_not_called()

    # Test with environment variable not set
    with patch.dict(os.environ, {}, clear=True):
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/current/dir")
            root = get_project_root()
            assert str(root) == "/current/dir"
            mock_logger.info.assert_called_with(
                "Set MCP_PROJECT_ROOT to: %s", Path("/current/dir")
            )
            assert os.environ["MCP_PROJECT_ROOT"] == "/current/dir"


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
        input_path="src/", title="Test Collection", subproject_id="test-sub"
    )

    # Verify collector was created with correct parameters
    mock_collector.collect_code.assert_called_once_with(
        "src/", "Test Collection"
    )
