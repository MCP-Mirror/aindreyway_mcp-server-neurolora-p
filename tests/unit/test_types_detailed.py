"""Tests for types module."""

from typing import Any, List, Optional

import pytest
from pydantic import TypeAdapter, ValidationError

from mcpneurolora.types import CommandType, RouterResponse


def test_command_type_validation() -> None:
    """Test CommandType validation."""
    # Test valid command types
    for cmd in CommandType:
        RouterResponse(
            command_type=cmd,
            confidence=0.9,
            reason="test",
            args={},
        )


def test_router_response_validation() -> None:
    """Test RouterResponse validation."""
    # Valid response
    response = RouterResponse(
        command_type=CommandType.COLLECT,
        confidence=0.9,
        reason="test reason",
        args={"path": "src"},
        command="collect",
    )
    assert response.command_type == CommandType.COLLECT
    assert response.confidence == 0.9
    assert response.reason == "test reason"
    assert response.args == {"path": "src"}
    assert response.command == "collect"

    # Test validation of confidence range
    router_adapter = TypeAdapter(RouterResponse)
    with pytest.raises(ValidationError):
        router_adapter.validate_python(
            {
                "command_type": "collect",
                "confidence": 1.1,  # Should be between 0 and 1
                "reason": "test",
                "args": {},
            }
        )

    # Default args
    response = RouterResponse(
        command_type=CommandType.COLLECT,
        confidence=0.9,
        reason="test",
        args={},
    )
    assert response.args == {}
    assert response.command is None


class MockContext:
    """Mock implementation of Context protocol."""

    def __init__(self) -> None:
        """Initialize mock context."""
        self.info_messages: List[str] = []
        self.progress_values: List[float] = []
        self.progress_totals: List[Optional[float]] = []

    def info(self, message: str, **extra: Any) -> None:
        """Log an informational message."""
        self.info_messages.append(message)

    async def report_progress(
        self, progress: float, total: Optional[float] = None
    ) -> None:
        """Report progress."""
        self.progress_values.append(progress)
        self.progress_totals.append(total)


def test_context_protocol_implementation() -> None:
    """Test that MockContext implements Context protocol."""
    context = MockContext()
    # Check if MockContext implements Context protocol interface
    assert hasattr(context, "info")
    assert hasattr(context, "report_progress")


@pytest.mark.asyncio
async def test_context_methods() -> None:
    """Test Context protocol methods."""
    context = MockContext()

    # Test info method
    context.info("test message")
    assert context.info_messages == ["test message"]

    # Test report_progress method
    await context.report_progress(0.5)
    await context.report_progress(0.75, 100.0)

    assert context.progress_values == [0.5, 0.75]
    assert context.progress_totals == [None, 100.0]
