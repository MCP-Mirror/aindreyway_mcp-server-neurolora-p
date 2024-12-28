"""Input validation utilities for secure file operations."""

import logging
import os
from pathlib import Path, PurePath
from typing import Optional, Union

logger = logging.getLogger(__name__)


def validate_path(
    path: Union[str, Path], base_dir: Optional[Path] = None
) -> Path:
    """Validate and sanitize file path.

    This function ensures that the provided path:
    1. Is a valid path string
    2. Does not contain path traversal attempts
    3. Is within the allowed base directory (if provided)

    Args:
        path: Path to validate
        base_dir: Optional base directory to restrict access to

    Returns:
        Path: Validated and sanitized path

    Raises:
        ValueError: If path is invalid or outside base directory
        TypeError: If path is not a string or Path object
    """
    try:
        # Convert to Path and resolve to absolute path
        path = Path(path).resolve()

        # If base_dir is provided, ensure path is within it
        if base_dir is not None:
            base_dir = Path(base_dir).resolve()
            try:
                path.relative_to(base_dir)
            except ValueError:
                raise ValueError(
                    f"Path {path} is outside base directory {base_dir}"
                )

        return path

    except Exception as e:
        logger.error(f"Invalid path {path}: {e}")
        raise ValueError(f"Invalid path: {e}")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and invalid characters.

    Args:
        filename: Filename to sanitize

    Returns:
        str: Sanitized filename

    Raises:
        ValueError: If filename is empty or invalid
    """
    if not filename:
        raise ValueError("Filename must be a non-empty string")

    # Get just the filename part, removing any path components
    safe_name = PurePath(filename).name

    # Remove any null bytes
    safe_name = safe_name.replace("\0", "")

    # Remove any leading/trailing whitespace
    safe_name = safe_name.strip()

    if not safe_name:
        raise ValueError("Invalid filename")

    return safe_name


def is_safe_path(
    path: Union[str, Path], allowed_dirs: Optional[list[Path]] = None
) -> bool:
    """Check if path is safe to access.

    Args:
        path: Path to check
        allowed_dirs: Optional list of allowed directories

    Returns:
        bool: True if path is safe to access
    """
    try:
        path = Path(path).resolve()

        # Check if path exists
        if not path.exists():
            return False

        # If allowed_dirs provided, check if path is in one of them
        if allowed_dirs:
            return any(
                str(path).startswith(str(allowed_dir))
                for allowed_dir in allowed_dirs
            )

        # Check basic file permissions
        return os.access(path, os.R_OK)

    except Exception as e:
        logger.error(f"Error checking path safety for {path}: {e}")
        return False
