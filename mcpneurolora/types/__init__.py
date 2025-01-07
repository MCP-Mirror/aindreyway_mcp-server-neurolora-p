"""Type definitions for external packages."""

from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    TypeVar,
    Union,
    runtime_checkable,
)

from mcp.server.fastmcp import Context as McpContext
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from .vscode import ServerConfig, ServerEnvConfig, VsCodeSettings


class ClinesConfig(TypedDict):
    """VSCode settings structure for Clines."""

    mcpServers: Dict[str, ServerConfig]


class CommandType(Enum):
    """Types of commands supported by the router."""

    COLLECT = auto()
    IMPROVE = auto()
    REQUEST = auto()
    HELP = auto()
    UNKNOWN = auto()


class RouterResponse(BaseModel):
    """Response from command router."""

    command_type: CommandType
    confidence: float = Field(ge=0.0, le=1.0)
    args: Dict[str, Any]
    reason: str
    command: Optional[str] = None


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


@runtime_checkable
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


# Re-export MCP Context type
Context = McpContext

# Type for MCP call_tool function arguments
CallToolArgs = Dict[str, Any]

# Type for MCP call_tool function result
CallToolResult = Sequence[TextContent | ImageContent | EmbeddedResource]

__all__ = [
    "CommandType",
    "RouterResponse",
    "Context",
    "CallToolArgs",
    "CallToolResult",
    "ClinesConfig",
    "ServerConfig",
    "ServerEnvConfig",
    "VsCodeSettings",
    "FastMCPType",
    "ToolFunction",
    "ListToolsHandler",
    "CallToolHandler",
    "ServerProtocol",
    "TextContent",
    "Tool",
]
