"""MCP server implementation for code collection.

This module implements a Model Context Protocol (MCP) server that provides
code collection functionality through a standardized interface using FastMCP.
It also includes a developer mode with JSON-RPC terminal interface.
"""

import logging
from typing import Any, Dict, List, Protocol, Union, cast

from mcp.server import Server
from mcp.types import TextContent, Tool

from mcp_server_neurolorap.collector import CodeCollector
from mcp_server_neurolorap.terminal import JsonRpcTerminal
from mcp_server_neurolorap.types import ServerProtocol

__all__ = ["run_dev_mode", "run", "create_initialization_options"]


class Transport(Protocol):
    async def __aenter__(self) -> tuple[Any, Any]: ...
    async def __aexit__(self, *args: Any) -> None: ...


# Get module logger
logger = logging.getLogger(__name__)


# Tool definitions
CODE_COLLECTOR_TOOL: Dict[str, Any] = {
    "name": "code-collector",
    "description": (
        "Collect code from files into a markdown document with syntax "
        "highlighting and table of contents."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "input": {
                "oneOf": [
                    {
                        "type": "string",
                        "description": "Directory or file path to collect",
                    },
                    {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of paths to collect code from",
                    },
                ]
            },
            "title": {
                "type": "string",
                "description": "Title for the collection",
                "default": "Code Collection",
            },
            "subproject_id": {
                "type": "string",
                "description": (
                    "Optional subproject identifier. If provided, files will "
                    "be stored in a subdirectory with this name."
                ),
            },
        },
        "required": ["input"],
    },
}


def create_initialization_options() -> Dict[str, Any]:
    """Create initialization options for the server."""
    return {
        "name": "neurolorap",
        "version": "0.1.0",
        "capabilities": {
            "tools": True,
        },
    }


# Initialize terminal for dev mode
terminal = JsonRpcTerminal()

# Initialize server with type hints
server = cast(ServerProtocol, Server("neurolorap"))


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
        except Exception as e:
            print(f"Error: {str(e)}")

    print("\nExiting developer mode")


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools."""
    logger.info("Listing available tools: code-collector")
    return [
        Tool(
            name=CODE_COLLECTOR_TOOL["name"],
            description=CODE_COLLECTOR_TOOL["description"],
            inputSchema=CODE_COLLECTOR_TOOL["inputSchema"],
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: Union[Dict[str, Any], None]
) -> List[TextContent]:
    """Handle tool execution requests."""
    # Log request details for debugging
    logger.error(f"Tool call: {name}")
    logger.error(f"Arguments: {arguments}")
    if not arguments:
        return [
            TextContent(type="text", text="Error: Missing required arguments")
        ]

    if name != CODE_COLLECTOR_TOOL["name"]:
        return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]

    try:
        raw_input = arguments.get("input")
        if isinstance(raw_input, str):
            input_path: Union[str, List[str]] = raw_input
        elif isinstance(raw_input, list):
            raw_list: List[Any] = raw_input
            if not all(isinstance(item, str) for item in raw_list):
                return [
                    TextContent(
                        type="text",
                        text=(
                            "Error: All items in 'input' list must be strings"
                        ),
                    )
                ]
            input_path = raw_input
        else:
            return [
                TextContent(
                    type="text",
                    text="Error: 'input' must be a string or list of strings",
                )
            ]
        title = str(arguments.get("title", "Code Collection"))

        if not input_path:
            return [
                TextContent(
                    type="text",
                    text="Error: Missing required 'input' argument",
                )
            ]

        # Get subproject_id if provided
        subproject_id = arguments.get("subproject_id")

        # Create collector with subproject_id
        collector = CodeCollector(
            project_root=None, subproject_id=subproject_id
        )

        logger.info("Starting code collection")
        logger.info("Input: %s", input_path)
        logger.info("Title: %s", title)
        logger.info("Subproject ID: %s", subproject_id)

        output_file = collector.collect_code(input_path, title)

        if not output_file:
            return [
                TextContent(
                    type="text",
                    text="No files found to process or error occurred "
                    "during collection",
                )
            ]

        return [
            TextContent(
                type="text",
                text=f"Code collection complete!\nOutput file: {output_file}",
            )
        ]

    except Exception:
        logger.exception("Error collecting code")
        return [
            TextContent(
                type="text",
                text="Failed to collect code. Check server logs for details.",
            )
        ]


async def run(reader: Any, writer: Any, options: Any) -> None:
    """Run the server with stdio transport.

    Args:
        reader: Stream reader
        writer: Stream writer
        options: Server initialization options
    """
    try:
        # Start server
        await server.run(reader, writer, options)
    except Exception as e:
        logger.exception("Server error: %s", str(e))
        raise RuntimeError(f"Server error: {str(e)}")
