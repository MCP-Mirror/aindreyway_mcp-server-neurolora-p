"""Integration tests for Gemini provider."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest import mark
from pytest_mock import MockerFixture

from mcpneurolora.providers.base_provider import ProviderConfig
from mcpneurolora.providers.gemini_provider import GeminiProvider


@pytest.fixture
def mock_genai(mocker: MockerFixture) -> MagicMock:
    """Mock google.generativeai module."""
    mock = MagicMock()
    mocker.patch("mcpneurolora.providers.gemini_provider.genai", mock)
    return mock


@pytest.fixture
def mock_progress_tracker(mocker: MockerFixture) -> MagicMock:
    """Mock ProgressTracker."""
    mock_tracker = MagicMock()
    mock_tracker.return_value.start = AsyncMock()
    mock_tracker.return_value.stop = AsyncMock()
    mocker.patch("mcpneurolora.providers.gemini_provider.ProgressTracker", mock_tracker)
    return mock_tracker


@pytest.fixture
def provider_config() -> ProviderConfig:
    """Provider configuration fixture."""
    return ProviderConfig(
        api_key="test_api_key",
        model="test-model",
        timeout_ms=30000,
    )


@mark.integration
def test_init(mock_genai: MagicMock, provider_config: ProviderConfig) -> None:
    """Test provider initialization."""
    provider = GeminiProvider(config=provider_config)

    # Check API key configuration
    mock_genai.configure.assert_called_once_with(api_key=provider_config.api_key)

    # Check model initialization
    mock_genai.GenerativeModel.assert_called_once_with(provider_config.model)

    # Check provider attributes
    assert provider.config.api_key == provider_config.api_key
    assert provider.config.model == provider_config.model
    assert provider.model == mock_genai.GenerativeModel.return_value


@mark.integration
def test_init_default_model(mock_genai: MagicMock) -> None:
    """Test provider initialization with default model."""
    config = ProviderConfig(
        api_key="test_api_key",
        model=GeminiProvider.default_model,  # Use default model from provider
    )
    provider = GeminiProvider(config=config)

    # Check model initialization with default model
    mock_genai.GenerativeModel.assert_called_once_with(provider.default_model)


@mark.integration
def test_count_tokens(mock_genai: MagicMock, provider_config: ProviderConfig) -> None:
    """Test token counting."""
    provider = GeminiProvider(config=provider_config)
    content = "Test content"

    with patch("mcpneurolora.providers.gemini_provider.count_tokens") as mock_count:
        mock_count.return_value = 42
        count = provider.count_tokens(content)

        mock_count.assert_called_once_with(
            content, provider_config.model, "cl100k_base"
        )
        assert count == 42


@pytest.mark.asyncio
@mark.integration
@mark.slow
async def test_analyze(
    mock_genai: MagicMock,
    mock_progress_tracker: MagicMock,
    provider_config: ProviderConfig,
) -> None:
    """Test code analysis."""
    provider = GeminiProvider(config=provider_config)
    content = "Test content"

    # Mock response
    mock_response = MagicMock()
    mock_response.text = "Analysis result"
    provider.model.generate_content_async = AsyncMock(return_value=mock_response)

    # Test analysis
    result = await provider.analyze(content)

    # Check progress tracker
    mock_progress_tracker.assert_called_once()
    mock_progress_tracker.return_value.start.assert_called_once()
    mock_progress_tracker.return_value.stop.assert_called_once_with("Complete")

    # Check result
    assert result == "Analysis result"


@pytest.mark.asyncio
@mark.integration
@mark.slow
async def test_analyze_timeout(
    mock_genai: MagicMock,
    mock_progress_tracker: MagicMock,
    provider_config: ProviderConfig,
) -> None:
    """Test timeout handling."""
    provider = GeminiProvider(config=provider_config)
    content = "Test content"

    # Mock timeout
    provider.model.generate_content_async = AsyncMock(side_effect=asyncio.TimeoutError)

    # Test timeout handling
    with pytest.raises(ValueError, match="Request timed out"):
        await provider.analyze(content)

    # Check progress tracker
    mock_progress_tracker.assert_called_once()
    mock_progress_tracker.return_value.start.assert_called_once()
    mock_progress_tracker.return_value.stop.assert_called_once_with("Timeout")


@pytest.mark.asyncio
@mark.integration
@mark.slow
async def test_analyze_error(
    mock_genai: MagicMock,
    mock_progress_tracker: MagicMock,
    provider_config: ProviderConfig,
) -> None:
    """Test error handling."""
    provider = GeminiProvider(config=provider_config)
    content = "Test content"

    # Mock error
    error = Exception("Test error")
    provider.model.generate_content_async = AsyncMock(side_effect=error)

    # Test error handling
    with pytest.raises(Exception, match="Test error"):
        await provider.analyze(content)

    # Check progress tracker
    mock_progress_tracker.assert_called_once()
    mock_progress_tracker.return_value.start.assert_called_once()
    mock_progress_tracker.return_value.stop.assert_called_once_with("Failed")
