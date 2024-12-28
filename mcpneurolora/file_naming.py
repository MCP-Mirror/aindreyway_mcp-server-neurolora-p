"""File naming utilities for consistent file naming across the project."""

import re
from datetime import datetime
from enum import Enum
from typing import Optional, Pattern


class FileType(Enum):
    """Enumeration of file types with their prefixes."""

    CODE = "CODE"
    IMPROVE_PROMPT = "IMPROVE_PROMPT"
    IMPROVE_RESULT = "IMPROVE_RESULT"
    REQUEST_PROMPT = "REQUEST_PROMPT"
    REQUEST_RESULT = "REQUEST_RESULT"
    REPORT_PROMPT = "REPORT_PROMPT"
    REPORT_RESULT = "REPORT_RESULT"
    FULL_TREE = "FULL_TREE_PROJECT_FILES"


def slugify(text: str) -> str:
    """Convert text to slug format.

    Args:
        text: Text to convert to slug

    Returns:
        str: Slugified text (lowercase, with spaces/special chars replaced by
             hyphens)
    """
    # Convert to lowercase and replace spaces/special chars with hyphens
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def format_filename(
    file_type: FileType,
    title: Optional[str] = None,
    timestamp: Optional[datetime] = None,
    provider: Optional[str] = None,
) -> str:
    """Format filename according to unified naming scheme.

    Args:
        file_type: Type of file from FileType enum
        title: Optional title to include in filename (will be slugified)
        timestamp: Optional timestamp (defaults to current time)
        provider: Optional provider name (e.g. CLAUDE, OPENAI, GEMINI)

    Returns:
        str: Formatted filename following the pattern:
             {TYPE}_{PROVIDER}_{YYYYMMDD_HHMMSS}_{slug}.md
    """
    # Special case for FULL_TREE type
    if file_type == FileType.FULL_TREE:
        return "FULL_TREE_PROJECT_FILES.md"

    # Use current time if not provided
    if timestamp is None:
        timestamp = datetime.now()

    # Format timestamp
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")

    # Format provider if provided
    provider_str = f"_{provider.upper()}" if provider else ""

    # Format title if provided
    if title:
        title_slug = slugify(title)
        return (
            f"{file_type.value}{provider_str}_{timestamp_str}_{title_slug}.md"
        )

    # For files without title (like project reports)
    return f"{file_type.value}{provider_str}_{timestamp_str}.md"


def parse_filename(filename: str) -> tuple[FileType, datetime, Optional[str]]:
    """Parse filename to extract components.

    Args:
        filename: Filename to parse

    Returns:
        tuple: (FileType, datetime, Optional[title_slug])

    Raises:
        ValueError: If filename doesn't match expected pattern
    """
    # Special case for FULL_TREE type
    if filename == "FULL_TREE_PROJECT_FILES.md":
        return FileType.FULL_TREE, datetime.now(), None

    # Match pattern with optional title
    pattern = r"^([A-Z_]+)_(\d{8}_\d{6})(?:_([a-z0-9-]+))?\.md$"
    match = re.match(pattern, filename)

    if not match:
        raise ValueError(f"Invalid filename format: {filename}")

    # Extract components
    type_str, timestamp_str, title_slug = match.groups()

    # Convert type string to enum
    try:
        file_type = FileType(type_str)
    except ValueError:
        raise ValueError(f"Unknown file type: {type_str}")

    # Parse timestamp
    try:
        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
    except ValueError:
        raise ValueError(f"Invalid timestamp format: {timestamp_str}")

    return file_type, timestamp, title_slug


def get_file_pattern(file_type: FileType) -> Pattern[str]:
    """Get regex pattern for matching files of specified type.

    Args:
        file_type: Type of file to match

    Returns:
        Pattern[str]: Compiled regex pattern
    """
    if file_type == FileType.FULL_TREE:
        return re.compile(r"FULL_TREE_PROJECT_FILES\.md$")
    return re.compile(f"{file_type.value}_.*\\.md$")
