"""Tests for providers/__init__.py module."""

import os
from typing import Dict, Generator, Type
from unittest.mock import patch

import pytest

from mcpneurolora.providers import (
    AnthropicProvider,
    BaseProvider,
    GeminiProvider,
    OpenAIProvider,
    create_provider,
    is_ai_configured,
    model_configs,
)


@pytest.fixture
def mock_env() -> Generator[None, None, None]:
    """Clear environment variables before each test."""
    with patch.dict(os.environ, clear=True):
        yield None


def test_model_configs() -> None:
    """Test model configurations."""
    # Test OpenAI models
    assert "o1" in model_configs
    provider_class, key_env, token_limit = model_configs["o1"]
    assert provider_class == OpenAIProvider
    assert key_env == "OPENAI_API_KEY"
    assert token_limit == 200000

    # Test Gemini models
    assert "gemini-2.0-flash-exp" in model_configs
    provider_class, key_env, token_limit = model_configs["gemini-2.0-flash-exp"]
    assert provider_class == GeminiProvider
    assert key_env == "GEMINI_API_KEY"
    assert token_limit == 1048576

    # Test Anthropic models
    assert "claude-3-opus-20240229" in model_configs
    provider_class, key_env, token_limit = model_configs["claude-3-opus-20240229"]
    assert provider_class == AnthropicProvider
    assert key_env == "ANTHROPIC_API_KEY"
    assert token_limit == 200000


def test_is_ai_configured_no_model(mock_env: None) -> None:
    """Test is_ai_configured when no model is configured."""
    assert not is_ai_configured()


def test_is_ai_configured_invalid_model(mock_env: None) -> None:
    """Test is_ai_configured with invalid model."""
    with patch.dict(os.environ, {"AI_MODEL": "invalid-model"}):
        assert not is_ai_configured()


def test_is_ai_configured_no_api_key(mock_env: None) -> None:
    """Test is_ai_configured when API key is missing."""
    with patch.dict(os.environ, {"AI_MODEL": "o1"}):
        assert not is_ai_configured()


def test_is_ai_configured_success(mock_env: None) -> None:
    """Test is_ai_configured with valid configuration."""
    with patch.dict(os.environ, {"AI_MODEL": "o1", "OPENAI_API_KEY": "test-key"}):
        assert is_ai_configured()


def test_create_provider_default_model(mock_env: None) -> None:
    """Test create_provider with default model."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        provider = create_provider()
        assert isinstance(provider, OpenAIProvider)
        assert provider.config.model == "o1-preview-2024-09-12"


def test_create_provider_custom_model(mock_env: None) -> None:
    """Test create_provider with custom model."""
    with patch.dict(
        os.environ,
        {
            "AI_MODEL": "gemini-2.0-flash-exp",
            "GEMINI_API_KEY": "test-key",
        },
    ):
        provider = create_provider()
        assert isinstance(provider, GeminiProvider)
        assert provider.config.model == "gemini-2.0-flash-exp"


def test_create_provider_invalid_model(mock_env: None) -> None:
    """Test create_provider with invalid model."""
    with patch.dict(os.environ, {"AI_MODEL": "invalid-model"}):
        with pytest.raises(ValueError, match="Unsupported model"):
            create_provider()


def test_create_provider_missing_api_key(mock_env: None) -> None:
    """Test create_provider with missing API key."""
    with patch.dict(os.environ, {"AI_MODEL": "o1"}):
        with pytest.raises(ValueError, match="API key not configured"):
            create_provider()


def test_create_provider_whitespace_api_key(mock_env: None) -> None:
    """Test create_provider with whitespace in API key."""
    with patch.dict(
        os.environ,
        {
            "AI_MODEL": "o1",
            "OPENAI_API_KEY": " test-key ",
        },
    ):
        provider = create_provider()
        assert provider.config.api_key == "test-key"


def test_create_provider_custom_timeout(mock_env: None) -> None:
    """Test create_provider with custom timeout."""
    with patch.dict(
        os.environ,
        {
            "AI_MODEL": "o1",
            "OPENAI_API_KEY": "test-key",
            "AI_TIMEOUT_MS": "10000",
        },
    ):
        provider = create_provider()
        assert provider.config.timeout_ms == 10000


@pytest.mark.parametrize(
    "model,provider_class",
    [
        ("o1", OpenAIProvider),
        ("o1-preview", OpenAIProvider),
        ("o1-preview-2024-09-12", OpenAIProvider),
        ("gemini-2.0-flash-exp", GeminiProvider),
        ("gemini-2.0-flash-thinking-exp-1219", GeminiProvider),
        ("claude-3-opus-20240229", AnthropicProvider),
        ("claude-3-sonnet-20240229", AnthropicProvider),
        ("claude-3-haiku-20240307", AnthropicProvider),
    ],
)
def test_create_provider_all_models(
    mock_env: None, model: str, provider_class: Type[BaseProvider]
) -> None:
    """Test create_provider with all supported models."""
    # Get API key environment variable for this model
    _, key_env, _ = model_configs[model]

    # Set up environment with model and API key
    env: Dict[str, str] = {
        "AI_MODEL": model,
        key_env: "test-key",
    }

    with patch.dict(os.environ, env):
        provider = create_provider()
        assert isinstance(provider, provider_class)
        assert provider.config.model == model
        assert provider.config.api_key == "test-key"
