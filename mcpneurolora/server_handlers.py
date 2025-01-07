"""Handlers for NeuroLoRA MCP server."""

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context
from mcp.types import Resource, ResourceTemplate, TextContent, Tool
from pydantic import AnyUrl

from .log_utils import LogCategory, get_logger
from .prompts import CommandHelpInput, CommandSuggestionInput, route_command
from .server_utils import (
    create_uri,
    ensure_project_root_env,
    get_project_root,
    load_prompt,
    parse_prompt_uri,
)
from .tools.definitions import (
    COMMANDS,
    CollectInput,
    ImproveInput,
    RequestInput,
    ShowTreeInput,
    get_mcp_tools,
)
from .tools.executor import ToolExecutor
from .types import RouterResponse
from .utils.validation import (
    validate_arguments,
    validate_command,
    validate_command_model,
)

# Get module logger
logger = get_logger(__name__, LogCategory.SERVER)


async def _try_route_command(name: str) -> str:
    """Try to route command if it's not internal.

    Args:
        name: Command name to route

    Returns:
        str: Routed command name or original name

    Raises:
        Exception: If command routing fails
    """
    if not name.startswith("_"):
        response: RouterResponse = await route_command(name)
        if response.confidence >= 0.7:
            logger.info(
                "Routed '%s' to '%s' (conf: %.2f)",
                name,
                response.command,
                response.confidence,
            )
            if response.command is None:
                logger.warning("Command routing returned None for '%s'", name)
                return name
            return response.command
    return name


async def _execute_command(name: str, validated: Any, executor: ToolExecutor) -> str:
    """Execute appropriate command based on name.

    Args:
        name: Command name
        validated: Validated arguments
        executor: Tool executor instance

    Returns:
        str: Command result

    Raises:
        ValueError: If command implementation is missing
    """
    if name == "collect":
        if not isinstance(validated, CollectInput):
            raise ValueError("Invalid model type for collect")
        return await executor.execute_code_collector(validated.input_path)
    elif name == "showtree":
        if not isinstance(validated, ShowTreeInput):
            raise ValueError("Invalid model type for showtree")
        return await executor.execute_project_structure_reporter(
            "FULL_TREE_PROJECT_FILES.md"
        )
    elif name == "improve":
        if not isinstance(validated, ImproveInput):
            raise ValueError("Invalid model type for improve")
        return await executor.execute_improve(validated.input_path)
    elif name == "request":
        if not isinstance(validated, RequestInput):
            raise ValueError("Invalid model type for request")
        return await executor.execute_request(
            validated.input_path,
            validated.request_text,
        )
    else:
        raise ValueError(f"Tool implementation missing: {name}")


async def list_tools_fn() -> List[Tool]:
    """List available tools."""
    # Get only MCP tools
    mcp_tools = get_mcp_tools()
    return [
        Tool(
            name=cmd_def["name"],
            description=cmd_def["description"],
            inputSchema=(
                cmd_def["model"].model_json_schema() if cmd_def["model"] else {}
            ),
        )
        for cmd_def in mcp_tools.values()
    ]


async def call_tool_fn(
    name: str,
    arguments: Optional[Dict[str, Any]] = None,
    context: Optional[Context] = None,
    **kwargs: Any,
) -> List[TextContent]:
    """Call a tool.

    Args:
        name: Tool name
        arguments: Tool arguments
        context: Tool context
        kwargs: Additional arguments

    Returns:
        List of text content

    Raises:
        Exception: If tool execution fails
    """
    try:
        # First try routing
        routed_name = await _try_route_command(name)

        # Validate command and setup
        validate_command(routed_name)
        if COMMANDS[routed_name]["requires_project_root"]:
            ensure_project_root_env()

        # Create executor
        executor = ToolExecutor(
            project_root=get_project_root(),
            context=context,
        )

        # Get and validate model
        model_cls = validate_command_model(routed_name)
        validated = validate_arguments(model_cls, arguments or {})

        # Execute appropriate command
        result = await _execute_command(routed_name, validated, executor)
        return [TextContent(type="text", text=result)]

    except Exception as e:
        error_msg = f"Error executing tool: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]


async def list_resources_fn() -> List[Resource]:
    """List available prompt resources."""
    return [
        Resource(
            uri=create_uri("prompts://commands"),
            name="Command Prompts",
            description="Command help, menu, and suggestions",
            mimeType="text/markdown",
        )
    ]


async def list_resource_templates_fn() -> List[ResourceTemplate]:
    """List available prompt templates."""
    return [
        ResourceTemplate(
            uriTemplate="prompts://commands/{command}/help",
            name="Command Help",
            description="Get help for a specific command",
            mimeType="text/markdown",
        ),
        ResourceTemplate(
            uriTemplate="prompts://commands/menu",
            name="Command Menu",
            description="Show available commands as a menu",
            mimeType="text/markdown",
        ),
        ResourceTemplate(
            uriTemplate="prompts://commands/{command}/suggest",
            name="Command Suggestions",
            description="Get suggestions for next actions",
            mimeType="text/markdown",
        ),
    ]


async def read_resource_fn(uri: AnyUrl) -> str:
    """Read prompt resource content.

    Args:
        uri: Resource URI to read

    Returns:
        str: Prompt content

    Raises:
        ValueError: If URI is invalid or resource cannot be read
    """
    parts = parse_prompt_uri(str(uri))
    if parts["category"] != "commands":
        msg = f"Invalid prompt category: {parts['category']}"
        raise ValueError(msg)

    if "command" not in parts:
        # Root commands prompt
        content = load_prompt("commands")
        if not content:
            raise ValueError("Failed to load root commands prompt")
        return content

    command = parts["command"]
    if command not in COMMANDS:
        raise ValueError(f"Unknown command: {command}")

    action = parts.get("action")
    if action == "help":
        # Validate input
        CommandHelpInput(command=command)
        # Return help content for specific command
        content = load_prompt("commands")
        if not content:
            raise ValueError("Failed to load help content")
        return content
    elif action == "suggest":
        # Validate input
        CommandSuggestionInput(
            command=command,
            success=True,
            error=None,
        )
        # Return suggestions for next actions
        content = load_prompt("commands")
        if not content:
            raise ValueError("Failed to load suggestions")
        return content

    raise ValueError(f"Invalid prompt action: {action}")
