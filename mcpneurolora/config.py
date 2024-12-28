"""Configuration utilities for MCP server."""

import json
import os
import platform
from pathlib import Path
from typing import Dict, List, Optional, TypedDict, cast

from .logging import get_logger, LogCategory

# Get module logger
logger = get_logger(__name__, LogCategory.CONFIG)


class EnvConfig(TypedDict, total=False):
    """Environment configuration.

    Required:
        - AI_MODEL: Name of the model to use (e.g. "o1", "gemini-2.0-flash")
        - API keys: OPENAI_API_KEY or GEMINI_API_KEY based on chosen model
        - AI_TIMEOUT_MS: Timeout for AI operations in milliseconds
          (default: 300000)
        - MAX_FILE_SIZE_MB: Maximum file size in MB to process (default: 1)
        - PREVIEW_SIZE_KB: Size of preview for large files in KB (default: 64)
    """

    AI_MODEL: str
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str
    AI_TIMEOUT_MS: str
    MAX_FILE_SIZE_MB: str
    PREVIEW_SIZE_KB: str


# Default values for file size limits
DEFAULT_MAX_FILE_SIZE_MB = 1
DEFAULT_PREVIEW_SIZE_KB = 64


class ServerConfig(TypedDict):
    env: EnvConfig


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
                flatpak_path = (
                    home / ".var/app/com.visualstudio.code/config/Code/User"
                )
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


class VsCodeSettings(TypedDict):
    mcpServers: Dict[str, ServerConfig]


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
            logger.info("Loading VSCode settings from: %s", settings_path)
            with open(settings_path, "r", encoding="utf-8") as f:
                content = f.read()
                logger.debug("Raw file content length: %d", len(content))
                settings = json.loads(content)
                logger.info("Successfully parsed JSON settings")
                return cast(VsCodeSettings, settings)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON settings: %s", str(e))
            continue
        except FileNotFoundError:
            logger.error(
                "VSCode settings file not found at: %s", settings_path
            )
            continue
        except PermissionError:
            logger.error("Permission denied reading VSCode settings")
            continue
        except OSError as e:
            logger.error("System error reading VSCode settings: %s", str(e))
            continue
        except (ValueError, TypeError) as e:
            logger.error("Invalid VSCode settings format: %s", str(e))
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
    server_config = cast(
        ServerConfig, mcp_servers.get("aindreyway-neurolora", {})
    )
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

    # Set default values for file size limits if not set
    if "MAX_FILE_SIZE_MB" not in os.environ:
        os.environ["MAX_FILE_SIZE_MB"] = str(DEFAULT_MAX_FILE_SIZE_MB)
        logger.info(
            "Using default MAX_FILE_SIZE_MB: %s MB", DEFAULT_MAX_FILE_SIZE_MB
        )

    if "PREVIEW_SIZE_KB" not in os.environ:
        os.environ["PREVIEW_SIZE_KB"] = str(DEFAULT_PREVIEW_SIZE_KB)
        logger.info(
            "Using default PREVIEW_SIZE_KB: %s KB", DEFAULT_PREVIEW_SIZE_KB
        )

    # Set other environment variables that don't exist yet
    for key, value in env_config.items():
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
                logger.info(
                    "API key %s is already set",
                    key,
                )
            else:
                logger.info(
                    "Using existing env var: %s = %s", key, os.environ[key]
                )

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
