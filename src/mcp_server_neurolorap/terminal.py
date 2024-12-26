"""Terminal module for developer mode JSON-RPC interface.

This module provides a terminal interface for interacting with the MCP server
using JSON-RPC protocol in developer mode. It allows executing commands and
viewing their output directly in the terminal.
"""

from itertools import count
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, cast

from mcp_server_neurolorap.collector import CodeCollector


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

    collector: CodeCollector | None
    project_root: Path | None
    commands: Dict[str, Any]
    _counter: Iterator[int]

    def __init__(self, project_root: str | None = None) -> None:
        """Initialize the terminal interface.

        Args:
            project_root: Optional root directory for code collection
        """
        self._counter = cast(Iterator[int], count())
        self.project_root = Path(project_root) if project_root else None
        try:
            self.collector = CodeCollector(project_root=self.project_root)
        except Exception:
            # Log error but don't fail initialization
            # Commands that need collector will fail when called
            self.collector = None
            self.project_root = None

        # Dictionary to store available commands and their handlers
        self.commands: Dict[str, Any] = {
            "help": self.cmd_help,
            "list_tools": self.cmd_list_tools,
            "collect": self.cmd_collect,
            "report": self.cmd_project_structure_reporter,
            "exit": self.cmd_exit,
        }

    def parse_request(self, line: str | None) -> Optional[Dict[str, Any]]:
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
                return None

            # Check for multiple spaces
            if "  " in line:
                return None

            # Split into parts and filter out empty/whitespace
            parts = [p for p in line.split() if p.strip()]
            if not parts:
                return None

            # Validate command (first part)
            command = parts[0]
            # Allow commands with hyphens
            if not command.replace("-", "").replace("_", "").isalnum():
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
                return self.format_response(
                    None,
                    {
                        "code": -32602,
                        "message": "Invalid params: must be a list",
                    },
                )
            result = await handler(params)
            return self.format_response(result)
        except ValueError as e:
            return self.format_response(
                None,
                {"code": -32602, "message": str(e)},
            )
        except Exception as e:
            return self.format_response(
                None,
                {"code": -32000, "message": str(e)},
            )

    async def cmd_help(self, params: List[str]) -> str:
        """Show help information about available commands."""
        return """Available commands:
- help: Show this help message
- list_tools: List available MCP tools
- collect [path] [subproject_id]: Collect code from specified path.
  Path and subproject_id are optional (defaults to entire project).
- report [path]: Generate project structure report.
  Optional path to analyze (defaults to entire project).
- exit: Exit the terminal"""

    async def cmd_list_tools(self, params: List[str]) -> List[str]:
        """List available MCP tools."""
        return ["code_collector", "report"]

    async def cmd_collect(self, params: List[str]) -> Dict[str, str]:
        """Execute code collection.

        Args:
            params: List of parameters:
                   - params[0]: Path to collect code from
                   - params[1]: Optional subproject_id
        """
        if not self.collector:
            raise ValueError("Code collector not initialized")

        if not params:
            raise ValueError("Path parameter required")

        path = params[0].strip("\"'")
        subproject_id = params[1].strip("\"'") if len(params) > 1 else None

        # Use existing collector for collecting code
        output_file = self.collector.collect_code(path, "Code Collection")
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

    async def cmd_project_structure_reporter(
        self, params: List[str]
    ) -> Dict[str, str]:
        """Execute project structure report generation.

        Args:
            params: List of parameters:
                   - params[0]: Optional path to analyze
        """
        if not self.project_root:
            raise ValueError("Project root not initialized")

        if not self.collector:
            raise ValueError("Code collector not initialized")

        # Get optional path parameter and set output filename
        analyze_path = self.project_root
        output_filename = "PROJECT_STRUCTURE_REPORT.md"
        if params:
            path = params[0].strip("\"'")
            analyze_path = self.project_root / path
            path_slug = path.replace("/", "_").replace("\\", "_")
            output_filename = f"PROJECT_STRUCTURE_REPORT_{path_slug}.md"

        # Initialize storage
        from .collector import CodeCollector
        from .storage import StorageManager

        storage = StorageManager(self.project_root)
        storage.setup()  # Create .neuroloraignore if needed

        # Create temporary collector to load ignore patterns
        temp_collector = CodeCollector(project_root=self.project_root)
        ignore_patterns = temp_collector.load_ignore_patterns()

        # Create reporter with ignore patterns
        from mcp_server_neurolorap.project_structure_reporter import (
            ProjectStructureReporter,
        )

        reporter = ProjectStructureReporter(
            root_dir=analyze_path,
            ignore_patterns=ignore_patterns,
        )

        # Generate report
        report_data = reporter.analyze_project_structure()

        output_path = self.project_root / ".neurolora" / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        reporter.generate_markdown_report(report_data, output_path)

        return {"result": f"Project structure report generated: {output_path}"}

    async def cmd_exit(self, params: List[str]) -> str:
        """Exit the terminal."""
        return "Goodbye!"
