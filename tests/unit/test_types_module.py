"""Tests for type definitions."""

import asyncio
from typing import Any, Dict, Optional, Sequence

from mcp.types import (
    EmbeddedResource,
    ImageContent,
    TextContent,
    TextResourceContents,
)
from pydantic import AnyUrl, BaseModel, HttpUrl

from mcpneurolora.types import (
    CallToolArgs,
    CallToolResult,
    CommandType,
    RouterResponse,
)


def test_command_type() -> None:
    """Test CommandType enum."""
    # Test all enum values
    assert CommandType.COLLECT.name == "COLLECT"
    assert CommandType.IMPROVE.name == "IMPROVE"
    assert CommandType.REQUEST.name == "REQUEST"
    assert CommandType.HELP.name == "HELP"
    assert CommandType.UNKNOWN.name == "UNKNOWN"

    # Test enum values are unique and are integers
    values = [cmd.value for cmd in CommandType]
    assert len(values) == len(set(values))
    assert all(isinstance(v, int) for v in values)

    # Test valid command type in RouterResponse
    response = RouterResponse(
        command_type=CommandType.COLLECT,
        confidence=0.9,
        args={},
        reason="Test",
    )
    assert response.command_type == CommandType.COLLECT


def test_router_response() -> None:
    """Test RouterResponse model."""
    response = RouterResponse(
        command_type=CommandType.COLLECT,
        confidence=0.9,
        args={"path": "test"},
        reason="Test reason",
        command="collect",
    )
    assert response.command_type == CommandType.COLLECT
    assert response.confidence == 0.9
    assert response.args == {"path": "test"}
    assert response.reason == "Test reason"
    assert response.command == "collect"

    # Test optional command
    response_no_cmd = RouterResponse(
        command_type=CommandType.COLLECT,
        confidence=0.9,
        args={},
        reason="Test reason",
    )
    assert response_no_cmd.command is None


def test_context_protocol() -> None:
    """Test Context protocol implementation."""

    class TestContext(BaseModel):
        """Test implementation of Context protocol."""

        client_id: str = "test_client"
        request_id: str = "test_request"
        session: Dict[str, Any] = {}

        def info(self, message: str) -> None:
            """Log an informational message."""

        def debug(self, message: str) -> None:
            """Log a debug message."""

        def warning(self, message: str) -> None:
            """Log a warning message."""

        def error(self, message: str) -> None:
            """Log an error message."""

        async def report_progress(
            self,
            progress: float,
            total: Optional[float] = None,
        ) -> None:
            """Report progress."""

        async def read_resource(self, uri: str) -> str:
            """Read a resource."""
            return ""

    context = TestContext()

    # Test protocol methods exist
    assert hasattr(context, "info")
    assert hasattr(context, "debug")
    assert hasattr(context, "warning")
    assert hasattr(context, "error")
    assert hasattr(context, "report_progress")
    assert hasattr(context, "read_resource")
    assert asyncio.iscoroutinefunction(context.report_progress)
    assert asyncio.iscoroutinefunction(context.read_resource)

    # Test properties
    assert hasattr(context, "client_id")
    assert hasattr(context, "request_id")
    assert hasattr(context, "session")


def test_call_tool_types() -> None:
    """Test CallToolArgs and CallToolResult types."""
    # Test CallToolArgs
    args: CallToolArgs = {"param": "value", "flag": True, "count": 42}
    assert isinstance(args, dict)
    assert all(isinstance(k, str) for k in args.keys())

    # Test CallToolResult
    text_content = TextContent(type="text", text="test")
    image_content = ImageContent(
        type="image",
        data="base64data",
        mimeType="image/png",
    )
    uri: AnyUrl = HttpUrl("https://example.com")
    resource = EmbeddedResource(
        type="resource",
        resource=TextResourceContents(
            text="test content",
            uri=uri,
        ),
    )

    result: CallToolResult = [text_content, image_content, resource]
    assert isinstance(result, Sequence)
    assert all(
        isinstance(content, (TextContent, ImageContent, EmbeddedResource))
        for content in result
    )
