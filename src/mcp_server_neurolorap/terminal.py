"""Terminal module for developer mode JSON-RPC interface.

This module provides a terminal interface for interacting with the MCP server
using JSON-RPC protocol in developer mode. It allows executing commands and
viewing their output directly in the terminal.
"""

from typing import Any, Dict, List, Optional

from mcp_server_neurolorap.collector import CodeCollector


class JsonRpcTerminal:
    """Terminal interface for JSON-RPC commands."""

    def __init__(self) -> None:
        self.request_id = 0
        self.collector = CodeCollector()
        # Dictionary to store available commands and their handlers
        self.commands: Dict[str, Any] = (
            {  # Any used because of different return types
                "help": self.cmd_help,
                "list_tools": self.cmd_list_tools,
                "collect": self.cmd_collect,
                "exit": self.cmd_exit,
            }
        )

    def parse_request(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a line of input into a JSON-RPC request.

        Args:
            line: The input line to parse

        Returns:
            Optional[Dict[str, Any]]: Parsed JSON-RPC request or None if
            invalid
        """
        try:
            # Simple command parsing for now
            parts = line.strip().split()
            if not parts:
                return None

            command = parts[0]
            params = parts[1:] if len(parts) > 1 else []

            return {
                "jsonrpc": "2.0",
                "method": command,
                "params": params,
                "id": self.request_id,
            }
        except Exception:
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
        response: Dict[str, Any] = {"jsonrpc": "2.0", "id": self.request_id}

        if error:
            response["error"] = error
        else:
            response["result"] = result

        self.request_id += 1
        return response

    async def handle_command(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a JSON-RPC command request.

        Args:
            request: The JSON-RPC request to handle

        Returns:
            Dict[str, Any]: JSON-RPC response
        """
        method = request.get("method")

        if not method or method not in self.commands:
            return self.format_response(
                None,
                {"code": -32601, "message": f"Method '{method}' not found"},
            )

        try:
            handler = self.commands[method]
            params = request.get("params", [])
            if not isinstance(params, list):
                params = []
            result = await handler(params)
            return self.format_response(result)
        except Exception as e:
            return self.format_response(
                None, {"code": -32000, "message": str(e)}
            )

    async def cmd_help(self, params: List[str]) -> str:
        """Show help information about available commands."""
        return """Available commands:
- help: Show this help message
- list_tools: List available MCP tools
- collect <path> [subproject_id]: Collect code from specified path.
  Optional subproject_id for organizing files in subdirectories.
- exit: Exit the terminal"""

    async def cmd_list_tools(self, params: List[str]) -> List[str]:
        """List available MCP tools."""
        return ["code-collector"]  # Static list for now

    async def cmd_collect(self, params: List[str]) -> Dict[str, str]:
        """Execute code collection.

        Args:
            params: List of parameters:
                   - params[0]: Path to collect code from
                   - params[1]: Optional subproject_id
        """
        if not params:
            raise ValueError("Path parameter required")

        # Remove quotes if present
        path = params[0].strip("\"'")

        # Get optional subproject_id
        subproject_id = None
        if len(params) > 1:
            subproject_id = params[1].strip("\"'")

        # Create collector with subproject_id
        collector = CodeCollector(
            project_root=None, subproject_id=subproject_id
        )

        output_file = collector.collect_code(path, "Code Collection")
        if not output_file:
            raise ValueError("Failed to collect code or no files found")

        return {
            "result": (
                f"Code collection complete!\n"
                f"Output file: {output_file}\n"
                f"Prompt file: PROMPT_ANALYZE_Code Collection.md\n"
                f"Subproject ID: {subproject_id or 'None'}"
            )
        }

    async def cmd_exit(self, params: List[str]) -> str:
        """Exit the terminal."""
        return "Goodbye!"
