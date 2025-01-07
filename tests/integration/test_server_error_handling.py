"""Tests for server error handling."""

import logging
from collections.abc import Generator
from pathlib import Path
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcpneurolora.server import run_terminal_server

# Get logger for capturing messages
server_logger = logging.getLogger("mcpneurolora.server")
terminal_logger = logging.getLogger("mcpneurolora.terminal")


class LogCaptureHandler(logging.Handler):
    """Custom handler to capture log messages."""

    def __init__(self) -> None:
        """Initialize handler."""
        super().__init__()
        self.messages: List[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Store log message."""
        self.messages.append(record.getMessage())


@pytest.fixture
def log_capture() -> Generator[LogCaptureHandler, None, None]:
    """Fixture to capture log messages."""
    handler = LogCaptureHandler()
    server_logger.addHandler(handler)
    terminal_logger.addHandler(handler)
    server_logger.setLevel(logging.DEBUG)
    terminal_logger.setLevel(logging.DEBUG)
    yield handler
    server_logger.removeHandler(handler)
    terminal_logger.removeHandler(handler)


class MockTerminal:
    """Mock terminal for testing."""

    def __init__(self) -> None:
        """Initialize mock terminal."""
        self.parse_request_calls = 0
        self.handle_command_calls = 0

    def parse_request(self, line: str) -> dict[str, Any] | None:
        """Mock parse_request method."""
        self.parse_request_calls += 1
        if line == "unknown_command":
            return {
                "jsonrpc": "2.0",
                "method": "unknown_command",
                "params": [],
                "id": 1,
            }
        elif line == "exit":
            return {
                "jsonrpc": "2.0",
                "method": "exit",
                "params": [],
                "id": 2,
            }
        return None

    async def handle_command(self, request: dict[str, Any]) -> dict[str, Any]:
        """Mock handle_command method."""
        self.handle_command_calls += 1
        if request["method"] == "unknown_command":
            return {
                "error": {"message": "Method 'unknown_command' not found"},
                "id": request["id"],
            }
        elif request["method"] == "exit":
            return {"result": "Goodbye!", "id": request["id"]}
        return {"error": {"message": "Invalid request"}, "id": request["id"]}


class ToolMock(AsyncMock):
    """Custom AsyncMock that matches the expected tool callable type."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._side_effect: Exception | None = None

    def set_side_effect(self, effect: Exception | None) -> None:
        """Set side effect for the mock."""
        self._side_effect = effect

    async def __call__(self, *args: Any, **kwargs: Any) -> str:
        """Mock tool call."""
        try:
            if self._side_effect:
                raise self._side_effect
            return "Success"
        except Exception:
            if kwargs.get("tool_name") == "project_structure_reporter":
                return "Error generating report"
            return "No files found to process or error occurred"


@pytest.fixture
def mock_fastmcp() -> Generator[MagicMock, None, None]:
    """Mock FastMCP server."""
    with patch("mcpneurolora.server.Server") as mock:
        mock_server = MagicMock()
        mock_server.name = "neurolora"
        mock_server.tools = {
            "project_structure_reporter": ToolMock(),
            "code_collector": ToolMock(),
        }
        mock_server.tool_called = False
        mock.return_value = mock_server
        yield mock_server


@pytest.mark.asyncio
async def test_project_structure_reporter_error_handling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_fastmcp: MagicMock,
) -> None:
    """Test error handling in project_structure_reporter tool."""
    monkeypatch.setenv("MCP_PROJECT_ROOT", str(tmp_path))

    # Test with invalid ignore patterns
    tool = mock_fastmcp.tools["project_structure_reporter"]
    tool.set_side_effect(ValueError("Invalid pattern"))
    result = await tool(
        tool_name="project_structure_reporter",
        output_filename="test.md",
        ignore_patterns=["["],
    )
    assert "Error generating report" in result

    # Test with file system error
    tool = mock_fastmcp.tools["project_structure_reporter"]
    tool.set_side_effect(OSError("Permission denied"))
    result = await tool(tool_name="project_structure_reporter")
    assert "Error generating report" in result

    # Test with analysis error
    tool = mock_fastmcp.tools["project_structure_reporter"]
    tool.set_side_effect(ValueError("Analysis failed"))
    result = await tool(tool_name="project_structure_reporter")
    assert "Error generating report" in result

    # Test with report generation error
    tool = mock_fastmcp.tools["project_structure_reporter"]
    tool.set_side_effect(ValueError("Report generation failed"))
    result = await tool(tool_name="project_structure_reporter")
    assert "Error generating report" in result


@pytest.mark.asyncio
async def test_code_collector_error_handling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_fastmcp: MagicMock,
) -> None:
    """Test error handling in code_collector tool."""
    monkeypatch.setenv("MCP_PROJECT_ROOT", str(tmp_path))

    # Test with invalid input path
    tool = mock_fastmcp.tools["code_collector"]
    tool.set_side_effect(ValueError("Invalid path"))
    result = await tool(
        tool_name="code_collector",
        input_path="/nonexistent/path",
        title="Test",
    )
    assert "No files found to process or error occurred" in result

    # Test with file system error
    tool = mock_fastmcp.tools["code_collector"]
    tool.set_side_effect(OSError("Permission denied"))
    result = await tool(tool_name="code_collector")
    assert "No files found to process or error occurred" in result

    # Test with collection error
    tool = mock_fastmcp.tools["code_collector"]
    tool.set_side_effect(ValueError("Collection failed"))
    result = await tool(tool_name="code_collector")
    assert "No files found to process or error occurred" in result

    # Test with unexpected error
    tool = mock_fastmcp.tools["code_collector"]
    tool.set_side_effect(Exception("Unexpected error"))
    result = await tool(tool_name="code_collector")
    assert "No files found to process or error occurred" in result


@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_terminal_server_value_error(
    monkeypatch: pytest.MonkeyPatch,
    log_capture: LogCaptureHandler,
) -> None:
    """Test error handling in terminal server."""
    monkeypatch.setenv("MCP_PROJECT_ROOT", "/tmp")

    # Mock input to raise ValueError
    input_mock = MagicMock(side_effect=[ValueError("Invalid input"), "exit"])
    monkeypatch.setattr("builtins.input", input_mock)

    # Run terminal server
    await run_terminal_server()

    # Verify error handling
    assert any(
        "ERROR Value error: Invalid input" in msg for msg in log_capture.messages
    )
    assert any(
        "ERROR Value error in terminal server: Invalid input" in msg
        for msg in log_capture.messages
    )
    assert any("INFO Terminal server stopped" in msg for msg in log_capture.messages)


@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_terminal_server_type_error(
    monkeypatch: pytest.MonkeyPatch,
    log_capture: LogCaptureHandler,
) -> None:
    """Test type error handling in terminal server."""
    monkeypatch.setenv("MCP_PROJECT_ROOT", "/tmp")

    # Mock input to raise TypeError
    input_mock = MagicMock(side_effect=[TypeError("Invalid type"), "exit"])
    monkeypatch.setattr("builtins.input", input_mock)

    # Run terminal server
    await run_terminal_server()

    # Verify error handling
    assert any("ERROR Type error: Invalid type" in msg for msg in log_capture.messages)
    assert any(
        "ERROR Type error in terminal server: Invalid type" in msg
        for msg in log_capture.messages
    )
    assert any("INFO Terminal server stopped" in msg for msg in log_capture.messages)


@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_terminal_server_empty_input(
    monkeypatch: pytest.MonkeyPatch,
    log_capture: LogCaptureHandler,
) -> None:
    """Test empty input handling in terminal server."""
    monkeypatch.setenv("MCP_PROJECT_ROOT", "/tmp")

    # Mock input to return empty string then exit
    input_mock = MagicMock(side_effect=["", "exit"])
    monkeypatch.setattr("builtins.input", input_mock)

    # Run terminal server
    await run_terminal_server()

    # Verify error handling
    assert any("INFO Empty input received" in msg for msg in log_capture.messages)
    assert any("WARNING Empty input" in msg for msg in log_capture.messages)
    assert any("INFO Terminal server stopped" in msg for msg in log_capture.messages)


@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_terminal_server_invalid_command(
    monkeypatch: pytest.MonkeyPatch,
    log_capture: LogCaptureHandler,
) -> None:
    """Test invalid command format handling in terminal server."""
    monkeypatch.setenv("MCP_PROJECT_ROOT", "/tmp")

    # Mock terminal to return None for parse_request
    terminal = MockTerminal()
    with patch(
        "mcpneurolora.server.JsonRpcTerminal",
        return_value=terminal,
    ):
        # Mock input with invalid command then exit
        input_mock = MagicMock(side_effect=["invalid command", "exit"])
        monkeypatch.setattr("builtins.input", input_mock)

        # Run terminal server
        await run_terminal_server()

        # Verify error handling
        assert any(
            "ERROR Method 'invalid' not found" in msg for msg in log_capture.messages
        )
        assert any(
            "INFO Terminal server stopped" in msg for msg in log_capture.messages
        )


@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_terminal_server_unknown_command(
    monkeypatch: pytest.MonkeyPatch,
    log_capture: LogCaptureHandler,
) -> None:
    """Test unknown command handling in terminal server."""
    monkeypatch.setenv("MCP_PROJECT_ROOT", "/tmp")

    # Mock JsonRpcTerminal class
    with patch("mcpneurolora.server.JsonRpcTerminal") as mock_terminal_class:
        terminal_instance = MockTerminal()
        mock_terminal_class.return_value = terminal_instance

        # Mock input to immediately exit
        input_mock = MagicMock(side_effect=["unknown_command", "exit"])
        monkeypatch.setattr("builtins.input", input_mock)

        # Run terminal server
        await run_terminal_server()

        # Verify error handling
        assert any(
            "ERROR Method 'unknown_command' not found" in msg
            for msg in log_capture.messages
        )
        assert any(
            "INFO Terminal server stopped" in msg for msg in log_capture.messages
        )


@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_terminal_server_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch,
    log_capture: LogCaptureHandler,
) -> None:
    """Test keyboard interrupt handling in terminal server."""
    monkeypatch.setenv("MCP_PROJECT_ROOT", "/tmp")

    # Mock input function to raise KeyboardInterrupt
    input_mock = MagicMock(side_effect=KeyboardInterrupt)
    monkeypatch.setattr("builtins.input", input_mock)

    # Run terminal server
    await run_terminal_server()

    # Verify error handling
    assert any(
        "INFO Keyboard interrupt received" in msg for msg in log_capture.messages
    )
    assert any("INFO Terminal server stopped" in msg for msg in log_capture.messages)
