"""Terminal server implementation for NeuroLoRA."""

import json
from typing import Any, Dict, Optional

from .log_utils import LogCategory, get_logger
from .server_utils import get_project_root
from .terminal import JsonRpcTerminal

# Get module logger
logger = get_logger(__name__, LogCategory.SERVER)


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
    from .server_utils import ensure_project_root_env

    try:
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
                    logger.info("Empty input received")
                    logger.warning("Empty input")
                    continue

                request: Optional[Dict[str, Any]] = terminal.parse_request(line)
                if not request:
                    logger.error("Invalid command format")
                    break

                if request.get("method") == "help":
                    logger.info("Help message")
                    response: Dict[str, Any] = await terminal.handle_command(request)
                    if "result" in response:
                        logger.info("Available Commands:")
                        logger.info(response["result"])
                else:
                    response = await terminal.handle_command(request)
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
                    logger.info("Exiting terminal server")
                    break

            except (KeyboardInterrupt, EOFError):
                logger.info("Keyboard interrupt received")
                logger.info("Exiting terminal server")
                break
            except ValueError as e:
                error_msg = f"Value error: {str(e)}"
                logger.error(error_msg)
                logger.error(f"Value error in terminal server: {str(e)}", exc_info=True)
                break
            except TypeError as e:
                error_msg = f"Type error: {str(e)}"
                logger.error(error_msg)
                logger.error(f"Type error in terminal server: {str(e)}", exc_info=True)
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

    logger.info("Terminal server stopped")
