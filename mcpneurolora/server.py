"""NeuroLoRA MCP server implementation."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Sequence
from urllib.parse import urlparse

from mcp.server import Server
from mcp.server.fastmcp import Context
from mcp.server.stdio import stdio_server
from mcp.types import (
    EmbeddedResource,
    ImageContent,
    Resource,
    ResourceTemplate,
    TextContent,
    Tool,
)
from pydantic import AnyUrl, TypeAdapter

from .log_utils import LogCategory, get_logger
from .prompts import CommandHelpInput, CommandSuggestionInput, route_command
from .terminal import JsonRpcTerminal
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

__all__ = ["run_terminal_server", "run_mcp_server"]

# Create TypeAdapter for AnyUrl validation
url_adapter = TypeAdapter(AnyUrl)


def create_uri(uri_str: str) -> AnyUrl:
    """Create AnyUrl from string.

    Args:
        uri_str: URI string

    Returns:
        AnyUrl instance
    """
    return url_adapter.validate_python(uri_str)


def get_project_root() -> Path:
    """Get project root directory from environment or current directory.

    Returns:
        Path: Project root directory path
    """
    project_root_str: Optional[str] = os.environ.get("MCP_PROJECT_ROOT")
    if project_root_str:
        return Path(project_root_str)
    return Path.cwd()


def ensure_project_root_env() -> None:
    """Ensure MCP_PROJECT_ROOT environment variable is set.
    Sets it to current directory if not already set."""
    if not os.environ.get("MCP_PROJECT_ROOT"):
        current_dir: Path = Path.cwd()
        os.environ["MCP_PROJECT_ROOT"] = str(current_dir)
        logger.info("Set MCP_PROJECT_ROOT to: %s", current_dir)


def load_prompt(name: str) -> str:
    """Load prompt content from file.

    Args:
        name: Name of the prompt file without extension

    Returns:
        Prompt content as string
    """
    prompt_path = Path(__file__).parent / "prompts" / f"{name}.prompt.md"
    return prompt_path.read_text()


def parse_prompt_uri(uri: str) -> Dict[str, str]:
    """Parse prompt URI into components.

    Args:
        uri: Prompt URI (e.g. prompts://commands/improve/help)

    Returns:
        Dictionary with URI components
    """
    parsed = urlparse(uri)
    if parsed.scheme != "prompts":
        raise ValueError(f"Invalid URI scheme: {parsed.scheme}")

    parts = parsed.path.strip("/").split("/")
    if not parts:
        raise ValueError("Empty URI path")

    result = {"category": parts[0]}
    if len(parts) > 1:
        result["command"] = parts[1]
    if len(parts) > 2:
        result["action"] = parts[2]
    return result


async def run_mcp_server() -> None:
    """Initialize and run the main MCP server.

    Creates and configures the main MCP server instance for handling
    production requests. Registers and prepares all available tools.
    """
    ensure_project_root_env()

    # Initialize server and register FastMCP handlers
    from .prompts import mcp

    server = Server("neurolora")

    async def _try_route_command(name: str) -> str:
        """Try to route command if it's not internal.

        Args:
            name: Command name to route

        Returns:
            str: Routed command name or original name
        """
        if not name.startswith("_"):
            try:
                response: RouterResponse = await route_command(name)
                if response.confidence >= 0.7:
                    logger.info(
                        "Routed '%s' to '%s' (conf: %.2f)",
                        name,
                        response.command,
                        response.confidence,
                    )
                    return response.command
            except Exception as e:
                logger.debug("Command routing failed: %s", str(e))
        return name

    async def _execute_command(
        name: str, validated: Any, executor: ToolExecutor
    ) -> str:
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

    # Register FastMCP handlers with proper types
    async def list_tools_wrapper() -> list[Tool]:
        return await mcp.list_tools()

    async def call_tool_wrapper(
        name: str,
        arguments: Dict[str, str | int | float | bool | None],
        context: Optional[Context] = None,
        **kwargs: Any,
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        # Try to route command if it's not an internal command
        routed_name: str = await _try_route_command(name)

        # Call tool with explicit typing for arguments and result
        tool_result = await mcp.call_tool(
            name=routed_name, arguments=arguments
        )

        # Ensure correct return type
        result: Sequence[TextContent | ImageContent | EmbeddedResource] = (
            tool_result
        )
        return result

    # Register handlers
    server.list_tools()(list_tools_wrapper)  # type: ignore[no-untyped-call]
    server.call_tool()(call_tool_wrapper)  # type: ignore[no-untyped-call]

    # Define prompt resources
    async def list_resources_fn() -> list[Resource]:
        """List available prompt resources."""
        return [
            Resource(
                uri=create_uri("prompts://commands"),
                name="Command Prompts",
                description="Prompts for command help, menu and suggestions",
                mimeType="text/markdown",
            )
        ]

    async def list_resource_templates_fn() -> list[ResourceTemplate]:
        """List available prompt templates."""
        templates = [
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
        return templates

    async def read_resource_fn(uri: AnyUrl) -> str:
        """Read prompt resource content."""
        try:
            parts = parse_prompt_uri(str(uri))
            if parts["category"] != "commands":
                msg = f"Invalid prompt category: {parts['category']}"
                raise ValueError(msg)

            if "command" not in parts:
                # Root commands prompt
                return load_prompt("commands")

            command = parts["command"]
            if command not in COMMANDS:
                raise ValueError(f"Unknown command: {command}")

            action = parts.get("action")
            if action == "help":
                # Validate input
                CommandHelpInput(command=command)
                # Return help content for specific command
                return load_prompt("commands")
            elif action == "suggest":
                # Validate input
                CommandSuggestionInput(
                    command=command,
                    success=True,
                    error=None,
                )
                # Return suggestions for next actions
                return load_prompt("commands")

            raise ValueError(f"Invalid prompt action: {action}")

        except Exception as e:
            logger.error("Error reading prompt resource: %s", str(e))
            raise ValueError(f"Invalid resource URI: {uri}")

    # Register resource handlers
    server.list_resources()(list_resources_fn)  # type: ignore[no-untyped-call]
    server.list_resource_templates()(list_resource_templates_fn)  # type: ignore[no-untyped-call]
    server.read_resource()(read_resource_fn)  # type: ignore[no-untyped-call]

    # Define tool functions
    async def list_tools_fn() -> list[Tool]:
        # Get only MCP tools
        mcp_tools = get_mcp_tools()
        return [
            Tool(
                name=cmd_def["name"],
                description=cmd_def["description"],
                inputSchema=(
                    cmd_def["model"].model_json_schema()
                    if cmd_def["model"]
                    else {}
                ),
            )
            for cmd_def in mcp_tools.values()
        ]

    async def call_tool_fn(
        name: str,
        arguments: Dict[str, Any],
        context: Optional["Context"] = None,
        **kwargs: Any,
    ) -> list[TextContent]:
        try:
            # Validate command and setup
            validate_command(name)
            if COMMANDS[name]["requires_project_root"]:
                ensure_project_root_env()

            # Create executor
            executor = ToolExecutor(
                project_root=get_project_root(),
                context=context,
            )

            # Get and validate model
            model_cls = validate_command_model(name)
            validated = validate_arguments(model_cls, arguments)

            # Execute appropriate command
            result = await _execute_command(name, validated, executor)
            return [TextContent(type="text", text=result)]

        except ValueError as e:
            error_msg = f"Error executing tool: {str(e)}"
            logger.error(error_msg)
            return [TextContent(type="text", text=error_msg)]

    # Register tool functions
    server.list_tools()(list_tools_fn)  # type: ignore[no-untyped-call]
    server.call_tool()(call_tool_fn)  # type: ignore[no-untyped-call]

    # Get timeout from environment or use default (5 minutes)
    timeout_ms = int(os.environ.get("AI_TIMEOUT_MS", "300000"))

    # Set timeout in environment for stdio server
    os.environ["JSONRPC_TIMEOUT_MS"] = str(timeout_ms)

    # Create initialization options
    options = server.create_initialization_options()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)


async def run_terminal_server() -> None:
    """Run the interactive JSON-RPC terminal server.

    This function starts a terminal server that accepts JSON-RPC commands
    for testing and development. It provides an interactive interface
    to execute and test the MCP server's tools and functionality.

    The terminal supports basic commands like:
    - help: Show available commands
    - list_tools: List registered tools
    - collect: Generate code documentation
    - showtree: Generate project files tree
    - improve: Analyze and suggest improvements
    - exit: Exit the terminal

    Raises:
        ValueError: If command input is malformed
        TypeError: If command arguments have invalid types
        KeyboardInterrupt: If Ctrl+C is pressed
        EOFError: If EOF is encountered (Ctrl+D)
        OSError: If system-level errors occur
        json.JSONDecodeError: If JSON parsing fails
    """
    ensure_project_root_env()
    logger.info("Starting terminal server...")
    logger.info("Type 'help' for available commands")
    logger.info("Type 'exit' to quit")

    # Initialize terminal server
    terminal: JsonRpcTerminal = JsonRpcTerminal(
        project_root=str(get_project_root())
    )

    while True:
        try:
            line: str = input("> ")
            if not line:
                continue

            request: Optional[Dict[str, Any]] = terminal.parse_request(line)
            if not request:
                logger.warning("Invalid command format")
                continue

            response: Dict[str, Any] = await terminal.handle_command(request)

            if "error" in response and response["error"] is not None:
                error: Any = response["error"]
                if (
                    isinstance(error, dict)
                    and "message" in error
                    and error["message"] is not None
                    and isinstance(error["message"], str)
                    and error["message"].strip()
                ):
                    msg: str = str(error["message"])
                    logger.error(msg)
            elif "result" in response:
                result: Any = response["result"]
                logger.info(result)

            if request.get("method") == "exit":
                break

        except (KeyboardInterrupt, EOFError):
            break
        except json.JSONDecodeError as e:
            json_error: str = f"Invalid JSON format: {str(e)}"
            logger.error(json_error)
            logger.error(
                "JSON parsing error in terminal server: %s",
                json_error,
                exc_info=True,
            )
        except ValueError as e:
            value_error: str = f"Value error: {str(e)}"
            logger.error(value_error)
            logger.error(
                "Value error in terminal server: %s",
                value_error,
                exc_info=True,
            )
        except TypeError as e:
            type_error: str = f"Type error: {str(e)}"
            logger.error(type_error)
            logger.error(
                "Type error in terminal server: %s",
                type_error,
                exc_info=True,
            )
        except OSError as e:
            os_error: str = f"System error: {str(e)}"
            logger.error(os_error)
            logger.error(
                "OS error in terminal server: %s",
                os_error,
                exc_info=True,
            )
        except RuntimeError as e:
            critical_error: str = f"Critical error: {str(e)}"
            logger.critical(critical_error)
            logger.critical(
                "Unexpected critical error in terminal server: %s",
                critical_error,
                exc_info=True,
            )
            raise  # Re-raise unexpected exceptions for proper handling

    logger.info("Exiting terminal server")
    logger.info("Terminal server stopped")
