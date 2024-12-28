"""Custom exceptions for the MCP server."""


class CollectionError(Exception):
    """Raised when there is an error during code collection."""

    pass


class TerminalError(Exception):
    """Raised when there is an error in terminal operations."""

    pass
