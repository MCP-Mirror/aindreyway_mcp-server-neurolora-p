"""Validation utilities for server operations."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, TypeVar, Union

from pydantic import ValidationError

from ..tools.definitions import COMMANDS

logger = logging.getLogger(__name__)

T = TypeVar("T")


def validate_command(name: str) -> None:
    """Validate command exists and is an MCP tool.

    Args:
        name: Command name to validate

    Raises:
        ValueError: If command is invalid or not an MCP tool
    """
    if name not in COMMANDS:
        raise ValueError(f"Unknown tool: {name}")

    cmd_def = COMMANDS[name]
    if not cmd_def["is_mcp_tool"]:
        raise ValueError(f"Not an MCP tool: {name}")


def validate_model_type(validated: Any, expected_type: type[T], command_name: str) -> T:
    """Validate model type matches expected type.

    Args:
        validated: Validated model instance
        expected_type: Expected model type
        command_name: Command name for error messages

    Returns:
        T: Validated model instance

    Raises:
        ValueError: If model type doesn't match expected type
    """
    if not isinstance(validated, expected_type):
        raise ValueError(f"Invalid model type for {command_name}")
    return validated


def validate_error_response(error: Any) -> Optional[str]:
    """Validate and extract error message from response.

    Args:
        error: Error response to validate

    Returns:
        Optional[str]: Error message if valid, None otherwise
    """
    if not isinstance(error, dict):
        return None

    # Cast error to Dict[str, Any] after type check
    error_dict: Dict[str, Any] = error
    message = error_dict.get("message", "")

    # Handle non-string messages
    if not isinstance(message, str):
        return None

    # Return None for empty messages
    return message.strip() or None


def validate_command_model(name: str) -> Any:
    """Validate command has a model and return it.

    Args:
        name: Command name

    Returns:
        Any: Command model class

    Raises:
        ValueError: If command has no model
    """
    cmd_def = COMMANDS[name]
    model_cls = cmd_def["model"]
    if not model_cls:
        raise ValueError(f"Tool has no input model: {name}")
    return model_cls


def validate_path(path: Union[str, Path]) -> Path:
    """Validate and convert path to Path object.

    Args:
        path: Path to validate (string or Path)

    Returns:
        Path: Validated Path object

    Raises:
        ValueError: If path is invalid
    """
    try:
        # Always convert to Path - it will work for both str and Path
        return Path(path)
    except TypeError as e:
        raise ValueError(f"Invalid path type: {type(path)} - {e}")
    except Exception as e:
        raise ValueError(f"Invalid path: {str(e)}")


def validate_arguments(model_cls: Any, arguments: Dict[str, Any]) -> Any:
    """Validate arguments using model.

    Args:
        model_cls: Model class to use for validation
        arguments: Arguments to validate

    Returns:
        Any: Validated model instance

    Raises:
        ValueError: If validation fails
    """
    try:
        return model_cls.model_validate(arguments)
    except ValidationError as e:
        logger.error("Argument validation failed: %s", str(e))
        raise ValueError(f"Invalid arguments: {str(e)}")
    except Exception as e:
        logger.error("Unexpected error during validation: %s", str(e))
        raise ValueError(f"Invalid arguments: {str(e)}")
