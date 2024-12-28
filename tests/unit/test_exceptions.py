"""Tests for custom exceptions."""

from mcpneurolora.exceptions import CollectionError, TerminalError


def test_collection_error_message() -> None:
    """Test CollectionError exception message."""
    error_message = "Test collection error"
    error = CollectionError(error_message)
    assert str(error) == error_message


def test_terminal_error_message() -> None:
    """Test TerminalError exception message."""
    error_message = "Test terminal error"
    error = TerminalError(error_message)
    assert str(error) == error_message
