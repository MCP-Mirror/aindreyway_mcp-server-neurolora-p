"""Tests for custom exceptions."""

import pytest

from mcp_server_neurolorap.exceptions import CollectionError, TerminalError


def test_collection_error() -> None:
    """Test CollectionError exception."""
    with pytest.raises(CollectionError) as exc_info:
        raise CollectionError("Test collection error")
    assert str(exc_info.value) == "Test collection error"


def test_terminal_error() -> None:
    """Test TerminalError exception."""
    with pytest.raises(TerminalError) as exc_info:
        raise TerminalError("Test terminal error")
    assert str(exc_info.value) == "Test terminal error"
