"""Unit tests for main server functionality."""

import os
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, NonCallableMock, patch

import pytest

from mcpneurolora.server import get_project_root, run_mcp_server


class ToolMock(AsyncMock):
    """Custom AsyncMock that matches the expected tool callable type."""

    def __init__(
        self,
        spec: list[str] | object | type[object] | None = None,
        wraps: Any | None = None,
        name: str | None = None,
        spec_set: list[str] | object | type[object] | None = None,
        parent: NonCallableMock | None = None,
        _spec_state: Any | None = None,
        _new_name: str = "",
        _new_parent: NonCallableMock | None = None,
        _spec_as_instance: bool = False,
        _eat_self: bool | None = None,
        unsafe: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            spec=spec,
            wraps=wraps,
            name=name,
            spec_set=spec_set,
            parent=parent,
            _spec_state=_spec_state,
            _new_name=_new_name,
            _new_parent=_new_parent,
            _spec_as_instance=_spec_as_instance,
            _eat_self=_eat_self,
            unsafe=unsafe,
            **kwargs,
        )
        self._collector: AsyncMock | None = None

    def set_collector(self, collector: AsyncMock | None) -> None:
        """Set the collector instance for this tool."""
        self._collector = collector


class MockFastMCP:
    """Mock FastMCP server."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.tools = {"code_collector": ToolMock()}
        self.tool_called = False
        self.info = MagicMock()
        self.debug = MagicMock()
        self.error = MagicMock()
        self._tool_error: Exception | None = None

    def set_tool_error(self, error: Exception) -> None:
        """Set error to be raised during tool registration."""
        self._tool_error = error

    def tool(self, *args: Any, **kwargs: Any) -> Any:
        """Tool decorator."""
        if self._tool_error is not None:
            self.error(
                "Failed to initialize server: Test error", exc_info=True
            )
            raise self._tool_error

        def decorator(func: Any) -> Any:
            self.tool_called = True
            self.debug("Registering tool: code_collector")
            self.info("Starting MCP server: neurolora")
            return self.tools["code_collector"]

        return decorator

    def run(self) -> None | Any:
        """Run the server."""
        return MagicMock()


@pytest.fixture
def mock_fastmcp() -> Generator[MockFastMCP, None, None]:
    """Mock FastMCP server."""
    with patch("mcp_server_neurolora.server.FastMCP") as mock:
        mock_server = MockFastMCP("neurolora")
        mock.return_value = mock_server
        yield mock_server


@pytest.fixture
def mock_logger() -> Generator[MagicMock, None, None]:
    """Mock logger."""
    with patch("mcp_server_neurolora.server.logger") as mock_logger:
        yield mock_logger


def test_run_mcp_server(mock_fastmcp: MockFastMCP) -> None:
    """Test MCP server initialization and configuration."""
    server = run_mcp_server()
    assert server.name == "neurolora"
    assert server.tool_called
    assert "code_collector" in server.tools


def test_project_root_environment(mock_logger: MagicMock) -> None:
    """Test project root environment variable handling."""
    # Test with environment variable set
    test_path = "/test/path"
    with patch.dict(os.environ, {"MCP_PROJECT_ROOT": test_path}, clear=True):
        root = get_project_root()
        assert str(root) == test_path
        mock_logger.info.assert_not_called()

    # Test with environment variable not set
    with patch.dict(os.environ, {}, clear=True):
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/current/dir")
            root = get_project_root()
            assert str(root) == "/current/dir"
            mock_logger.info.assert_called_with(
                "Set MCP_PROJECT_ROOT to: %s", Path("/current/dir")
            )


@pytest.mark.asyncio
async def test_mcp_server_initialization(mock_fastmcp: MockFastMCP) -> None:
    """Test MCP server initialization process."""
    server = run_mcp_server()
    assert server.name == "neurolora"
    mock_fastmcp.info.assert_called_with("Starting MCP server: neurolora")


@pytest.mark.asyncio
async def test_mcp_server_tool_registration(mock_fastmcp: MockFastMCP) -> None:
    """Test MCP server tool registration process."""
    server = run_mcp_server()
    assert "code_collector" in server.tools
    mock_fastmcp.debug.assert_any_call("Registering tool: code_collector")


@pytest.mark.asyncio
async def test_mcp_server_error_handling(mock_fastmcp: MockFastMCP) -> None:
    """Test MCP server error handling."""
    # Test initialization error
    test_error = Exception("Test error")
    mock_fastmcp.set_tool_error(test_error)
    with pytest.raises(Exception) as exc_info:
        run_mcp_server()
    assert str(exc_info.value) == "Test error"
    mock_fastmcp.error.assert_called_with(
        "Failed to initialize server: Test error", exc_info=True
    )
