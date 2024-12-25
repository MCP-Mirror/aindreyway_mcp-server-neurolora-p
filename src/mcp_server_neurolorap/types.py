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


@runtime_checkable
class FastMCPType(Protocol):
    """Protocol for FastMCP instance with dynamic attributes."""

    tool: Callable[[], Callable[[Callable[..., Any]], Callable[..., Any]]]
    __call__: Callable[..., Any]
    run: Callable[[], None] | None
    registered_tools: Dict[str, Callable[..., Coroutine[Any, Any, str]]]


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
