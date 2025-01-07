"""Integration test fixtures and configuration."""

from typing import Any, AsyncGenerator, Dict, List

import pytest
from mcp.server import Server

from mcpneurolora.server_handlers import (
    call_tool_fn,
    list_resource_templates_fn,
    list_resources_fn,
    list_tools_fn,
    read_resource_fn,
)
from mcpneurolora.server_utils import wrap_async_fn
from mcpneurolora.tools.executor import ToolExecutor


@pytest.fixture
async def test_server() -> AsyncGenerator[Server, None]:
    """Create a test server instance with mock configuration."""
    server = Server("test-server")

    # Register handlers
    server.list_tools()(wrap_async_fn(list_tools_fn))
    server.call_tool()(wrap_async_fn(call_tool_fn))
    server.list_resources()(wrap_async_fn(list_resources_fn))
    server.list_resource_templates()(wrap_async_fn(list_resource_templates_fn))
    server.read_resource()(wrap_async_fn(read_resource_fn))

    yield server


@pytest.fixture
def tool_executor() -> ToolExecutor:
    """Create a tool executor instance."""
    return ToolExecutor()


@pytest.fixture
def mock_api_response() -> Dict[str, Any]:
    """Mock response from external APIs."""
    return {"choices": [{"text": "test response"}]}


@pytest.fixture
def mock_tools() -> List[Dict[str, Any]]:
    """Mock list of available tools."""
    return [
        {
            "name": "test_tool",
            "description": "Test tool for integration tests",
            "inputSchema": {
                "type": "object",
                "properties": {"test_param": {"type": "string"}},
            },
        }
    ]
