"""Type definitions for the MCP server."""

from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Protocol,
    TypeVar,
    Union,
    runtime_checkable,
)

from mcp.types import TextContent, Tool

T = TypeVar("T")

ListToolsHandler = Callable[[], Coroutine[Any, Any, List[Tool]]]
CallToolHandler = Callable[
    [str, Union[Dict[str, Any], None]], Coroutine[Any, Any, List[TextContent]]
]

# Type for async functions that can be used as tools
ToolFunction = Callable[..., Coroutine[Any, Any, str]]


@runtime_checkable
class FastMCPType(Protocol):
    """Protocol for FastMCP instance with dynamic attributes."""

    name: str
    # The tool decorator type is complex due to its dual nature:
    # 1. It can be called directly with a function: @tool
    # 2. It can be called with config args: @tool(name="x", description="y")
    # This makes static typing challenging, so we use Any
    tool: Any
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
