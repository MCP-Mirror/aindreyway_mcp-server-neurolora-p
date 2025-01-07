"""NeuroLoRA MCP server implementation."""

import os
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .log_utils import get_logger, LogCategory
from .mcp_server import run_mcp_server
from .prompts import route_command
from .server_utils import (
    create_uri,
    ensure_project_root_env,
    get_project_root,
    load_prompt,
    parse_prompt_uri,
)
from .terminal import JsonRpcTerminal
from .terminal_server import run_terminal_server
from .tools.definitions import COMMANDS
from .tools.executor import ToolExecutor
from .utils.validation import (
    validate_arguments,
    validate_command,
    validate_command_model,
)

# Get module logger
logger = get_logger(__name__, LogCategory.SERVER)

__all__ = [
    "run_terminal_server",
    "run_mcp_server",
    "create_uri",
    "ensure_project_root_env",
    "get_project_root",
    "load_prompt",
    "parse_prompt_uri",
    "Server",
    "JsonRpcTerminal",
    "ToolExecutor",
    "stdio_server",
    "logger",
    "route_command",
    "COMMANDS",
    "os",
    "validate_arguments",
    "validate_command",
    "validate_command_model",
]
