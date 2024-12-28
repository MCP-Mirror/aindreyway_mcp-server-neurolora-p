"""Type definitions for the MCP server."""

from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    TypeVar,
    Union,
    runtime_checkable,
)

from mcp.types import TextContent, Tool
from pydantic import BaseModel

__all__ = [
    "FastMCPType",
    "ToolFunction",
    "ListToolsHandler",
    "CallToolHandler",
    "ServerProtocol",
    "Context",
    "RouterResponse",
    "CommandType",
]

CommandType = Literal["collect", "improve", "request", "showtree"]


class RouterResponse(BaseModel):
    """Response from command router."""

    command: CommandType
    confidence: float
    reason: str


T = TypeVar("T")

ListToolsHandler = Callable[[], Coroutine[Any, Any, List[Tool]]]
CallToolHandler = Callable[
    [str, Union[Dict[str, Any], None]], Coroutine[Any, Any, List[TextContent]]
]

# Type for async functions that can be used as tools
ToolFunction = Callable[..., Coroutine[Any, Any, str]]

# Type for tool decorator configuration
ToolDecoratorConfig = Dict[str, Union[str, None]]


@runtime_checkable
class Context(Protocol):
    """Protocol for MCP context with progress reporting."""

    def info(self, message: str) -> None:
        """Log an informational message.

        Args:
            message: Message to log
        """
        ...

    async def report_progress(
        self,
        progress: float,
        total: Optional[float] = None,
    ) -> None:
        """Report progress of an operation.

        Args:
            progress: Current progress value (0.0 to 1.0 or raw value)
            total: Optional total value for raw progress values
        """
        ...


@runtime_checkable
class FastMCPType(Protocol):
    """Protocol for FastMCP instance with dynamic attributes."""

    name: str

    def tool(
        self,
        name: str | None = None,
        *,
        description: str | None = None,
    ) -> Callable[[ToolFunction], ToolFunction]:
        """Tool decorator for registering MCP tools."""
        ...

    def prompt(
        self,
        name: str | None = None,
        *,
        description: str | None = None,
    ) -> Callable[[ToolFunction], ToolFunction]:
        """Prompt decorator for registering MCP prompts."""
        ...

    run: Callable[[], None] | None
    tool_called: bool
    tools: Dict[str, ToolFunction]


class ServerProtocol(Protocol):
    """Protocol for Server class."""

    def list_tools(self) -> Callable[[ListToolsHandler], ListToolsHandler]:
        """List tools decorator."""
        ...

    def call_tool(self) -> Callable[[CallToolHandler], CallToolHandler]:
        """Call tool decorator."""
        ...

    async def run(self, reader: Any, writer: Any, options: Any) -> None:
        """Run the server."""
        ...
