"""Tests for input validation utilities."""

from pathlib import Path
from unittest.mock import patch

import pytest

from mcpneurolora.utils.input_validation import (
    is_safe_path,
    sanitize_filename,
    validate_path,
)


def test_validate_path() -> None:
    """Test path validation."""
    # Test valid paths
    assert validate_path("test.txt") == Path("test.txt").resolve()
    assert validate_path(Path("test.txt")) == Path("test.txt").resolve()

    # Test with base directory
    base_dir = Path("/base/dir").resolve()
    test_path = base_dir / "test.txt"
    assert validate_path(test_path, base_dir) == test_path.resolve()

    # Test path traversal attempts
    with pytest.raises(ValueError):
        validate_path("../test.txt", base_dir)

    with pytest.raises(ValueError):
        validate_path("/etc/passwd", base_dir)

    # Test invalid paths
    with pytest.raises(ValueError):
        validate_path("\0invalid")


def test_sanitize_filename() -> None:
    """Test filename sanitization."""
    # Test valid filenames
    assert sanitize_filename("test.txt") == "test.txt"
    assert sanitize_filename("my file.txt") == "my file.txt"
    assert sanitize_filename(" spaces.txt ") == "spaces.txt"

    # Test path components are removed
    assert sanitize_filename("/path/to/file.txt") == "file.txt"
    assert sanitize_filename("../file.txt") == "file.txt"

    # Test null bytes are removed
    assert sanitize_filename("test\0.txt") == "test.txt"

    # Test empty or invalid filenames
    with pytest.raises(ValueError):
        sanitize_filename("")

    with pytest.raises(ValueError):
        sanitize_filename("   ")

    with pytest.raises(ValueError):
        sanitize_filename("\0")


def test_is_safe_path(tmp_path: Path) -> None:
    """Test path safety checks."""
    # Create test files and directories
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    test_file = test_dir / "test.txt"
    test_file.touch()

    other_dir = tmp_path / "other_dir"
    other_dir.mkdir()
    other_file = other_dir / "other.txt"
    other_file.touch()

    try:
        # Test existing file with read permissions
        assert is_safe_path(test_file) is True

        # Test with allowed directories
        allowed_dirs = [test_dir]
        assert is_safe_path(test_file, allowed_dirs) is True

        # Test file outside allowed directories
        assert is_safe_path(other_file, allowed_dirs) is False

        # Test non-existent path
        assert is_safe_path(tmp_path / "nonexistent.txt") is False

        # Test path with no read permissions
        with patch("os.access") as mock_access:
            mock_access.return_value = False
            assert is_safe_path(test_file) is False

        # Test error handling
        with patch("pathlib.Path.resolve") as mock_resolve:
            mock_resolve.side_effect = Exception("Test error")
            assert is_safe_path("error.txt") is False

    finally:
        # Cleanup not needed as tmp_path is automatically cleaned up
        pass
