"""MCP server implementation for NeuroLoRA."""

import os
from typing import cast

from mcp.server import Server
from mcp.server.stdio import stdio_server

from .log_utils import LogCategory, get_logger
from .server_handlers import (
    call_tool_fn,
    list_resources_fn,
    list_resource_templates_fn,
    list_tools_fn,
    read_resource_fn,
)
from .server_types import (
    ServerCallTool,
    ServerListResources,
    ServerListResourceTemplates,
    ServerListTools,
    ServerReadResource,
)
from .server_utils import ensure_project_root_env, wrap_async_fn

# Get module logger
logger = get_logger(__name__, LogCategory.SERVER)


async def run_mcp_server() -> None:
    """Initialize and run the main MCP server.

    Creates and configures the main MCP server instance for handling
    production requests. Registers and prepares all available tools.
    """
    ensure_project_root_env()

    server = Server("neurolora")
    server_list_tools = cast(ServerListTools, server.list_tools())  # type: ignore
    server_call_tool = cast(ServerCallTool, server.call_tool())  # type: ignore
    server_list_resources = cast(
        ServerListResources, server.list_resources()  # type: ignore
    )
    server_list_templates = cast(
        ServerListResourceTemplates,
        server.list_resource_templates(),  # type: ignore
    )
    server_read_resource = cast(
        ServerReadResource, server.read_resource()  # type: ignore
    )

    # Register handlers
    server_list_tools(wrap_async_fn(list_tools_fn))
    server_call_tool(wrap_async_fn(call_tool_fn))
    server_list_resources(wrap_async_fn(list_resources_fn))
    server_list_templates(wrap_async_fn(list_resource_templates_fn))
    server_read_resource(wrap_async_fn(read_resource_fn))

    # Get timeout from environment or use default (5 minutes)
    timeout_ms = int(os.environ.get("AI_TIMEOUT_MS", "300000"))

    # Set timeout in environment for stdio server
    os.environ["JSONRPC_TIMEOUT_MS"] = str(timeout_ms)

    # Create initialization options
    options = server.create_initialization_options()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)
