"""Token counting utilities for AI providers."""

import logging
from typing import Dict, Optional

import tiktoken

logger = logging.getLogger(__name__)

# Cache for tokenizers to avoid recreating them
_tokenizers: Dict[str, tiktoken.Encoding] = {}


def count_tokens(
    content: str, model: str, fallback_encoding: str = "cl100k_base"
) -> int:
    """Count tokens in content using tiktoken.

    Args:
        content: Text content to count tokens for
        model: Model name to use for token counting
        fallback_encoding: Fallback encoding to use if model-specific encoding
                         is not available

    Returns:
        int: Number of tokens in content

    Raises:
        ImportError: If tiktoken is not installed
        ValueError: If model encoding is not found and fallback fails
    """
    try:
        # Get or create tokenizer for this model
        if model not in _tokenizers:
            try:
                # Try model-specific encoding first
                _tokenizers[model] = tiktoken.encoding_for_model(model)
            except KeyError:
                # Fall back to base encoding if model-specific not found
                logger.warning(
                    "Model %s not found in tiktoken, using %s encoding",
                    model,
                    fallback_encoding,
                )
                _tokenizers[model] = tiktoken.get_encoding(fallback_encoding)

        encoding = _tokenizers[model]
        return len(encoding.encode(content))

    except ImportError:
        raise ImportError(
            "tiktoken package not found. Install it with: pip install tiktoken"
        )
    except Exception as e:
        logger.error("Token counting failed: %s", str(e))
        # Fallback to simple estimation
        return len(content) // 4


def get_token_limit(model: str) -> Optional[int]:
    """Get token limit for a specific model.

    Args:
        model: Model name

    Returns:
        Optional[int]: Token limit for the model, or None if unknown
    """
    # OpenAI models
    if model.startswith("gpt-4-32k"):
        return 32768
    elif model.startswith("gpt-4"):
        return 8192
    elif model.startswith("gpt-3.5-turbo-16k"):
        return 16384
    elif model.startswith("gpt-3.5-turbo"):
        return 4096
    elif model == "o1":
        return 200000
    elif model == "o1-preview" or model == "o1-preview-2024-09-12":
        return 128000

    # Anthropic models
    elif model == "claude-3-opus-20240229":
        return 200000
    elif model == "claude-3-sonnet-20240229":
        return 200000
    elif model == "claude-3-haiku-20240307":
        return 200000

    # Gemini models
    elif model == "gemini-2.0-flash-exp":
        return 1048576  # 1M tokens
    elif model == "gemini-2.0-flash-thinking-exp-1219":
        return 32767

    # Unknown model
    return None
