"""MCP server implementation for code collection."""

import logging
import os
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from mcp_server_neurolorap.collector import CodeCollector
from mcp_server_neurolorap.terminal import JsonRpcTerminal

# Get module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Set project root if not set
current_dir = Path.cwd()
if not os.environ.get("MCP_PROJECT_ROOT"):
    os.environ["MCP_PROJECT_ROOT"] = str(current_dir)
    logger.info("Set MCP_PROJECT_ROOT to: %s", os.environ["MCP_PROJECT_ROOT"])

# Get project root from environment variable
project_root_str: Optional[str] = os.environ.get("MCP_PROJECT_ROOT")
if not project_root_str:
    raise RuntimeError("MCP_PROJECT_ROOT not set")

project_root: Path = Path(project_root_str)

__all__ = ["run_dev_mode", "create_server"]


def create_server() -> FastMCP:
    """Create and configure a new server instance."""
    mcp = FastMCP("neurolorap", tools=True)

    @mcp.tool()
    async def code_collector(
        input: str | list[str],
        title: str = "Code Collection",
        subproject_id: str | None = None,
    ) -> str:
        """Collect code from files into a markdown document."""
        logger.debug("Tool call: code-collector")
        logger.debug(
            "Arguments: input=%s, title=%s, subproject_id=%s",
            input,
            title,
            subproject_id,
        )

        try:
            collector = CodeCollector(
                project_root=project_root, subproject_id=subproject_id
            )

            logger.info("Starting code collection")
            logger.debug("Input: %s", input)
            logger.debug("Title: %s", title)
            logger.debug("Subproject ID: %s", subproject_id)

            output_file = collector.collect_code(input, title)
            if not output_file:
                msg = "No files found to process or error occurred"
                return msg

            return f"Code collection complete!\nOutput file: {output_file}"

        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.warning(f"File system error collecting code: {str(e)}")
            return f"File system error: {str(e)}"
        except ValueError as e:
            logger.warning(f"Value error collecting code: {str(e)}")
            return f"Invalid input: {str(e)}"
        except TypeError as e:
            logger.warning(f"Type error collecting code: {str(e)}")
            return f"Type error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error collecting code: {str(e)}")
            logger.debug("Stack trace:", exc_info=True)
            return "An unexpected error occurred. Check server logs."

    return mcp


# Initialize terminal for dev mode with project root
terminal = JsonRpcTerminal(
    project_root=str(project_root) if project_root else None
)


async def run_dev_mode() -> None:
    """Run the server in developer mode with JSON-RPC terminal."""
    print("Starting developer mode terminal...")
    print("Type 'help' for available commands")
    print("Type 'exit' to quit")

    while True:
        try:
            line = input("> ")
            if not line:
                continue

            request = terminal.parse_request(line)
            if not request:
                print("Invalid command format")
                continue

            response = await terminal.handle_command(request)

            if "error" in response:
                print(f"Error: {response['error']['message']}")
            else:
                print(response["result"])

            if request["method"] == "exit":
                break

        except (KeyboardInterrupt, EOFError):
            break
        except ValueError as e:
            print(f"Value error: {str(e)}")
        except TypeError as e:
            print(f"Type error: {str(e)}")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            logger.debug("Stack trace:", exc_info=True)

    print("\nExiting developer mode")
