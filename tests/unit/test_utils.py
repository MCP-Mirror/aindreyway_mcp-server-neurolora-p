"""Common test utilities and fixtures."""

from typing import Any, Callable, Coroutine, Dict, Generator, TypeVar, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
            logger.debug(
                "Arguments: input=%s, title=%s, subproject_id=%s",
                input_val,
                title,
                subproject_id,
            )
            logger.info("Starting code collection")
            logger.debug("Input: %s", input_val)
            logger.debug("Title: %s", title)
            logger.debug("Subproject ID: %s", subproject_id)

            if self.side_effect is not None:
                raise self.side_effect

            if not self._collector:
                # Return mock result for initialization tests
                return "Code collection complete!\nOutput file: output.md"

            output = await self._collector.collect_code(input_val, title)
            if output is None:
                return "No files found to process or error occurred"

            return f"Code collection complete!\nOutput file: {output}"
        except Exception as e:
            error_msg = f"Unexpected error collecting code: {e}"
            logger.error(error_msg, exc_info=True)
            return "No files found to process or error occurred"


class MockFastMCP:
    """Mock class for FastMCP."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.tools: Dict[str, ToolMock] = {}
        self.tool_called = False
        self._run_mock = MagicMock()
        self.info = MagicMock()
        self.debug = MagicMock()
        self.error = MagicMock()
        self._tool_mock = MagicMock()

    def set_tool_error(self, error: Exception) -> None:
        """Set error to be raised during tool registration."""
        self._tool_mock.side_effect = error

    def tool(self, *args: Any, **kwargs: Any) -> Callable[[T], T]:
        """Tool decorator."""
        if hasattr(self._tool_mock, "side_effect"):
            raise self._tool_mock.side_effect

        def decorator(func: T) -> T:
            tool_mock = ToolMock()
            self.tools[func.__name__] = tool_mock
            self.tool_called = True
            return cast(T, tool_mock)

        return decorator

    def run(self) -> None | Callable[[], None]:
        """Run the server."""
        return self._run_mock


@pytest.fixture
def mock_fastmcp() -> Generator[MockFastMCP, None, None]:
    """Mock FastMCP server."""
    with patch("mcp_server_neurolorap.server.FastMCP") as mock:
        mock_server = MockFastMCP("neurolorap")
        mock.return_value = mock_server
        yield mock_server


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
