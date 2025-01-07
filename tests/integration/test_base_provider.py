"""Unit tests for the BaseProvider class."""

import asyncio
import logging
import os
from typing import Any, List
from unittest.mock import AsyncMock, patch

import pytest

from mcpneurolora.providers.base_provider import (
    BaseProvider,
    Message,
    ProviderConfig,
    get_env_int,
)
from mcpneurolora.utils.progress import ProgressTracker

# Disable logging for tests
logging.getLogger("mcpneurolora.providers.base_provider").setLevel(logging.CRITICAL)


@pytest.fixture
def provider_config() -> ProviderConfig:
    """Create test provider configuration."""
    return ProviderConfig(
        api_key="test_key",
        model="test_model",
        timeout_ms=1000,
        extra_params={"token_limit": 1000},
    )


class TestProvider(BaseProvider):
    """Test implementation of BaseProvider."""

    name = "test_provider"

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize test provider."""
        super().__init__(config)
        self.send_request_mock = AsyncMock(return_value="1. [ ] ISSUE HIGH\nTest")

    def count_tokens(self, content: str) -> int:
        """Test implementation of count_tokens."""
        return len(content) // 4

    async def analyze(self, content: str) -> str:
        """Test implementation of analyze."""
        messages = self._prepare_messages(content)
        return await self._make_request(messages)

    async def _send_request(self, messages: List[Message]) -> str:
        """Test implementation of _send_request."""
        result = await self.send_request_mock(messages)
        assert isinstance(result, str)
        return result


class TestProgressTracker(ProgressTracker):
    """Test implementation of ProgressTracker."""

    def __init__(self, updates: List[float]) -> None:
        """Initialize test progress tracker."""
        super().__init__(total_steps=100, prefix="[Test]", use_spinner=False)
        self.updates = updates

    async def update(self, step: int, message: str = "") -> None:
        """Record progress updates."""
        self.updates.append(float(step))


@pytest.fixture
def mock_provider(provider_config: ProviderConfig) -> TestProvider:
    """Create mock provider instance."""
    return TestProvider(provider_config)


def test_provider_config_validation() -> None:
    """Test provider configuration validation."""
    # Test valid config
    config = ProviderConfig(api_key="test", model="test")
    assert config.api_key == "test"
    assert config.model == "test"
    assert config.timeout_ms == 300000  # Default
    assert config.extra_params is None  # Default

    # Test empty API key
    with pytest.raises(ValueError, match="API key is required"):
        ProviderConfig(api_key="", model="test")

    # Test empty model
    with pytest.raises(ValueError, match="Model is required"):
        ProviderConfig(api_key="test", model="")


def test_get_env_int() -> None:
    """Test get_env_int function."""
    # Test with valid value
    with patch.dict(os.environ, {"TEST_INT": "123"}):
        assert get_env_int("TEST_INT", 456) == 123

    # Test with invalid value
    with patch.dict(os.environ, {"TEST_INT": "invalid"}):
        assert get_env_int("TEST_INT", 456) == 456

    # Test with missing value
    assert get_env_int("NONEXISTENT", 789) == 789


def test_provider_initialization(
    provider_config: ProviderConfig, mock_provider: TestProvider
) -> None:
    """Test provider initialization."""
    assert mock_provider.config == provider_config
    assert mock_provider.name == "test_provider"
    assert mock_provider.progress_tracker is not None


def test_validate_response(mock_provider: TestProvider) -> None:
    """Test response format validation."""
    # Valid format
    valid_response = "1. [ ] ISSUE HIGH\nTest description"
    assert mock_provider.validate_response(valid_response)

    # Invalid format
    invalid_responses = [
        "",  # Empty
        "Test description",  # No issue marker
        "[ ] ISSUE HIGH\nTest",  # No number
        "1. ISSUE HIGH\nTest",  # No checkbox
    ]
    for response in invalid_responses:
        assert not mock_provider.validate_response(response)


@pytest.mark.asyncio
async def test_response_validation_and_fixing(
    mock_provider: TestProvider,
) -> None:
    """Test response validation and fixing."""
    # Already correct format - should be preserved
    correct = "1. [ ] ISSUE HIGH\nTest"
    mock_provider.send_request_mock.return_value = correct
    result = await mock_provider.analyze(correct)
    assert result == correct

    # Need fixing - should be fixed with IMPROVE
    incorrect = "Test description"
    mock_provider.send_request_mock.return_value = incorrect
    result = await mock_provider.analyze(incorrect)
    assert result.startswith("1. [ ] ISSUE IMPROVE\n")


@pytest.mark.asyncio
async def test_token_limits(mock_provider: TestProvider) -> None:
    """Test token limit handling."""
    # Within limit
    result = await mock_provider.analyze("small content")
    assert result is not None

    # Exceed limit
    large_content = "x" * 5000  # Will exceed 1000 token limit
    with pytest.raises(ValueError, match="Content size .* exceeds model"):
        await mock_provider.analyze(large_content)

    # No limit set
    mock_provider.config.extra_params = None
    result = await mock_provider.analyze(large_content)
    assert result is not None


@pytest.mark.asyncio
async def test_message_preparation(mock_provider: TestProvider) -> None:
    """Test message preparation through analyze."""
    result = await mock_provider.analyze("test content")
    assert result is not None
    assert "1. [ ] ISSUE HIGH" in result


@pytest.mark.asyncio
async def test_make_request_success(mock_provider: TestProvider) -> None:
    """Test successful request."""
    result = await mock_provider.analyze("test content")
    assert "1. [ ] ISSUE HIGH" in result


@pytest.mark.asyncio
async def test_make_request_timeout(mock_provider: TestProvider) -> None:
    """Test request timeout."""

    async def slow_request(*args: Any) -> str:
        await asyncio.sleep(2)  # Longer than timeout
        return "result"

    mock_provider.send_request_mock = AsyncMock(side_effect=slow_request)

    with pytest.raises(ValueError, match="Request timed out"):
        await mock_provider.analyze("test content")


@pytest.mark.asyncio
async def test_make_request_empty_response(
    mock_provider: TestProvider,
) -> None:
    """Test empty response handling."""
    mock_provider.send_request_mock.return_value = ""
    with pytest.raises(ValueError, match="Empty response received"):
        await mock_provider.analyze("test content")


@pytest.mark.asyncio
async def test_make_request_invalid_format(
    mock_provider: TestProvider,
) -> None:
    """Test invalid format handling."""
    mock_provider.send_request_mock.return_value = "Invalid format response"
    result = await mock_provider.analyze("test content")
    assert result.startswith("1. [ ] ISSUE IMPROVE\n")


@pytest.mark.asyncio
async def test_progress_tracking(mock_provider: TestProvider) -> None:
    """Test progress tracking during request."""
    progress_updates: List[float] = []

    # Create a test progress tracker
    tracker = TestProgressTracker(progress_updates)
    mock_provider.progress_tracker = tracker

    await mock_provider.analyze("test content")

    # Verify progress steps
    assert 10 in progress_updates  # START
    assert 20 in progress_updates  # PREPARING
    assert 30 in progress_updates  # SENDING
    assert 60 in progress_updates  # RECEIVING
    assert 80 in progress_updates  # VALIDATING
    assert 100 in progress_updates  # COMPLETE


@pytest.mark.asyncio
async def test_analyze_workflow(mock_provider: TestProvider) -> None:
    """Test complete analysis workflow."""
    result = await mock_provider.analyze("test content")
    assert "1. [ ] ISSUE HIGH" in result
    assert "Test" in result
