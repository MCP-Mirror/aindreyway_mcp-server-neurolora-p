"""Terminal module for developer mode JSON-RPC interface.

This module provides a terminal interface for interacting with the MCP server
using JSON-RPC protocol in developer mode. It allows executing commands and
viewing their output directly in the terminal.
"""

import json
from itertools import count
from pathlib import Path
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    TypedDict,
    cast,
)

from colorama import Style, init

from .log_utils import LogCategory, get_logger
from .providers import is_ai_configured
from .tools.definitions import COMMANDS
from .tools.executor import ToolExecutor

# Initialize colorama
init()

# Get module logger
logger = get_logger(__name__, LogCategory.TERMINAL)

# Colorama formatting
COLORS = {
    "BOLD": Style.BRIGHT,  # Bold text
    "RESET": Style.RESET_ALL,  # Reset formatting
}


class SchemaProperty(TypedDict):
    """Type definition for JSON schema property."""

    description: str
    default: Optional[Any]


class JsonSchema(TypedDict, total=False):
    """Type definition for JSON schema."""

    properties: Dict[str, SchemaProperty]
    required: List[str]


CommandHandler = Callable[[List[str]], Awaitable[Any]]


class JsonRpcTerminal:
    """Terminal interface for JSON-RPC commands.

    This class provides a thread-safe implementation of JSON-RPC request
    handling for the developer mode terminal interface.

    Thread Safety:
        - Uses itertools.count() for atomic request ID generation
        - Safe for concurrent command execution
        - Note: Command handlers themselves may not be thread-safe

    Concurrency Limitations:
        - Command execution is not parallelized
        - File operations in commands may block
        - Future versions may add async command execution
    """

    executor: ToolExecutor
    project_root: Optional[Path]
    commands: Dict[str, CommandHandler]
    _counter: Iterator[int]

    def __init__(self, project_root: Optional[str] = None) -> None:
        """Initialize the terminal interface.

        Args:
            project_root: Optional root directory for code collection
        """
        logger.info("Initializing terminal with project_root=%s", project_root)

        self._counter = cast(Iterator[int], count())
        self.project_root = Path(project_root) if project_root else None
        self.executor = ToolExecutor(project_root=self.project_root)
        logger.info(
            "Created ToolExecutor with project_root=%s", self.project_root
        )

        # Initialize commands directly from COMMANDS
        self.commands = {
            name: cast(CommandHandler, getattr(self, cmd_def["handler_name"]))
            for name, cmd_def in COMMANDS.items()
            if not cmd_def["requires_ai"] or is_ai_configured()
        }

    def parse_request(self, line: Optional[str]) -> Optional[Dict[str, Any]]:
        """Parse a line of input into a JSON-RPC request.

        Args:
            line: The input line to parse

        Returns:
            Optional[Dict[str, Any]]: Parsed JSON-RPC request or None if
            invalid

        Validation rules:
            - Line must not be None or empty
            - Line must not contain null bytes or control characters
            - Command must be a single word
            - Parameters are space-separated
        """
        if not line:
            return None

        try:
            # Check for invalid characters
            if "\0" in line or "\n" in line or "\r" in line:
                logger.warning("Invalid characters in input")
                return None

            # Check for multiple spaces
            if "  " in line:
                logger.warning("Multiple consecutive spaces in input")
                return None

            # Split into parts and filter out empty/whitespace
            parts = [p for p in line.split() if p.strip()]
            if not parts:
                logger.warning("No command found in input")
                return None

            # Validate command (first part)
            command = parts[0]
            # Allow commands with hyphens
            if not command.replace("-", "").replace("_", "").isalnum():
                logger.warning("Invalid command format")
                return None

            # Get params (remaining parts)
            params = parts[1:] if len(parts) > 1 else []

            request_id = next(self._counter)
            return {
                "jsonrpc": "2.0",
                "method": command,
                "params": params,
                "id": request_id,
            }
        except ValueError as e:
            logger.error("Value error parsing request: %s", str(e))
            return None
        except TypeError as e:
            logger.error("Type error parsing request: %s", str(e))
            return None

    def format_response(
        self, result: Any, error: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format a JSON-RPC response.

        Args:
            result: The result of the command execution
            error: Optional error information

        Returns:
            Dict[str, Any]: Formatted JSON-RPC response
        """
        request_id = next(self._counter)
        response: Dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}

        if error:
            response["error"] = error
        else:
            response["result"] = result
        return response

    async def handle_command(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a JSON-RPC command request.

        Args:
            request: The JSON-RPC request to handle

        Returns:
            Dict[str, Any]: JSON-RPC response
        """
        # Reload environment configuration before each command
        from .config import setup_environment

        setup_environment()

        method = request.get("method")

        if not method or method not in self.commands:
            return self.format_response(
                None,
                {"code": -32601, "message": f"Method '{method}' not found"},
            )

        try:
            # Get command definition
            cmd_def = COMMANDS[method]

            # Check if command requires project root
            if cmd_def["requires_project_root"] and not self.project_root:
                raise ValueError("Project root not initialized")

            # Get handler and params
            handler = self.commands[method]
            params: List[str] = request.get("params", [])

            result = await handler(params)
            return self.format_response(result)
        except ValueError as e:
            logger.error("Invalid parameter value: %s", str(e))
            return self.format_response(
                None,
                {"code": -32602, "message": f"Invalid parameter: {str(e)}"},
            )
        except FileNotFoundError as e:
            logger.error("File not found: %s", str(e))
            return self.format_response(
                None,
                {"code": -32603, "message": f"File not found: {str(e)}"},
            )
        except PermissionError as e:
            logger.error("Permission denied: %s", str(e))
            return self.format_response(
                None,
                {"code": -32603, "message": f"Permission denied: {str(e)}"},
            )
        except OSError as e:
            logger.error("System error: %s", str(e))
            return self.format_response(
                None,
                {"code": -32603, "message": f"System error: {str(e)}"},
            )
        except (TypeError, json.JSONDecodeError) as e:
            logger.error("Invalid request format: %s", str(e))
            return self.format_response(
                None,
                {"code": -32600, "message": f"Invalid request: {str(e)}"},
            )
        except RuntimeError as e:
            logger.error("Runtime error: %s", str(e))
            return self.format_response(
                None,
                {"code": -32603, "message": f"Runtime error: {str(e)}"},
            )

    def _parse_command_desc(self, desc: str) -> Tuple[str, str]:
        """Parse command description into name and description parts.

        Args:
            desc: Command description string

        Returns:
            Tuple[str, str]: Command name and description
        """
        parts = desc.split(":", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return desc, ""

    async def cmd_help(self, params: List[str]) -> str:
        """Show help information about available commands."""
        help_text = "Available Commands:\n\n"

        # Add command descriptions and parameters
        for cmd_def in COMMANDS.values():
            if cmd_def["requires_ai"] and not is_ai_configured():
                continue
            # Extract command name from description
            cmd_name, cmd_desc = self._parse_command_desc(
                cmd_def["description"]
            )
            # Make command name bold
            help_text += (
                f"{COLORS['BOLD']}{cmd_name}{COLORS['RESET']}: "
                f"{cmd_desc}\n"
            )

            # Add parameter descriptions for MCP tools
            if cmd_def["is_mcp_tool"] and cmd_def["model"]:
                model_cls = cmd_def["model"]
                if model_cls:
                    schema = model_cls.model_json_schema()
                    if "properties" in schema and schema["properties"]:
                        help_text += "   Parameters:\n"
                        required = schema.get("required", [])
                        for param_name, param_info in schema[
                            "properties"
                        ].items():
                            desc = param_info.get(
                                "description", "No description"
                            )
                            is_required = param_name in required
                            param_type = (
                                "[REQUIRED]" if is_required else "[OPTIONAL]"
                            )
                            help_text += (
                                f"   {COLORS['BOLD']}{param_name}"
                                f"{COLORS['RESET']} {param_type}: {desc}\n"
                            )
            help_text += "\n"

        return help_text.rstrip()

    async def cmd_list_tools(self, params: List[str]) -> List[str]:
        """List available MCP tools."""
        # Return MCP tool names directly from COMMANDS
        return [
            name
            for name, cmd_def in COMMANDS.items()
            if cmd_def["is_mcp_tool"]
            and (not cmd_def["requires_ai"] or is_ai_configured())
        ]

    async def cmd_improve(self, params: List[str]) -> Dict[str, Any]:
        """Execute improve tool.

        Args:
            params: List of parameters:
                   - params[0]: Optional path to analyze
        """
        path = params[0].strip("\"'") if params else "."
        result = await self.executor.execute_improve(path)
        return self.executor.format_result(result)

    async def cmd_request(self, params: List[str]) -> Dict[str, Any]:
        """Execute request tool.

        Args:
            params: List of parameters:
                   - params[0]: Optional path to analyze
                   - params[1]: Request text
        """
        if len(params) < 2:
            raise ValueError("Request text is required")

        path = params[0].strip("\"'") if params else "."
        request_text = params[1].strip("\"'")
        result = await self.executor.execute_request(path, request_text)
        return self.executor.format_result(result)

    async def cmd_collect(self, params: List[str]) -> Dict[str, Any]:
        """Execute code collection.

        Args:
            params: List of parameters:
                   - params[0]: Path to collect code from
        """
        path = params[0].strip("\"'") if params else "."
        result = await self.executor.execute_code_collector(path)
        return self.executor.format_result(result)

    async def cmd_project_structure_reporter(
        self, params: List[str]
    ) -> Dict[str, Any]:
        """Execute project structure report generation.

        This command generates a project files tree structure in
        FULL_TREE_PROJECT_FILES.md.

        Args:
            params: List of parameters (ignored as this command has no
                   parameters)
        """
        result = await self.executor.execute_project_structure_reporter(
            "FULL_TREE_PROJECT_FILES.md"
        )
        return self.executor.format_result(result)

    async def cmd_reload(self, params: List[str]) -> str:
        """Reload the server to apply code changes."""
        import os
        import sys

        logger.info("Reloading server...")

        # Clear AI-related environment variables
        ai_vars: List[str] = [
            "AI_MODEL",
            "OPENAI_API_KEY",
            "GEMINI_API_KEY",
            "ANTHROPIC_API_KEY",
        ]
        for var in ai_vars:
            if var in os.environ:
                del os.environ[var]

        python = sys.executable
        # execl replaces current process, no code after this will execute
        os.execl(
            python, python, "-m", "aindreyway-mcp-server-neurolora", "--dev"
        )

    async def cmd_exit(self, params: List[str]) -> str:
        """Exit the terminal."""
        logger.info("Exiting terminal")
        return "Goodbye!"
