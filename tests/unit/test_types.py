"""Tests for type definitions."""

import asyncio
import base64
from typing import Any, List, Optional, Sequence

import pytest
from mcp.types import (
    BlobResourceContents,
    EmbeddedResource,
    ImageContent,
    TextContent,
    TextResourceContents,
)
from pydantic import BaseModel, HttpUrl

from mcpneurolora.types import (
    CallToolArgs,
    CallToolResult,
    ClinesConfig,
    CommandType,
    RouterResponse,
    ServerConfig,
    ServerEnvConfig,
    VsCodeSettings,
)


class MockContext(BaseModel):
    """Mock implementation of Context."""

    info_calls: List[tuple[str, dict[str, Any]]] = []
    progress_calls: List[tuple[float, Optional[float]]] = []

    def info(self, message: str, **extra: Any) -> None:
        """Log an informational message."""
        self.info_calls.append((message, extra))

    async def report_progress(
        self,
        progress: float,
        total: Optional[float] = None,
    ) -> None:
        """Report progress."""
        self.progress_calls.append((progress, total))


def test_context_protocol() -> None:
    """Test Context protocol implementation."""
    context = MockContext()

    # Test info method
    context.info("test message", field="test")
    assert len(context.info_calls) == 1
    assert context.info_calls[0][0] == "test message"
    assert context.info_calls[0][1]["field"] == "test"

    # Test report_progress method
    async def test_progress() -> None:
        await context.report_progress(0.5, 100.0)
        assert (0.5, 100.0) in context.progress_calls

    asyncio.run(test_progress())


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

    # Test invalid command type
    with pytest.raises(ValueError):
        # Use Any to bypass type checking since we're testing runtime behavior
        invalid_value: Any = "invalid"
        CommandType(invalid_value)


def test_router_response() -> None:
    """Test RouterResponse dataclass."""
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


def test_call_tool_args() -> None:
    """Test CallToolArgs type."""
    args: CallToolArgs = {"param": "value", "flag": True, "count": 42}
    assert isinstance(args, dict)
    assert all(isinstance(k, str) for k in args.keys())


def test_call_tool_result() -> None:
    """Test CallToolResult type."""
    # Convert binary data to base64 string for ImageContent
    test_data = base64.b64encode(b"test").decode("utf-8")

    text_content = TextContent(type="text", text="test")
    image_content = ImageContent(
        type="image",
        data=test_data,
        mimeType="image/png",
    )

    # Create text resource
    text_resource = TextResourceContents(
        text="test content",
        uri=HttpUrl("https://example.com/text"),
    )
    embedded_text = EmbeddedResource(
        type="resource",
        resource=text_resource,
    )

    # Create blob resource
    blob_resource = BlobResourceContents(
        blob=test_data,
        uri=HttpUrl("https://example.com/blob"),
    )
    embedded_blob = EmbeddedResource(
        type="resource",
        resource=blob_resource,
    )

    result: CallToolResult = [text_content, image_content, embedded_text, embedded_blob]
    assert isinstance(result, Sequence)
    assert all(
        isinstance(
            content,
            (TextContent, ImageContent, EmbeddedResource),
        )
        for content in result
    )


def test_clines_config() -> None:
    """Test ClinesConfig type."""
    config: ClinesConfig = {
        "mcpServers": {
            "test-server": {
                "command": "test",
                "args": ["arg1", "arg2"],
                "env": {"PYTHONUNBUFFERED": "1"},
                "disabled": False,
                "alwaysAllow": [],
            }
        }
    }
    assert isinstance(config, dict)
    assert "mcpServers" in config
    assert isinstance(config["mcpServers"], dict)


def test_server_config() -> None:
    """Test ServerConfig type."""
    config: ServerConfig = {
        "command": "test",
        "args": ["arg1", "arg2"],
        "env": {"PYTHONUNBUFFERED": "1"},
        "disabled": False,
        "alwaysAllow": [],
    }
    assert isinstance(config, dict)
    assert "command" in config
    assert "args" in config
    assert "env" in config
    assert "disabled" in config
    assert "alwaysAllow" in config


def test_server_env_config() -> None:
    """Test ServerEnvConfig type."""
    config: ServerEnvConfig = {
        "AI_MODEL": "gpt-4",
        "OPENAI_API_KEY": "test-key",
        "PYTHONUNBUFFERED": "1",
    }
    assert isinstance(config, dict)
    assert all(isinstance(k, str) for k in config.keys())
    assert all(isinstance(v, str) for v in config.values())


def test_vscode_settings() -> None:
    """Test VsCodeSettings type."""
    settings: VsCodeSettings = {
        "mcpServers": {
            "test-server": {
                "command": "test",
                "args": ["arg1"],
                "env": {"PYTHONUNBUFFERED": "1"},
                "disabled": False,
                "alwaysAllow": [],
            }
        }
    }
    assert isinstance(settings, dict)
    assert "mcpServers" in settings
    assert isinstance(settings["mcpServers"], dict)
