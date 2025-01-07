"""Configuration utilities for MCP server."""

import json
import os
import platform
from pathlib import Path
from typing import List, Optional, cast

from .log_utils import LogCategory, get_logger
from .types.vscode import ServerConfig, VsCodeSettings

# Get module logger
logger = get_logger(__name__, LogCategory.CONFIG)

# Default values for file size limits
DEFAULT_MAX_FILE_SIZE_MB = 1
DEFAULT_PREVIEW_SIZE_KB = 64


def get_vscode_settings_paths() -> List[Path]:
    """Get paths to VSCode settings based on current OS.

    Returns:
        List of paths to VSCode settings directories
    """
    system = platform.system().lower()
    home = Path.home()

    # Try environment variable first
    if vscode_path := os.environ.get("VSCODE_CONFIG_PATH"):
        base_path = Path(vscode_path)
    else:
        # Define default paths for different OS
        if system == "darwin":
            base_path = home / "Library/Application Support/Code/User"
            # Check for VSCode Insiders
            if not base_path.exists():
                insiders_path = (
                    home / "Library/Application Support/Code - Insiders/User"
                )
                base_path = insiders_path
        elif system == "linux":
            base_path = home / ".config/Code/User"
            # Check for VSCode Insiders and Flatpak
            if not base_path.exists():
                base_path = home / ".config/Code - Insiders/User"
            if not base_path.exists():
                flatpak_path = home / ".var/app/com.visualstudio.code/config/Code/User"
                base_path = flatpak_path
        elif system == "windows":
            # Try APPDATA environment variable first
            if appdata := os.environ.get("APPDATA"):
                base_path = Path(appdata) / "Code/User"
                if not base_path.exists():
                    base_path = Path(appdata) / "Code - Insiders/User"
            else:
                base_path = home / "AppData/Roaming/Code/User"
        else:
            logger.warning("Unsupported operating system: %s", system)
            return []

    if not base_path.exists():
        logger.warning("VSCode config directory not found at: %s", base_path)
        return []

    # Define settings paths for different VSCode extensions
    settings_dir = "globalStorage"
    claude_path = (
        base_path
        / settings_dir
        / "saoudrizwan.claude-dev/settings/cline_mcp_settings.json"
    )
    roo_path = (
        base_path
        / settings_dir
        / "rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json"
    )
    settings_paths = [claude_path, roo_path]

    existing_paths = [p for p in settings_paths if p.exists()]
    if not existing_paths:
        logger.warning("No VSCode settings found in any location")
        return []

    return existing_paths


def load_vscode_settings() -> Optional[VsCodeSettings]:
    """Load settings from VSCode configuration.

    Returns:
        Dict with settings or None if no valid settings found
    """
    settings_paths = get_vscode_settings_paths()
    if not settings_paths:
        return None

    for settings_path in settings_paths:
        try:
            logger.info("Attempting to load VSCode settings from: %s", settings_path)

            # Check file existence and permissions first
            if not settings_path.exists():
                logger.error(
                    "VSCode settings file not found at: %s\n"
                    "Please ensure the file exists and the path is correct.",
                    settings_path,
                )
                continue

            if not os.access(settings_path, os.R_OK):
                logger.error(
                    "Permission denied reading VSCode settings at: %s\n"
                    "Please check file permissions.",
                    settings_path,
                )
                continue

            # Read and parse settings
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError as err:
                logger.error(
                    "Failed to decode VSCode settings file at %s:\n"
                    "%s\nPlease ensure the file is properly encoded as UTF-8.",
                    settings_path,
                    str(err),
                )
                continue
            except OSError as err:
                logger.error(
                    "System error reading VSCode settings at %s:\n"
                    "%s\nThis may indicate a file system or I/O problem.",
                    settings_path,
                    str(err),
                )
                continue

            # Validate content
            if not content.strip():
                logger.error(
                    "VSCode settings file is empty at: %s\n"
                    "Please ensure the file contains valid configuration.",
                    settings_path,
                )
                continue

            logger.debug("Raw file content length: %d", len(content))

            try:
                settings = json.loads(content)
            except json.JSONDecodeError as err:
                logger.error(
                    "Failed to parse JSON settings at %s: %s\n"
                    "Line %d, Column %d: %s\n"
                    "Please ensure the file contains valid JSON.",
                    settings_path,
                    str(err),
                    err.lineno,
                    err.colno,
                    err.msg,
                )
                continue

            # Type validation
            if not isinstance(settings, dict):
                logger.error(
                    "Invalid settings format at %s: expected dictionary, "
                    "got %s\n"
                    "Please ensure the configuration follows the format.",
                    settings_path,
                    type(settings).__name__,
                )
                continue

            if "mcpServers" not in settings:
                logger.warning(
                    "No 'mcpServers' configuration found in %s\n"
                    "The file may be missing required configuration.",
                    settings_path,
                )

            logger.info(
                "Successfully loaded and validated settings from: %s",
                settings_path,
            )
            return cast(VsCodeSettings, settings)

        except Exception as exc:
            logger.exception(
                "Unexpected error loading VSCode settings from %s: %s\n"
                "This is likely a bug that should be reported.",
                settings_path,
                exc,
            )
            continue

    return None


def get_server_config() -> Optional[ServerConfig]:
    """Get configuration for our MCP server from VSCode settings.

    Returns:
        Dict with server config or None if not found
    """
    settings = load_vscode_settings()
    if not settings:
        return None

    mcp_servers = settings.get("mcpServers", {})
    server_config = cast(ServerConfig, mcp_servers.get("aindreyway-neurolora", {}))
    return server_config


def setup_environment() -> None:
    """Set up environment variables from VSCode settings."""
    server_config = get_server_config()
    if not server_config:
        logger.warning("Server configuration not found in VSCode settings")
        print_config_instructions()
        return

    env_config = server_config.get("env", {})
    logger.info("Loaded env config: %s", env_config)

    try:
        # Set default values for file size limits if not set
        if "MAX_FILE_SIZE_MB" not in os.environ:
            os.environ["MAX_FILE_SIZE_MB"] = str(DEFAULT_MAX_FILE_SIZE_MB)
            logger.info(
                "Using default MAX_FILE_SIZE_MB: %s MB",
                DEFAULT_MAX_FILE_SIZE_MB,
            )

        if "PREVIEW_SIZE_KB" not in os.environ:
            os.environ["PREVIEW_SIZE_KB"] = str(DEFAULT_PREVIEW_SIZE_KB)
            logger.info("Using default PREVIEW_SIZE_KB: %s KB", DEFAULT_PREVIEW_SIZE_KB)

        # Set other environment variables that don't exist yet
        for key, value in env_config.items():
            try:
                if key not in os.environ:
                    # Convert value to string and strip whitespace
                    str_value = str(value).strip()
                    os.environ[key] = str_value
                    if key in ["OPENAI_API_KEY", "GEMINI_API_KEY"]:
                        logger.info(
                            "Set API key: %s (length: %d)",
                            key,
                            len(str_value),
                        )
                    else:
                        logger.info("Set env var from config: %s = %s", key, str_value)
                else:
                    if key in ["OPENAI_API_KEY", "GEMINI_API_KEY"]:
                        logger.info("API key %s is already set", key)
                    else:
                        logger.info(
                            "Using existing env var: %s = %s",
                            key,
                            os.environ[key],
                        )
            except (TypeError, ValueError) as exc:
                logger.error("Invalid value for environment variable %s: %s", key, exc)
                continue
    except OSError as exc:
        logger.error("Failed to set environment variables: %s", exc)

    if not os.environ.get("AI_MODEL"):
        logger.warning("AI_MODEL not configured in VSCode settings")
        print_config_instructions()


def print_config_instructions() -> None:
    """Print instructions for configuring the server."""
    settings_paths = get_vscode_settings_paths()
    if not settings_paths:
        path_msg = "(path depends on your OS)"
    else:
        path_msg = "\n".join(str(p) for p in settings_paths)

    print("\nConfiguration required:")
    print(f"1. Open VSCode settings: {path_msg}")
    print("2. Add to 'aindreyway-neurolora' -> 'env':")
    print('   "AI_MODEL": Model name (e.g. "o1", "gemini-2.0-flash-exp")')
    print("   Required API key based on model:")
    print('   - For OpenAI models (o1, o1-preview-*): "OPENAI_API_KEY"')
    print('   - For Gemini models: "GEMINI_API_KEY"')
    print("\n   Optional settings:")
    print(
        '   - "MAX_FILE_SIZE_MB": Maximum file size in MB '
        f"(default: {DEFAULT_MAX_FILE_SIZE_MB})"
    )
    print(
        '   - "PREVIEW_SIZE_KB": Preview size for large files in KB '
        f"(default: {DEFAULT_PREVIEW_SIZE_KB})"
    )
