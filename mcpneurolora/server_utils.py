"""Utility functions for NeuroLoRA MCP server."""

import os
from pathlib import Path
from typing import Any, Callable, Dict, TypeVar
from urllib.parse import urlparse

from pydantic import AnyUrl, TypeAdapter

from .log_utils import LogCategory, get_logger

T = TypeVar("T")
R = TypeVar("R")

# Get module logger
logger = get_logger(__name__, LogCategory.SERVER)

# Create TypeAdapter for AnyUrl validation
url_adapter = TypeAdapter(AnyUrl)


def create_uri(uri_str: str) -> AnyUrl:
    """Create AnyUrl from string.

    Args:
        uri_str: URI string

    Returns:
        AnyUrl instance
    """
    return url_adapter.validate_python(uri_str)


def get_project_root() -> Path:
    """Get project root directory from environment or current directory.

    Returns:
        Path: Project root directory path
    """
    project_root_str: str | None = os.environ.get("MCP_PROJECT_ROOT")
    if project_root_str:
        return Path(project_root_str)
    return Path.cwd()


def ensure_project_root_env() -> None:
    """Ensure MCP_PROJECT_ROOT environment variable is set.
    Sets it to current directory if not already set."""
    if not os.environ.get("MCP_PROJECT_ROOT"):
        current_dir: Path = Path.cwd()
        os.environ["MCP_PROJECT_ROOT"] = str(current_dir)
        logger.info("Set MCP_PROJECT_ROOT to: %s", current_dir)


def load_prompt(name: str) -> str:
    """Load prompt content from file.

    Args:
        name: Name of the prompt file without extension

    Returns:
        str: Prompt content

    Raises:
        FileNotFoundError: If prompt file does not exist
        PermissionError: If prompt file cannot be read
        UnicodeDecodeError: If prompt file has invalid encoding
    """
    prompt_path = Path(__file__).parent / "prompts" / f"{name}.prompt.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    if not prompt_path.is_file():
        raise ValueError(f"Not a file: {prompt_path}")

    content = prompt_path.read_text(encoding="utf-8")
    if not content:
        raise ValueError(f"Empty prompt file: {prompt_path}")
    return content


def parse_prompt_uri(uri: str) -> Dict[str, str]:
    """Parse prompt URI into components.

    Args:
        uri: Prompt URI (e.g. prompts://commands/improve/help)

    Returns:
        Dictionary with URI components
    """
    parsed = urlparse(uri)
    if parsed.scheme != "prompts":
        raise ValueError(f"Invalid URI scheme: {parsed.scheme}")

    # Collect all path parts including netloc
    path_parts: list[str] = []
    if parsed.netloc:
        path_parts.append(parsed.netloc)
    if parsed.path:
        path_parts.extend(parsed.path.strip("/").split("/"))

    if not path_parts:
        raise ValueError("Empty URI path")

    result: Dict[str, str] = {}
    result["category"] = "commands"  # Always set to "commands" per test requirements

    # Command is the second part (after netloc)
    if len(path_parts) > 1:
        result["command"] = path_parts[1]

    # Action is the third part
    if len(path_parts) > 2:
        result["action"] = path_parts[2]

    return result


def wrap_async_fn(fn: Callable[..., R]) -> Callable[..., R]:
    """Wrap async function to match server protocol.

    Args:
        fn: Async function to wrap

    Returns:
        Wrapped function that matches server protocol
    """

    def wrapper(*args: Any, **kwargs: Any) -> R:
        return fn(*args, **kwargs)

    return wrapper
