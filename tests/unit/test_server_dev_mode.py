"""Unit tests for developer mode functionality."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_neurolorap.server import run_dev_mode


@pytest.fixture
def mock_terminal_fixture() -> Generator[MagicMock, None, None]:
    """Mock terminal fixture."""
    with patch("mcp_server_neurolorap.server.JsonRpcTerminal") as mock_class:
        mock_instance = MagicMock()
        mock_instance.parse_request = MagicMock()
        mock_instance.handle_command = AsyncMock()
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.mark.asyncio
async def test_dev_mode_commands(mock_terminal_fixture: MagicMock) -> None:
    """Test developer mode command handling."""
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

    # Mock input/print functions
    with patch("builtins.input", side_effect=["help", "exit"]), patch(
        "builtins.print"
    ) as mock_print:
        await run_dev_mode()

        # Verify output
        mock_print.assert_any_call("Help message")
        mock_print.assert_any_call("Goodbye!")


@pytest.mark.asyncio
async def test_dev_mode_error_handling(
    mock_terminal_fixture: MagicMock,
) -> None:
    """Test error handling in developer mode."""
    error_cases: list[tuple[type[Exception], str]] = [
        (ValueError, "Value error: Invalid command"),
        (TypeError, "Type error: Type error"),
        (Exception, "Unexpected error: Unexpected error"),
    ]

    for error, expected_msg in error_cases:
        # Reset mocks for each test case
        mock_terminal_fixture.parse_request.reset_mock()
        mock_terminal_fixture.handle_command.reset_mock()

        # Set up the error case
        mock_terminal_fixture.parse_request.side_effect = [
            error("Invalid command"),
            {"jsonrpc": "2.0", "method": "exit", "id": 1},
        ]
        mock_terminal_fixture.handle_command.side_effect = [
            {"jsonrpc": "2.0", "result": "Goodbye!", "id": 1}
        ]

        with patch("builtins.input", side_effect=["invalid", "exit"]), patch(
            "builtins.print"
        ) as mock_print:
            await run_dev_mode()
            expected_error = expected_msg.split(":")[0]
            mock_print.assert_any_call(f"{expected_error}: Invalid command")


@pytest.mark.asyncio
async def test_dev_mode_empty_input(mock_terminal_fixture: MagicMock) -> None:
    """Test empty input handling in developer mode."""
    mock_terminal_fixture.parse_request.side_effect = [
        {"jsonrpc": "2.0", "method": "exit", "id": 1},
    ]
    mock_terminal_fixture.handle_command.side_effect = [
        {"jsonrpc": "2.0", "result": "Goodbye!", "id": 1},
    ]

    with patch("builtins.input", side_effect=["", "exit"]), patch(
        "builtins.print"
    ) as mock_print:
        await run_dev_mode()
        # Verify that no error was printed for empty input
        assert mock_print.call_count == 5


@pytest.mark.asyncio
async def test_dev_mode_interrupts(mock_terminal_fixture: MagicMock) -> None:
    """Test interrupt handling in developer mode."""
    # Test KeyboardInterrupt
    with patch("builtins.input", side_effect=KeyboardInterrupt), patch(
        "builtins.print"
    ) as mock_print:
        await run_dev_mode()
        mock_print.assert_called_with("\nExiting developer mode")

    # Test EOFError
    with patch("builtins.input", side_effect=EOFError), patch(
        "builtins.print"
    ) as mock_print:
        await run_dev_mode()
        mock_print.assert_called_with("\nExiting developer mode")
