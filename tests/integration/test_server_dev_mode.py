"""Unit tests for terminal server functionality."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcpneurolora.server import run_terminal_server


@pytest.fixture
def mock_terminal_fixture() -> Generator[MagicMock, None, None]:
    """Mock terminal fixture."""
    with patch("mcpneurolora.server.JsonRpcTerminal") as mock_class:
        mock_instance = MagicMock()
        mock_instance.parse_request = MagicMock()
        mock_instance.handle_command = AsyncMock()
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_logger() -> Generator[MagicMock, None, None]:
    """Mock logger fixture."""
    with patch("mcpneurolora.terminal_server.logger") as mock_logger:
        yield mock_logger


@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_terminal_server_commands(
    mock_terminal_fixture: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Test terminal server command handling."""
    # Setup mock terminal responses
    mock_terminal_fixture.parse_request.side_effect = [
        {
            "jsonrpc": "2.0",
            "method": "help",
            "id": 1,
        },
        {
            "jsonrpc": "2.0",
            "method": "exit",
            "id": 2,
        },
    ]
    mock_terminal_fixture.handle_command.side_effect = [
        {
            "jsonrpc": "2.0",
            "result": "Help message",
            "id": 1,
        },
        {
            "jsonrpc": "2.0",
            "result": "Goodbye!",
            "id": 2,
        },
    ]

    # Mock input function
    with patch("builtins.input", side_effect=["help", "exit"]):
        await run_terminal_server()

        # Verify output
        mock_logger.info.assert_any_call("Help message")
        mock_logger.info.assert_any_call("Available Commands:")
        mock_logger.info.assert_any_call("Goodbye!")


@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_terminal_server_error_handling(
    mock_terminal_fixture: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Test error handling in terminal server."""
    # Test invalid command format
    mock_terminal_fixture.parse_request.side_effect = [
        None,  # Return None to trigger warning
        {"jsonrpc": "2.0", "method": "exit", "id": 1},
    ]
    mock_terminal_fixture.handle_command.side_effect = [
        {"jsonrpc": "2.0", "result": "Goodbye!", "id": 1},
    ]

    with patch("builtins.input", side_effect=["invalid", "exit"]):
        await run_terminal_server()
        # Check for error and warning about invalid command format
        mock_logger.error.assert_any_call("Invalid command format")
        mock_logger.warning.assert_any_call("Invalid command format")

    # Test JSON decode error
    mock_terminal_fixture.parse_request.reset_mock()
    mock_terminal_fixture.handle_command.reset_mock()
    mock_logger.reset_mock()

    mock_terminal_fixture.parse_request.side_effect = [
        {"jsonrpc": "2.0", "method": "invalid", "id": 1},
        {"jsonrpc": "2.0", "method": "exit", "id": 2},
    ]
    mock_terminal_fixture.handle_command.side_effect = [
        ValueError("Invalid command"),
        {"jsonrpc": "2.0", "result": "Goodbye!", "id": 2},
    ]

    with patch("builtins.input", side_effect=["invalid", "exit"]):
        await run_terminal_server()
        # Check for error message
        assert any(
            call.args[0] == "Value error: Invalid command"
            for call in mock_logger.error.mock_calls
        )


@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_terminal_server_empty_input(
    mock_terminal_fixture: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Test empty input handling in terminal server."""
    mock_terminal_fixture.parse_request.side_effect = [
        {"jsonrpc": "2.0", "method": "exit", "id": 1},
    ]
    mock_terminal_fixture.handle_command.side_effect = [
        {"jsonrpc": "2.0", "result": "Goodbye!", "id": 1},
    ]

    with patch("builtins.input", side_effect=["", "exit"]):
        await run_terminal_server()
        # Verify empty input messages
        mock_logger.info.assert_any_call("Empty input received")
        mock_logger.warning.assert_any_call("Empty input")
        mock_logger.info.assert_any_call("Exiting terminal server")


@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_terminal_server_interrupts(
    mock_terminal_fixture: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Test interrupt handling in terminal server."""
    # Test KeyboardInterrupt
    with patch("builtins.input", side_effect=KeyboardInterrupt):
        await run_terminal_server()
        mock_logger.info.assert_any_call("Keyboard interrupt received")
        mock_logger.info.assert_any_call("Exiting terminal server")

    # Reset mock
    mock_logger.reset_mock()

    # Test EOFError
    with patch("builtins.input", side_effect=EOFError):
        await run_terminal_server()
        assert any(
            call.args[0] == "Exiting terminal server"
            for call in mock_logger.info.mock_calls
        )
