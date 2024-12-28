"""AI providers package."""

import logging
import os
from typing import Dict

from .anthropic_provider import AnthropicProvider
from .base_provider import BaseProvider, Message, ProviderConfig
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider

# Re-export for better type hints
__annotations__ = {
    "BaseProvider": BaseProvider,
    "Message": Message,
    "ProviderConfig": ProviderConfig,
    "OpenAIProvider": OpenAIProvider,
    "AnthropicProvider": AnthropicProvider,
    "GeminiProvider": GeminiProvider,
}

logger = logging.getLogger(__name__)

__all__ = [
    "BaseProvider",
    "Message",
    "ProviderConfig",
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    # Function to create provider instances
    "create_provider",
    "is_ai_configured",
]


# Model configurations with their limits and providers
# (provider_class, env_key, token_limit)
model_configs: Dict[str, tuple[type[BaseProvider], str, int]] = {
    # OpenAI models
    "o1": (OpenAIProvider, "OPENAI_API_KEY", 200000),
    "o1-preview": (OpenAIProvider, "OPENAI_API_KEY", 128000),
    "o1-preview-2024-09-12": (OpenAIProvider, "OPENAI_API_KEY", 128000),
    # Gemini models
    "gemini-2.0-flash-exp": (GeminiProvider, "GEMINI_API_KEY", 1048576),
    "gemini-2.0-flash-thinking-exp-1219": (
        GeminiProvider,
        "GEMINI_API_KEY",
        32767,
    ),
    # Anthropic models
    "claude-3-opus-20240229": (AnthropicProvider, "ANTHROPIC_API_KEY", 200000),
    "claude-3-sonnet-20240229": (
        AnthropicProvider,
        "ANTHROPIC_API_KEY",
        200000,
    ),
    "claude-3-haiku-20240307": (
        AnthropicProvider,
        "ANTHROPIC_API_KEY",
        200000,
    ),
}


def is_ai_configured() -> bool:
    """Check if AI model and API key are properly configured.

    Returns:
        bool: True if both model and corresponding API key are configured
    """
    model = os.environ.get("AI_MODEL")
    if not model:
        return False

    # Check if model is supported
    if model not in model_configs:
        return False

    # Get required API key environment variable
    _, key_env, _ = model_configs[model]

    # Check if API key is configured
    return bool(os.environ.get(key_env))


def create_provider() -> BaseProvider:
    """Create provider instance based on model configuration.

    Creates a provider instance for the specified model, using the appropriate
    provider class and token limits. The model can be specified via the
    AI_MODEL environment variable.

    Returns:
        Configured provider instance

    Raises:
        ValueError: If model is not supported or API key is missing
    """
    # Get model from environment or use default
    model = os.environ.get("AI_MODEL", "o1-preview-2024-09-12")

    # Validate model
    if model not in model_configs:
        logger.error("Model %s not found in available models", model)
        raise ValueError(f"Unsupported model: {model}")

    # Get model configuration
    provider_class, key_env, token_limit = model_configs[model]
    logger.info(
        "Selected model config: model=%s, provider=%s, key_env=%s",
        model,
        provider_class.__name__,
        key_env,
    )

    # Check for API key
    api_key = os.environ.get(key_env)
    if not api_key:
        logger.error("API key not found in environment: %s", key_env)
        raise ValueError(f"API key not configured for {model}")

    # Check for whitespace in key
    if api_key != api_key.strip():
        logger.warning("API key contains leading/trailing whitespace")
        api_key = api_key.strip()

    # Get timeout from environment or use default (5 minutes)
    timeout_ms = int(os.environ.get("AI_TIMEOUT_MS", "300000"))

    config = ProviderConfig(
        api_key=api_key,
        model=model,
        timeout_ms=timeout_ms,
        extra_params={"token_limit": token_limit},
    )

    logger.info("Creating provider instance: %s", provider_class.__name__)
    provider = provider_class(config)
    logger.info("Provider instance created")
    return provider
