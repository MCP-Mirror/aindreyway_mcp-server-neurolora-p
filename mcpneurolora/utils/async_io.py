"""Asynchronous I/O utilities."""

import asyncio
import os
from pathlib import Path
from typing import Callable, Iterator, List, Optional, Tuple

from ..log_utils import LogCategory, get_logger

logger = get_logger(__name__, LogCategory.TOOLS)


async def read_file(path: Path) -> str:
    """Read file content asynchronously.

    Args:
        path: Path to file to read

    Returns:
        str: File content or error message
    """
    try:
        loop = asyncio.get_running_loop()

        # Check if path is a directory
        is_dir_result = await loop.run_in_executor(None, path.is_dir)
        if is_dir_result:
            return (
                f"[System error: Cannot read directory as file: {path}\n"
                f"This is a directory and should be processed using walk_directory.\n"
                f"Current working directory: {Path.cwd()}\n"
                f"Absolute path: {path.absolute()}\n"
                f"Parent directory: {path.parent}\n"
                f"Directory name: {path.name}]"
            )

        return await loop.run_in_executor(
            None, lambda: path.read_text(encoding="utf-8")
        )
    except FileNotFoundError:
        logger.error("File not found: %s", path)
        return "[File not found]"
    except PermissionError:
        logger.error("Permission denied accessing file: %s", path)
        return "[Permission denied]"
    except UnicodeDecodeError:
        logger.warning("Binary file detected: %s", path)
        return "[Binary file content not shown]"
    except OSError as e:
        logger.error("System error reading file %s: %s", path, str(e))
        return f"[System error: {str(e)}]"


async def write_file(path: Path, content: str) -> None:
    """Write content to file asynchronously.

    Args:
        path: Path to write to
        content: Content to write

    Raises:
        OSError: If there's an error writing to the file
    """
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, lambda: path.write_text(content, encoding="utf-8")
        )
    except OSError as e:
        logger.error("Error writing to %s: %s", path, str(e))
        raise


async def ensure_dir(path: Path) -> None:
    """Ensure directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists

    Raises:
        OSError: If there's an error creating the directory
    """
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, lambda: path.mkdir(parents=True, exist_ok=True)
        )
    except OSError as e:
        logger.error("Error creating directory %s: %s", path, str(e))
        raise


async def get_file_size(path: Path) -> Optional[int]:
    """Get file size asynchronously.

    Args:
        path: Path to get size for

    Returns:
        Optional[int]: File size in bytes or None if error
    """
    try:
        loop = asyncio.get_running_loop()
        stat = await loop.run_in_executor(None, path.stat)
        return stat.st_size
    except OSError:
        return None


async def is_dir(path: Path) -> bool:
    """Check if path is a directory asynchronously.

    Args:
        path: Path to check

    Returns:
        bool: True if path is a directory
    """
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, path.is_dir)
    except OSError as e:
        logger.error("Error checking if path is directory %s: %s", path, str(e))
        return False


async def path_exists(path: Path) -> bool:
    """Check if path exists asynchronously.

    Args:
        path: Path to check

    Returns:
        bool: True if path exists
    """
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, path.exists)
    except OSError as e:
        logger.error("Error checking path %s: %s", path, str(e))
        return False


async def count_lines(path: Path) -> int:
    """Count non-empty lines in file asynchronously.

    Args:
        path: Path to file

    Returns:
        int: Number of non-empty lines
    """
    try:
        loop = asyncio.get_running_loop()

        # Check if binary first
        is_binary = await loop.run_in_executor(
            None, lambda: b"\0" in path.read_bytes()[:1024]
        )
        if is_binary:
            return 0

        # Count lines if not binary
        content = await read_file(path)
        return len([line for line in content.splitlines() if line.strip()])
    except OSError:
        return 0


def _walk(path: Path) -> Iterator[Tuple[Path, List[str], List[str]]]:
    """Helper function to wrap os.walk() for type hints.

    Args:
        path: Directory to walk

    Returns:
        Iterator yielding tuples of (root_path, dir_names, file_names)
    """
    for root, dirs, files in os.walk(path):
        yield Path(root), dirs, files


async def walk_directory(path: Path, ignore_func: Callable[[Path], bool]) -> List[Path]:
    """Walk directory asynchronously, filtering with ignore function.

    Args:
        path: Directory to walk
        ignore_func: Function that takes a Path and returns True if it should
                    be ignored

    Returns:
        List[Path]: List of non-ignored file paths
    """
    try:
        loop = asyncio.get_running_loop()
        result: List[Path] = []

        for root_path, dirs, files in await loop.run_in_executor(
            None, lambda: list(_walk(path))
        ):
            # Filter directories
            dirs[:] = [d for d in dirs if not ignore_func(root_path / d)]

            # Add non-ignored files
            for file in files:
                file_path = root_path / file
                if not ignore_func(file_path):
                    result.append(file_path)

        return sorted(result)
    except OSError as e:
        logger.error("Error walking directory %s: %s", path, str(e))
        return []
