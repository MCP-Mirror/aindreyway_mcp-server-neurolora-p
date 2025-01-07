"""Integration tests for OpenAI provider."""

import asyncio
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest import mark
from openai.types.chat import ChatCompletionMessage
from pytest_mock import MockerFixture

from mcpneurolora.providers.base_provider import ProviderConfig

# Skip all OpenAI tests on Python 3.13+ due to dataclasses compatibility issue
skip_openai_tests = pytest.mark.skipif(
    sys.version_info >= (3, 13),
    reason=("Tests incompatible with Python 3.13+ dataclasses"),
)


class FakeOpenAIError(Exception):
    """Fake OpenAI error."""


class FakeChoice:
    """Fake ChatCompletionChoice."""

    def __init__(self, content: str | None = None) -> None:
        """Initialize fake choice."""
        self.message = ChatCompletionMessage(
            role="assistant",
            content=content,
        )


class FakeResponse:
    """Fake ChatCompletion response."""

    def __init__(self, choices: list[FakeChoice]) -> None:
        """Initialize fake response."""
        self.choices = choices


def create_fake_openai(  # type: ignore[no-any-return, no-untyped-call, return-value]
    api_key: str,
    timeout: float,
) -> MagicMock:  # type: ignore[type-arg]
    """Create a fake OpenAI client for testing."""
    mock = MagicMock()
    mock.api_key = api_key
    mock.timeout = timeout
    mock.chat = MagicMock()
    mock.chat.completions = MagicMock()
    mock.chat.completions.create = AsyncMock()
    mock.chat.completions.create.return_value = None  # type: ignore[no-untyped-call]
    return mock


@pytest.fixture
def mock_progress_tracker(mocker: MockerFixture) -> MagicMock:
    """Mock ProgressTracker."""
    mock = mocker.MagicMock()
    mock.return_value.start = AsyncMock()
    mock.return_value.stop = AsyncMock()
    mocker.patch("mcpneurolora.utils.progress.ProgressTracker", return_value=mock)
    return mock


@pytest.fixture
def provider_config() -> ProviderConfig:
    """Provider configuration fixture."""
    return ProviderConfig(
        api_key="test_api_key",
        model="gpt-4",
        timeout_ms=30000,
    )


@skip_openai_tests
@mark.integration
def test_init(provider_config: ProviderConfig) -> None:
    """Test provider initialization."""
    from mcpneurolora.providers.openai_provider import OpenAIProvider

    with patch(
        "mcpneurolora.providers.openai_provider.sys.modules", {"openai": MagicMock()}
    ), patch("mcpneurolora.providers.openai_provider.AsyncOpenAI", create_fake_openai):
        provider = OpenAIProvider(config=provider_config)

        # Check provider attributes
        assert provider.config.api_key == provider_config.api_key
        assert provider.config.model == provider_config.model
        assert isinstance(provider.client, MagicMock)
        assert provider.client.api_key == provider_config.api_key
        assert provider.client.timeout == provider_config.timeout_ms / 1000


@skip_openai_tests
@mark.integration
def test_count_tokens(provider_config: ProviderConfig) -> None:
    """Test token counting."""
    from mcpneurolora.providers.openai_provider import OpenAIProvider

    with patch(
        "mcpneurolora.providers.openai_provider.sys.modules", {"openai": MagicMock()}
    ), patch(
        "mcpneurolora.providers.openai_provider.AsyncOpenAI", create_fake_openai
    ), patch(
        "mcpneurolora.providers.openai_provider.count_tokens"
    ) as mock_count:
        provider = OpenAIProvider(config=provider_config)
        content = "Test content"

        mock_count.return_value = 42  # type: ignore[no-untyped-call]
        count = provider.count_tokens(content)

        mock_count.assert_called_once_with(  # type: ignore[no-untyped-call]
            content, provider_config.model
        )
        assert count == 42


@skip_openai_tests
@pytest.mark.asyncio
@mark.integration
@mark.slow
async def test_analyze(
    mock_progress_tracker: MagicMock,
    provider_config: ProviderConfig,
) -> None:
    """Test code analysis."""
    from mcpneurolora.providers.openai_provider import OpenAIProvider

    # Set up mock response
    mock_response = FakeResponse([FakeChoice("Analysis result")])

    with patch(
        "mcpneurolora.providers.openai_provider.sys.modules", {"openai": MagicMock()}
    ), patch("mcpneurolora.providers.openai_provider.AsyncOpenAI", create_fake_openai):
        provider = OpenAIProvider(config=provider_config)
        mock_create = provider.client.chat.completions.create
        mock_create.return_value = (  # type: ignore[no-untyped-call, attr-defined]
            mock_response
        )
        content = "Test content"

        # Test analysis
        result = await provider.analyze(content)

        # Check API call
        expected_messages = [{"role": "user", "content": content}]
        call_kwargs: dict[str, Any] = {
            "model": provider_config.model,
            "messages": expected_messages,
        }
        mock_create.assert_called_once_with(  # type: ignore[no-untyped-call]
            **call_kwargs
        )

        # Check progress tracker
        mock_progress_tracker.return_value.start.assert_called_once()
        mock_progress_tracker.return_value.stop.assert_called_once_with("Complete")

        # Check result
        assert result == "Analysis result"


@skip_openai_tests
@pytest.mark.asyncio
@mark.integration
@mark.slow
async def test_analyze_timeout(
    mock_progress_tracker: MagicMock,
    provider_config: ProviderConfig,
) -> None:
    """Test timeout handling."""
    from mcpneurolora.providers.openai_provider import OpenAIProvider

    with patch(
        "mcpneurolora.providers.openai_provider.sys.modules", {"openai": MagicMock()}
    ), patch("mcpneurolora.providers.openai_provider.AsyncOpenAI", create_fake_openai):
        provider = OpenAIProvider(config=provider_config)
        mock_create = provider.client.chat.completions.create
        error_msg = "Event loop timed out"
        mock_create.side_effect = (  # type: ignore[no-untyped-call, attr-defined]
            asyncio.TimeoutError(error_msg)
        )
        content = "Test content"

        # Test timeout handling
        with pytest.raises(ValueError, match=f"Unexpected error: {error_msg}"):
            await provider.analyze(content)

        # Check progress tracker
        mock_progress_tracker.return_value.start.assert_called_once()
        mock_progress_tracker.return_value.stop.assert_called_once_with("Failed")


@skip_openai_tests
@pytest.mark.asyncio
@mark.integration
@mark.slow
async def test_analyze_empty_response(
    mock_progress_tracker: MagicMock,
    provider_config: ProviderConfig,
) -> None:
    """Test empty response handling."""
    from mcpneurolora.providers.openai_provider import OpenAIProvider

    # Set up mock response
    mock_response = FakeResponse([])

    with patch(
        "mcpneurolora.providers.openai_provider.sys.modules", {"openai": MagicMock()}
    ), patch("mcpneurolora.providers.openai_provider.AsyncOpenAI", create_fake_openai):
        provider = OpenAIProvider(config=provider_config)
        mock_create = provider.client.chat.completions.create
        mock_create.return_value = (  # type: ignore[no-untyped-call, attr-defined]
            mock_response
        )
        content = "Test content"

        # Test empty response handling
        with pytest.raises(ValueError, match="Empty response from OpenAI"):
            await provider.analyze(content)

        # Check progress tracker
        mock_progress_tracker.return_value.start.assert_called_once()
        mock_progress_tracker.return_value.stop.assert_called_once_with("Failed")


@skip_openai_tests
@pytest.mark.asyncio
@mark.integration
@mark.slow
async def test_analyze_empty_content(
    mock_progress_tracker: MagicMock,
    provider_config: ProviderConfig,
) -> None:
    """Test empty content handling."""
    from mcpneurolora.providers.openai_provider import OpenAIProvider

    # Set up mock response
    mock_response = FakeResponse([FakeChoice(None)])

    with patch(
        "mcpneurolora.providers.openai_provider.sys.modules", {"openai": MagicMock()}
    ), patch("mcpneurolora.providers.openai_provider.AsyncOpenAI", create_fake_openai):
        provider = OpenAIProvider(config=provider_config)
        mock_create = provider.client.chat.completions.create
        mock_create.return_value = (  # type: ignore[no-untyped-call, attr-defined]
            mock_response
        )
        content = "Test content"

        # Test empty content handling
        with pytest.raises(ValueError, match="Empty message content from OpenAI"):
            await provider.analyze(content)

        # Check progress tracker
        mock_progress_tracker.return_value.start.assert_called_once()
        mock_progress_tracker.return_value.stop.assert_called_once_with("Failed")


@skip_openai_tests
@pytest.mark.asyncio
@mark.integration
@mark.slow
async def test_analyze_openai_error(
    mock_progress_tracker: MagicMock,
    provider_config: ProviderConfig,
) -> None:
    """Test OpenAI error handling."""
    from mcpneurolora.providers.openai_provider import OpenAIProvider

    with patch(
        "mcpneurolora.providers.openai_provider.sys.modules", {"openai": MagicMock()}
    ), patch(
        "mcpneurolora.providers.openai_provider.AsyncOpenAI", create_fake_openai
    ), patch(
        "mcpneurolora.providers.openai_provider.OpenAIError", FakeOpenAIError
    ):
        provider = OpenAIProvider(config=provider_config)
        mock_create = provider.client.chat.completions.create
        mock_create.side_effect = (  # type: ignore[no-untyped-call, attr-defined]
            FakeOpenAIError("Test error")
        )
        content = "Test content"

        # Test OpenAI error handling
        with pytest.raises(ValueError, match="OpenAI API error: Test error"):
            await provider.analyze(content)

        # Check progress tracker
        mock_progress_tracker.return_value.start.assert_called_once()
        mock_progress_tracker.return_value.stop.assert_called_once_with("Failed")


@skip_openai_tests
@mark.integration
def test_import_error() -> None:
    """Test import error handling."""
    from mcpneurolora.providers.openai_provider import OpenAIProvider

    with patch("mcpneurolora.providers.openai_provider.sys.modules", {}):
        with pytest.raises(ImportError, match="OpenAI package not found"):
            OpenAIProvider(config=ProviderConfig(api_key="test", model="test"))
