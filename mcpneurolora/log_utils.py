"""Unified logging configuration for the NeuroLoRA project.

This module provides a centralized logging configuration to ensure consistent
logging across all components of the project.
"""

import logging
import sys
from enum import Enum
from typing import Any, Optional

from colorama import Back, Fore, Style, init

# Initialize colorama
init()


class LogCategory(Enum):
    """Log categories for better organization and filtering."""

    CONFIG = "CONFIG"  # Configuration and environment setup
    COMMAND = "COMMAND"  # Command execution and results
    STORAGE = "STORAGE"  # Storage operations
    TOOLS = "TOOLS"  # Tool execution
    SERVER = "SERVER"  # Server operations
    TERMINAL = "TERMINAL"  # Terminal interface


class ColorFormatter(logging.Formatter):
    """Custom formatter adding colors and category prefixes to log messages."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the formatter with colorama colors."""
        super().__init__(*args, **kwargs)

        # Level colors using colorama
        self.COLORS = {
            "DEBUG": Fore.CYAN,
            "INFO": Style.RESET_ALL,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "CRITICAL": Back.RED + Fore.WHITE,
            "RESET": Style.RESET_ALL,
        }

        # Category-specific colors using colorama
        self.CATEGORY_COLORS = {
            LogCategory.CONFIG.value: Fore.GREEN,
            LogCategory.COMMAND.value: Fore.BLUE,
            LogCategory.STORAGE.value: Fore.MAGENTA,
            LogCategory.TOOLS.value: Fore.CYAN,
            LogCategory.SERVER.value: Fore.YELLOW,
            LogCategory.TERMINAL.value: Fore.WHITE,
        }

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors and category.

        Args:
            record: The log record to format

        Returns:
            str: The formatted log message
        """
        # Get level color
        level_color = self.COLORS.get(record.levelname, self.COLORS["RESET"])

        # Extract category and get its color
        category = getattr(record, "category", None)
        category_color = (
            self.CATEGORY_COLORS.get(category, self.COLORS["RESET"])
            if category
            else self.COLORS["RESET"]
        )

        # Format category prefix
        category_str = f"[{category}] " if category else ""

        # Format the message with colors
        # First reset any existing colors
        msg = self.COLORS["RESET"] + str(record.msg)

        # Format the final message with all components
        record.msg = (
            f"{level_color}{record.levelname}{self.COLORS['RESET']} "
            f"{category_color}{category_str}{self.COLORS['RESET']}"
            f"{msg}"
        )
        return super().format(record)


# Configure root logger to prevent duplicate logs
root_logger = logging.getLogger()
root_logger.handlers = []  # Remove any existing handlers
root_logger.addHandler(logging.NullHandler())  # Add null handler


def get_logger(name: str, category: Optional[LogCategory] = None) -> logging.Logger:
    """Get a logger with the specified name and category.

    Args:
        name: Name for the logger (usually __name__)
        category: Optional category for grouping logs

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)

    # Remove any existing handlers
    logger.handlers = []

    # Configure logger with category-specific levels
    if category:
        if category == LogCategory.CONFIG:
            logger.setLevel(logging.WARNING)  # Show only important config messages
        elif category == LogCategory.STORAGE:
            logger.setLevel(logging.INFO)  # Show main storage operations
        elif category == LogCategory.TOOLS:
            logger.setLevel(logging.INFO)  # Show main tool operations
        else:
            logger.setLevel(logging.INFO)  # Default level
    else:
        logger.setLevel(logging.INFO)

    logger.propagate = False  # Prevent propagation to root logger

    # Create console handler with category-specific formatting
    handler = logging.StreamHandler(sys.stderr)

    # Use compact format for TOOLS category
    if category == LogCategory.TOOLS:
        handler.setFormatter(
            ColorFormatter(
                fmt="%(message)s",  # No timestamp for cleaner tool output
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    else:
        handler.setFormatter(
            ColorFormatter(
                fmt="%(asctime)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    logger.addHandler(handler)

    # Add category as a filter
    if category:

        def add_category(record: logging.LogRecord) -> bool:
            record.category = category.value
            # Filter out debug messages for storage operations
            if category == LogCategory.STORAGE and record.levelno < logging.INFO:
                return False
            # Filter out repetitive config messages
            if category == LogCategory.CONFIG and record.levelno < logging.WARNING:
                return False
            return True

        logger.addFilter(add_category)

    return logger


def configure_mcp_logging(level: int = logging.WARNING) -> None:
    """Configure logging for all MCP modules.

    Args:
        level: Logging level to set for MCP modules (default: WARNING)
    """
    mcp_modules = [
        "mcp",
        "mcp.server",
        "mcp.server.fastmcp",
        "mcp.server.transport",
        "mcp.server.request",
    ]

    for module in mcp_modules:
        logging.getLogger(module).setLevel(level)


def configure_test_logging() -> None:
    """Configure logging for test environment.

    This function sets stricter logging levels during test execution to reduce noise:
    - Sets WARNING level for most categories
    - Disables propagation to root logger
    - Removes timestamp from log format
    - Filters out non-essential messages
    """
    # Set strict levels for all categories
    for category in LogCategory:
        logger = get_logger(f"test.{category.value.lower()}", category)
        logger.setLevel(logging.WARNING)
        logger.propagate = False

        # Remove existing handlers
        logger.handlers = []

        # Add test-specific handler
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            ColorFormatter(
                fmt="%(message)s",  # No timestamp in tests
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)

    # Configure MCP logging
    configure_mcp_logging(logging.ERROR)  # More strict for MCP modules

    # Disable root logger
    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.addHandler(logging.NullHandler())


# Example usage:
# logger = get_logger(__name__, LogCategory.CONFIG)
# logger.info("Loading configuration...")  # [CONFIG] Loading configuration...
# logger.error("Failed to load config")    # [CONFIG] Failed to load config
