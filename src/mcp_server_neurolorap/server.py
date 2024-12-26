"""MCP server implementation for code collection."""

import logging
import os
from pathlib import Path
from typing import Any, cast

from mcp.server.fastmcp import FastMCP

from mcp_server_neurolorap.collector import CodeCollector
from mcp_server_neurolorap.project_structure_reporter import (
    ProjectStructureReporter,
)
from mcp_server_neurolorap.terminal import JsonRpcTerminal
from mcp_server_neurolorap.types import FastMCPType

# Get module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

__all__ = ["run_dev_mode", "create_server"]


def get_project_root() -> Path:
    """Get project root directory from environment or current directory."""
    current_dir = Path.cwd()
    project_root_str = os.environ.get("MCP_PROJECT_ROOT")
    if not project_root_str:
        os.environ["MCP_PROJECT_ROOT"] = str(current_dir)
        logger.info("Set MCP_PROJECT_ROOT to: %s", current_dir)
        return current_dir
    return Path(project_root_str)


def create_server() -> FastMCPType:
    """Create and configure a new server instance."""
    mcp = FastMCP("neurolorap")

    # Project structure reporter tool
    async def project_structure_reporter(
        output_filename: str = "PROJECT_STRUCTURE_REPORT.md",
        ignore_patterns: list[str] | None = None,
    ) -> str:
        """Generate a report of project structure metrics."""
        logger.debug("Tool call: project_structure_reporter")
        logger.debug(
            "Arguments: output_filename=%s, ignore_patterns=%s",
            output_filename,
            ignore_patterns,
        )

        try:
            root_path = get_project_root()
            reporter = ProjectStructureReporter(
                root_dir=root_path,
                ignore_patterns=ignore_patterns,
            )

            logger.info("Starting project structure analysis")
            report_data = reporter.analyze_project_structure()

            output_path = root_path / ".neurolora" / output_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)

            reporter.generate_markdown_report(report_data, output_path)

            return f"Project structure report generated: {output_path}"

        except Exception as e:
            error_msg = f"Unexpected error generating report: {e}"
            logger.error(error_msg, exc_info=True)
            return f"Error generating report: {str(e)}"

    # Code collector tool
    async def code_collector(
        input_path: str | list[str] = ".",
        title: str = "Code Collection",
        subproject_id: str | None = None,
    ) -> str:
        """Collect code from files into a markdown document."""
        logger.debug("Tool call: code_collector")
        logger.debug(
            "Arguments: input=%s, title=%s, subproject_id=%s",
            input_path,
            title,
            subproject_id,
        )

        try:
            root_path = get_project_root()
            collector = CodeCollector(
                project_root=root_path, subproject_id=subproject_id
            )

            logger.info("Starting code collection")
            logger.debug("Input: %s", input_path)
            logger.debug("Title: %s", title)
            logger.debug("Subproject ID: %s", subproject_id)

            output_file = collector.collect_code(input_path, title)
            if not output_file:
                msg = "No files found to process or error occurred"
                return msg

            return f"Code collection complete!\nOutput file: {output_file}"

        except Exception as e:
            error_msg = f"Unexpected error collecting code: {e}"
            logger.error(error_msg, exc_info=True)
            return "No files found to process or error occurred"

    # Register tools with MCP
    mcp.tool(
        name="code_collector",
        description="Collect code from files into a markdown document",
    )(code_collector)

    mcp.tool(
        name="project_structure_reporter",
        description="Generate a report of project structure metrics",
    )(project_structure_reporter)

    return cast(FastMCPType, mcp)


async def run_dev_mode() -> None:
    """Run the server in developer mode with JSON-RPC terminal."""
    print("Starting developer mode terminal...")
    print("Type 'help' for available commands")
    print("Type 'exit' to quit")

    # Initialize terminal for dev mode
    terminal = JsonRpcTerminal(project_root=str(get_project_root()))

    while True:
        try:
            line = input("> ")
            if not line:
                continue

            request: dict[str, Any] | None = terminal.parse_request(line)
            if not request:
                print("Invalid command format")
                continue

            response: dict[str, Any] = await terminal.handle_command(request)

            if "error" in response and response["error"] is not None:
                error = response["error"]
                if (
                    isinstance(error, dict)
                    and "message" in error
                    and error["message"] is not None
                    and isinstance(error["message"], str)
                    and error["message"].strip()
                ):
                    print(f"Error: {error['message']}")
            elif "result" in response:
                print(response["result"])

            if request.get("method") == "exit":
                break

        except (KeyboardInterrupt, EOFError):
            break
        except ValueError as e:
            print(f"Value error: {str(e)}")
        except TypeError as e:
            print(f"Type error: {str(e)}")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            logger.error("Unexpected error in developer mode", exc_info=True)

    print("\nExiting developer mode")
