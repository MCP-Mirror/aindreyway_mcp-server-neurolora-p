"""MCP prompts for command routing and templates."""

from pathlib import Path
from typing import Any, Callable, List, TypeVar

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import Prompt

from ..types import CommandType, RouterResponse
from .commands import (
    CommandHelpInput,
    CommandHelpOutput,
    CommandMenuItem,
    CommandRoutingInput,
    CommandRoutingOutput,
    CommandSuggestionInput,
    CommandSuggestionOutput,
)

T = TypeVar("T")
PromptFunction = Callable[..., Any]
PromptDecorator = Callable[[PromptFunction], PromptFunction]

__all__ = [
    "CommandHelpInput",
    "CommandHelpOutput",
    "CommandMenuItem",
    "CommandSuggestionInput",
    "CommandSuggestionOutput",
    "CommandRoutingInput",
    "CommandRoutingOutput",
    "route_command",
    "get_command_help",
    "format_error",
    "mcp",
]


def load_prompt(name: str) -> str:
    """Load prompt content from file."""
    prompt_path = Path(__file__).parent / f"{name}.prompt.md"
    return prompt_path.read_text()


# Initialize FastMCP
mcp = FastMCP("neurolora")


# Add command patterns prompt
async def commands_prompt() -> str:
    """Command patterns prompt.

    This prompt contains command patterns for routing natural language input
    to appropriate MCP commands. The patterns are defined in commands.prompt.md
    and include both English and Russian language triggers.
    """
    return load_prompt("commands")


mcp._prompt_manager.add_prompt(
    Prompt.from_function(commands_prompt, name="commands")
)


@mcp.prompt()
async def route_command(text: str) -> RouterResponse:
    """Route natural language input to appropriate command.

    You are a command router for the NeuroLoRA MCP server.
    Analyze the user's input and determine which MCP command to execute.
    The command patterns are defined in commands.prompt.md.

    User input: {text}

    Return a RouterResponse with:
    - command: The selected command name
    - confidence: How confident you are (0.0-1.0)
    - reason: Explanation for the selection
    """
    # This implementation will be provided by the MCP prompt decorator
    # but we need to return something to satisfy the type checker
    return RouterResponse(
        command="improve", confidence=0.0, reason="Placeholder implementation"
    )


@mcp.prompt()
async def get_command_help(command: CommandType) -> str:
    """Get help text for a specific command.

    You are a helpful assistant providing information about NeuroLoRA MCP
    commands.
    Explain what the command does and how to use it.

    Command: {command}
    """
    # This implementation will be provided by the MCP prompt decorator
    # but we need to return something to satisfy the type checker
    return "Placeholder help text"


@mcp.prompt()
async def format_error(error: str) -> List[str]:
    """Format error message for user display.

    You are a helpful assistant explaining errors in a clear way.
    Break down the error message and suggest possible solutions.

    Error: {error}

    Return a list of messages:
    1. What the error means
    2. Possible causes
    3. Suggested solutions
    """
    # This implementation will be provided by the MCP prompt decorator
    # but we need to return something to satisfy the type checker
    return [
        "Placeholder error explanation",
        "Placeholder cause",
        "Placeholder solution",
    ]
