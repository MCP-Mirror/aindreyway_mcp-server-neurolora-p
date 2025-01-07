"""Type definitions for NeuroLoRA MCP server."""

import asyncio
from typing import Any, Callable, Coroutine, Dict, List, Optional, Protocol

from mcp.server.fastmcp import Context
from mcp.types import Resource, ResourceTemplate, TextContent, Tool
from pydantic import AnyUrl


class ServerMethod(Protocol):
    def __call__(self, handler: Any) -> Any: ...


class ServerListTools(Protocol):
    def __call__(
        self,
        handler: Callable[
            [],
            List[Tool] | asyncio.Future[List[Tool]] | Coroutine[Any, Any, List[Tool]],
        ],
    ) -> Callable[[], List[Tool]]: ...


class ServerCallTool(Protocol):
    def __call__(
        self,
        handler: Callable[
            [str, Optional[Dict[str, Any]], Optional[Context]],
            List[TextContent]
            | asyncio.Future[List[TextContent]]
            | Coroutine[Any, Any, List[TextContent]],
        ],
    ) -> Callable[
        [str, Optional[Dict[str, Any]], Optional[Context]], List[TextContent]
    ]: ...


class ServerListResources(Protocol):
    def __call__(
        self,
        handler: Callable[
            [],
            List[Resource]
            | asyncio.Future[List[Resource]]
            | Coroutine[Any, Any, List[Resource]],
        ],
    ) -> Callable[[], List[Resource]]: ...


class ServerListResourceTemplates(Protocol):
    def __call__(
        self,
        handler: Callable[
            [],
            List[ResourceTemplate]
            | asyncio.Future[List[ResourceTemplate]]
            | Coroutine[Any, Any, List[ResourceTemplate]],
        ],
    ) -> Callable[[], List[ResourceTemplate]]: ...


class ServerReadResource(Protocol):
    def __call__(
        self,
        handler: Callable[
            [AnyUrl], str | asyncio.Future[str] | Coroutine[Any, Any, str]
        ],
    ) -> Callable[[AnyUrl], str]: ...
