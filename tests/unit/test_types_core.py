"""Tests for core type definitions."""

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from mcpneurolora.types import (
    CallToolHandler,
    CommandType,
    Context,
    FastMCPType,
    ListToolsHandler,
    RouterResponse,
    ServerProtocol,
    TextContent,
    Tool,
    ToolFunction,
)


def test_command_type_values() -> None:
    """Test CommandType enum values."""
    # Test all enum values exist
    assert hasattr(CommandType, "COLLECT")
    assert hasattr(CommandType, "IMPROVE")
    assert hasattr(CommandType, "REQUEST")
    assert hasattr(CommandType, "HELP")
    assert hasattr(CommandType, "UNKNOWN")

    # Test all values are unique
    all_values = set(CommandType)
    assert len(all_values) == 5
    assert all(isinstance(v.value, int) for v in all_values)


def test_router_response_validation() -> None:
    """Test RouterResponse model validation."""
    # Test valid response
    response = RouterResponse(
        command_type=CommandType.COLLECT,
        confidence=0.8,
        args={"path": "src"},
        reason="Matched collect command",
        command="collect src",
    )
    assert response.command_type == CommandType.COLLECT
    assert response.confidence == 0.8
    assert response.args == {"path": "src"}
    assert response.reason == "Matched collect command"
    assert response.command == "collect src"

    # Test confidence bounds
    with pytest.raises(ValueError):
        RouterResponse(
            command_type=CommandType.COLLECT,
            confidence=1.5,  # Invalid: > 1.0
            args={},
            reason="test",
        )

    with pytest.raises(ValueError):
        RouterResponse(
            command_type=CommandType.COLLECT,
            confidence=-0.5,  # Invalid: < 0.0
            args={},
            reason="test",
        )

    # Test optional fields
    response = RouterResponse(
        command_type=CommandType.COLLECT,
        confidence=0.5,
        args={},
        reason="test",
    )
    assert response.args == {}
    assert response.command is None


def test_context_protocol() -> None:
    """Test Context protocol implementation."""
    # Create mock context
    mock_context = MagicMock(spec=Context)
    mock_context.info = MagicMock()
    mock_context.report_progress = AsyncMock()

    # Test info method
    mock_context.info("test message")
    mock_context.info.assert_called_once_with("test message")

    # Test report_progress method
    async def test_progress() -> None:
        await mock_context.report_progress(0.5, 100.0)
        await mock_context.report_progress(0.75, None)

        # Verify all calls
        assert mock_context.report_progress.call_args_list == [
            call(0.5, 100.0),
            call(0.75, None),
        ]

    asyncio.run(test_progress())


def test_fastmcp_protocol() -> None:
    """Test FastMCP protocol implementation."""

    class TestFastMCP(FastMCPType):
        """Test implementation of FastMCP protocol."""

        def __init__(self) -> None:
            """Initialize test FastMCP."""
            self.name = "test_mcp"
            self.tool_called = False
            self.tools: Dict[str, ToolFunction] = {}
            self.run = MagicMock()

        def tool(
            self,
            name: str | None = None,
            *,
            description: str | None = None,
        ) -> Any:
            """Tool decorator."""

            def decorator(func: Any) -> Any:
                self.tools[name or func.__name__] = func
                return func

            return decorator

        def prompt(
            self,
            name: str | None = None,
            *,
            description: str | None = None,
        ) -> Any:
            """Prompt decorator."""

            def decorator(func: Any) -> Any:
                return func

            return decorator

        async def __call__(self, *args: Any, **kwargs: Any) -> Any:
            """Make the class callable."""
            return None

    # Create test instance
    mcp = TestFastMCP()

    # Verify it implements FastMCP protocol
    assert isinstance(mcp, FastMCPType)

    # Test tool decorator
    @mcp.tool(name="test_tool", description="Test tool")
    async def test_tool() -> str:
        return "test result"

    assert "test_tool" in mcp.tools
    assert mcp.tools["test_tool"] == test_tool

    # Test attributes
    assert mcp.name == "test_mcp"
    assert mcp.tool_called is False
    assert isinstance(mcp.run, MagicMock)


def test_server_protocol() -> None:
    """Test Server protocol implementation."""

    class TestServer:
        """Test implementation of Server protocol."""

        def list_tools(self) -> Any:
            """List tools decorator."""

            def decorator(handler: ListToolsHandler) -> ListToolsHandler:
                async def wrapper() -> List[Tool]:
                    return await handler()

                return wrapper

            return decorator

        def call_tool(self) -> Any:
            """Call tool decorator."""

            def decorator(handler: CallToolHandler) -> CallToolHandler:
                async def wrapper(
                    name: str, args: Optional[Dict[str, Any]] = None
                ) -> List[TextContent]:
                    return await handler(name, args)

                return wrapper

            return decorator

        async def run(self, reader: Any, writer: Any, options: Any) -> None:
            """Run the server."""
            pass

    # Create test instance
    server = TestServer()

    # Verify it implements Server protocol
    assert isinstance(server, ServerProtocol)

    # Test list_tools decorator
    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return []

    # Test call_tool decorator
    @server.call_tool()
    async def call_tool(
        name: str, args: Optional[Dict[str, Any]] = None
    ) -> List[TextContent]:
        return []

    # Verify decorated functions are coroutines
    assert asyncio.iscoroutinefunction(list_tools)
    assert asyncio.iscoroutinefunction(call_tool)

    # Test run method exists
    assert hasattr(server, "run")
    assert asyncio.iscoroutinefunction(server.run)
