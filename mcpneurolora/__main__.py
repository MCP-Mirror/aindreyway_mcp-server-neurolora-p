"""Entry point for the MCP server.

This module provides the main entry point for running the server
and handles configuration setup.
"""

__all__ = [
    "ClinesConfig",
    "configure_cline",
    "handle_shutdown",
    "main",
    "main_entry",
]

import asyncio
import json
import signal
import sys
from pathlib import Path
from types import FrameType
from typing import List, cast

from .config import setup_environment
from .log_utils import LogCategory, configure_mcp_logging, get_logger
from .server import run_mcp_server, run_terminal_server
from .types import ClinesConfig, ServerConfig

# Global flag for graceful shutdown
shutdown_requested = False

# Get module logger with category
logger = get_logger(__name__, LogCategory.CONFIG)


def handle_shutdown(signum: int, frame: FrameType | None) -> None:
    """Handle shutdown signals.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    global shutdown_requested
    logger.info("Shutdown requested, cleaning up...")
    shutdown_requested = True


def get_config_paths() -> List[Path]:
    """Get the paths to the Cline configuration files.

    Returns:
        List[Path]: The paths to the configuration files
    """
    from .config import get_vscode_settings_paths

    return get_vscode_settings_paths()


def configure_cline(config_paths: List[Path] | None = None) -> None:
    """Configure integration with Cline.

    Automatically sets up the MCP server configuration in Cline's settings.
    Handles installation, updates, and environment configuration.

    Args:
        config_paths: Optional paths to configuration files (for testing)

    Raises:
        FileNotFoundError: If configuration file cannot be found
        PermissionError: If there are permission issues accessing the config
            file
        json.JSONDecodeError: If configuration file contains invalid JSON
        OSError: If there are file system related errors
    """
    try:
        # Get Cline config paths
        if config_paths is None:
            config_paths = get_config_paths()

        server_name = "aindreyway-neurolora"
        server_config: ServerConfig = {
            "command": "uvx",
            "args": ["mcp-server-neurolora"],
            "disabled": False,
            "alwaysAllow": [],
            "env": {"PYTHONUNBUFFERED": "1"},
        }

        for config_path in config_paths:
            try:
                config: ClinesConfig
                if config_path.exists():
                    try:
                        with open(config_path, "r", encoding="utf-8") as f:
                            try:
                                raw_config = json.load(f)
                                if "mcpServers" not in raw_config:
                                    raw_config["mcpServers"] = {}
                                config = cast(ClinesConfig, raw_config)
                            except json.JSONDecodeError as e:
                                logger.error(f"Invalid JSON in {config_path}: {e}")
                                continue
                    except PermissionError as e:
                        logger.error(f"Permission denied reading {config_path}: {e}")
                        continue
                    except OSError as e:
                        logger.error(f"Error reading {config_path}: {e}")
                        continue
                else:
                    try:
                        logger.info(f"Creating new configuration at {config_path}")
                        config_path.parent.mkdir(parents=True, exist_ok=True)
                        config = {"mcpServers": {}}
                    except PermissionError as e:
                        logger.error(
                            f"Permission denied creating directory for "
                            f"{config_path}: {e}"
                        )
                        continue
                    except OSError as e:
                        logger.error(f"Error creating directory for {config_path}: {e}")
                        continue

                # Only add configuration if server doesn't exist
                if server_name not in config["mcpServers"]:
                    config["mcpServers"][server_name] = server_config
                    try:
                        with open(config_path, "w", encoding="utf-8") as f:
                            json.dump(config, f, indent=2)
                        logger.info(
                            f"Added server configuration to Cline at {config_path}"
                        )
                    except (PermissionError, OSError) as e:
                        logger.error(f"Error writing to {config_path}: {e}")
                        continue
                else:
                    current_config = config["mcpServers"][server_name]
                    # Only update command and args if needed
                    if (
                        current_config.get("command") != server_config["command"]
                        or current_config.get("args") != server_config["args"]
                    ):
                        current_config["command"] = server_config["command"]
                        current_config["args"] = server_config["args"]
                        try:
                            with open(config_path, "w", encoding="utf-8") as f:
                                json.dump(config, f, indent=2)
                            logger.info(
                                f"Updated command configuration at {config_path}"
                            )
                        except (PermissionError, OSError) as e:
                            logger.error(f"Error updating {config_path}: {e}")
                            continue
                    else:
                        logger.info(
                            f"Server already configured in Cline at {config_path}"
                        )

            except (FileNotFoundError, NotADirectoryError) as e:
                logger.error(f"File system error configuring {config_path}: {e}")
                continue
            except (TypeError, ValueError, AttributeError) as e:
                logger.error(f"Configuration data error in {config_path}: {e}")
                continue
            except Exception as exc:
                logger.exception(
                    f"Critical error configuring {config_path}: {exc}. "
                    f"This is likely a bug that should be reported."
                )
                continue

    except Exception as exc:
        logger.exception(
            f"Critical error configuring {config_paths}: {exc}. "
            f"This is likely a bug that should be reported."
        )


def main() -> None:
    """Run the server in production or terminal mode.

    This function initializes and runs either:
    - Production mode: MCP server with stdio transport
    - Terminal mode: Interactive JSON-RPC terminal for development
    """
    # Configure MCP module logging
    configure_mcp_logging()

    # Set up environment
    setup_environment()

    # Parse command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--dev":
        logger.info("Starting in terminal mode")
        asyncio.run(run_terminal_server())
        return

    try:
        logger.info("Starting in production mode")

        # Configure Cline integration
        configure_cline()

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

        # Initialize and run production MCP server
        asyncio.run(run_mcp_server())

    except (FileNotFoundError, PermissionError) as e:
        error_msg = (
            f"Server startup failed due to file system error: {e}\n"
            "Please check file permissions and paths."
        )
        logger.error(error_msg)
        sys.exit(1)
    except json.JSONDecodeError as e:
        error_msg = (
            f"Server startup failed due to invalid configuration: {e}\n"
            "Please check your configuration files."
        )
        logger.error(error_msg)
        sys.exit(1)
    except Exception as e:
        error_msg = (
            f"Unexpected error during server startup: {e.__class__.__name__}\n"
            f"Details: {str(e)}\n"
            "This is likely a bug that should be reported."
        )
        logger.exception(error_msg)
        sys.exit(1)


def main_entry() -> None:
    """Entry point for the NeuroLoRA server.

    Supports two modes:
    - Production mode: Run as MCP server with stdio transport
    - Terminal mode: Run with JSON-RPC terminal interface (use --dev flag)
    """
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except KeyError as e:
        logger.error(f"Missing required configuration key: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Invalid configuration value: {e}")
        sys.exit(1)
    except Exception as exc:
        logger.exception(
            "Unexpected server error: "
            f"{exc}. This is likely a bug that should be reported."
        )
        sys.exit(1)


if __name__ == "__main__":
    main_entry()
