"""File locking utilities for safe concurrent file operations."""

import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

logger = logging.getLogger(__name__)


class FileLockError(Exception):
    """Error raised when file locking fails."""

    pass


@contextmanager
def file_lock(path: Path) -> Generator[None, None, None]:
    """Create a lock file to prevent concurrent access.

    This function creates a .lock file alongside the target file
    to prevent concurrent access. The lock file is automatically
    removed when the context manager exits.

    Args:
        path: Path to the file to lock

    Yields:
        None

    Raises:
        FileLockError: If lock cannot be acquired or released
    """
    lock_path = path.parent / f"{path.name}.lock"
    lock_fd: Optional[int] = None

    try:
        # Create lock file directory if it doesn't exist
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        # Try to create lock file
        try:
            # Open with O_CREAT | O_EXCL to ensure atomic creation
            lock_fd = os.open(
                lock_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o644,
            )
        except FileExistsError:
            raise FileLockError(f"Lock exists for {path}")
        except PermissionError:
            raise FileLockError(f"Permission denied creating lock for {path}")
        except OSError as e:
            raise FileLockError(f"Error creating lock for {path}: {e}")

        logger.debug("Acquired lock for %s", path)
        yield

    finally:
        # Always try to clean up lock file
        if lock_fd is not None:
            try:
                os.close(lock_fd)
            except OSError as e:
                logger.error("Error closing lock file: %s", e)

        try:
            if lock_path.exists():
                lock_path.unlink()
                logger.debug("Released lock for %s", path)
        except OSError as e:
            logger.error("Error removing lock file: %s", e)
