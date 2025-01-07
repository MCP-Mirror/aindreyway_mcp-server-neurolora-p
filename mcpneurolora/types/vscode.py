"""VSCode settings types."""

from typing import Dict, List, TypedDict

__all__ = ["ServerEnvConfig", "ServerConfig", "VsCodeSettings"]


class ServerEnvConfig(TypedDict, total=False):
    """Environment configuration for MCP server."""

    AI_MODEL: str
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str
    AI_TIMEOUT_MS: str
    MAX_FILE_SIZE_MB: str
    PREVIEW_SIZE_KB: str
    PYTHONUNBUFFERED: str


class ServerConfig(TypedDict):
    """Configuration for MCP server."""

    command: str
    args: List[str]
    disabled: bool
    alwaysAllow: List[str]
    env: Dict[str, str]


class VsCodeSettings(TypedDict):
    """VSCode settings structure."""

    mcpServers: Dict[str, ServerConfig]
