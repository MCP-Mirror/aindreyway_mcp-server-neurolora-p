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
)

from mcp.types import TextContent, Tool

T = TypeVar("T")

ListToolsHandler = Callable[[], Coroutine[Any, Any, List[Tool]]]
CallToolHandler = Callable[
    [str, Union[Dict[str, Any], None]], Coroutine[Any, Any, List[TextContent]]
]


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
