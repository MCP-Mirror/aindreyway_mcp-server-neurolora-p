"""Unit test fixtures and configuration."""

from typing import Any, Dict, List

import pytest

from mcpneurolora.tools.executor import ToolExecutor


@pytest.fixture
def tool_executor() -> ToolExecutor:
    """Create a tool executor instance for unit tests."""
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
            "description": "Test tool for unit tests",
            "inputSchema": {
                "type": "object",
                "properties": {"test_param": {"type": "string"}},
            },
        }
    ]
