"""Tool definitions module.

This module contains centralized definitions for all tools, including their
descriptions, parameters, and schemas. These definitions are used by both
the MCP server and terminal interface.
"""

from typing import Annotated, List, Optional, TypedDict, Union

from pydantic import BaseModel, Field


class CollectInput(BaseModel):
    """Parameters for code collection."""

    input_path: Annotated[
        Union[str, List[str]],
        Field(
            default=".",
            description=(
                "Path or list of paths to collect code from. "
                "Use '.' for current directory. "
                "Supports both relative and absolute paths. "
                "Examples: 'src/main.py', ['src/main.py', 'tests/']"
            ),
        ),
    ]


class ShowTreeInput(BaseModel):
    """Parameters for project structure tree generation.
    This tool has no parameters as it always generates
    FULL_TREE_PROJECT_FILES.md in the .neurolora directory.
    """

    pass


class ImproveInput(BaseModel):
    """Parameters for code improvement."""

    input_path: Annotated[
        Union[str, List[str]],
        Field(
            default=".",
            description=(
                "Path or list of paths to analyze. "
                "Use '.' for current directory. "
                "Supports both relative and absolute paths. "
                "Examples: 'src/main.py', ['src/main.py', 'tests/']"
            ),
        ),
    ]


class RequestInput(BaseModel):
    """Parameters for code change requests."""

    input_path: Annotated[
        Union[str, List[str]],
        Field(
            default=".",
            description=(
                "Path or list of paths to analyze. "
                "Use '.' for current directory. "
                "Supports both relative and absolute paths. "
                "Examples: 'src/main.py', ['src/main.py', 'tests/']"
            ),
        ),
    ]
    request_text: Annotated[
        str,
        Field(
            default="",
            description=(
                "Natural language description of the changes. "
                "Example: 'Add error handling to all API calls'"
            ),
        ),
    ]


class CommandDefinition(TypedDict):
    """Type definition for command configuration."""

    name: str
    description: str
    handler_name: str
    requires_project_root: bool
    is_mcp_tool: bool
    requires_ai: bool
    model: Optional[type[BaseModel]]


# Command definitions that can be used by both MCP server and terminal
COMMANDS: dict[str, CommandDefinition] = {
    "help": {
        "name": "help",
        "description": "help: Show this help message",
        "handler_name": "cmd_help",
        "requires_project_root": False,
        "is_mcp_tool": False,
        "requires_ai": False,
        "model": None,
    },
    "list_tools": {
        "name": "list_tools",
        "description": "list_tools: List available MCP tools",
        "handler_name": "cmd_list_tools",
        "requires_project_root": False,
        "is_mcp_tool": False,
        "requires_ai": False,
        "model": None,
    },
    "collect": {
        "name": "collect",
        "description": (
            "collect: Generate code documentation with syntax highlighting"
        ),
        "handler_name": "cmd_collect",
        "requires_project_root": False,
        "is_mcp_tool": True,
        "requires_ai": False,
        "model": CollectInput,
    },
    "showtree": {
        "name": "showtree",
        "description": (
            "showtree: Generate project files tree structure in .neurolora"
        ),
        "handler_name": "cmd_project_structure_reporter",
        "requires_project_root": True,
        "is_mcp_tool": True,
        "requires_ai": False,
        "model": ShowTreeInput,
    },
    "improve": {
        "name": "improve",
        "description": (
            "improve: Analyze code and suggest AI-powered improvements. "
            "Note: This operation may take up to 5 minutes to complete."
        ),
        "handler_name": "cmd_improve",
        "requires_project_root": True,
        "is_mcp_tool": True,
        "requires_ai": True,
        "model": ImproveInput,
    },
    "request": {
        "name": "request",
        "description": (
            "request: Process code changes using natural language"
        ),
        "handler_name": "cmd_request",
        "requires_project_root": True,
        "is_mcp_tool": True,
        "requires_ai": True,
        "model": RequestInput,
    },
    "reload": {
        "name": "reload",
        "description": "reload: Reload the server to apply code changes",
        "handler_name": "cmd_reload",
        "requires_project_root": False,
        "is_mcp_tool": False,
        "requires_ai": False,
        "model": None,
    },
    "exit": {
        "name": "exit",
        "description": "exit: Exit the terminal",
        "handler_name": "cmd_exit",
        "requires_project_root": False,
        "is_mcp_tool": False,
        "requires_ai": False,
        "model": None,
    },
}


# Helper functions to get filtered commands
def get_mcp_tools() -> dict[str, CommandDefinition]:
    """Get MCP tools only."""
    return {name: cmd for name, cmd in COMMANDS.items() if cmd["is_mcp_tool"]}


def get_terminal_commands() -> dict[str, CommandDefinition]:
    """Get terminal-only commands."""
    return {
        name: cmd for name, cmd in COMMANDS.items() if not cmd["is_mcp_tool"]
    }


def get_available_commands(
    ai_configured: bool,
) -> dict[str, CommandDefinition]:
    """Get all available commands based on AI configuration."""
    return {
        name: cmd
        for name, cmd in COMMANDS.items()
        if not cmd["requires_ai"] or ai_configured
    }
