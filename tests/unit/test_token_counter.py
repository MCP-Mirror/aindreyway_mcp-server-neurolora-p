"""Tests for token counting utilities."""

import pytest
from pytest_mock import MockerFixture

from mcpneurolora.utils.token_counter import count_tokens, get_token_limit


def test_get_token_limit() -> None:
    """Test getting token limits for different models."""
    # Test OpenAI models
    assert get_token_limit("gpt-4-32k") == 32768
    assert get_token_limit("gpt-4") == 8192
    assert get_token_limit("gpt-3.5-turbo-16k") == 16384
    assert get_token_limit("gpt-3.5-turbo") == 4096
    assert get_token_limit("o1") == 200000
    assert get_token_limit("o1-preview") == 128000
    assert get_token_limit("o1-preview-2024-09-12") == 128000

    # Test Anthropic models
    assert get_token_limit("claude-3-opus-20240229") == 200000
    assert get_token_limit("claude-3-sonnet-20240229") == 200000
    assert get_token_limit("claude-3-haiku-20240307") == 200000

    # Test Gemini models
    assert get_token_limit("gemini-2.0-flash-exp") == 1048576
    assert get_token_limit("gemini-2.0-flash-thinking-exp-1219") == 32767

    # Test unknown model
    assert get_token_limit("unknown-model") is None


def test_count_tokens(mocker: MockerFixture) -> None:
    """Test token counting."""
    # Mock tiktoken encoding
    mock_encoding = mocker.MagicMock()
    mock_encoding.encode.side_effect = lambda text: [] if not text else [1, 2, 3]
    mocker.patch(
        "tiktoken.encoding_for_model",
        return_value=mock_encoding,
    )

    # Test with known model
    text = "Hello, world!"
    count = count_tokens(text, "gpt-4")
    assert isinstance(count, int)
    assert count > 0

    # Test with fallback encoding
    count = count_tokens(text, "unknown-model")
    assert isinstance(count, int)
    assert count > 0

    # Test empty string
    assert count_tokens("", "gpt-4") == 0

    # Test with special characters
    text_with_special = "Hello 🌍! How are you?"
    count = count_tokens(text_with_special, "gpt-4")
    assert isinstance(count, int)
    assert count > 0

    # Test with long text
    long_text = "Hello " * 1000
    mock_encoding.encode.side_effect = lambda text: [1] * (len(str(text)) // 4)
    count = count_tokens(long_text, "gpt-4")
    assert isinstance(count, int)
    assert count > 1000  # Each "Hello " should be at least one token


def test_count_tokens_import_error(mocker: MockerFixture) -> None:
    """Test ImportError handling."""
    # Mock the import of tiktoken to raise ImportError
    mocker.patch(
        "mcpneurolora.utils.token_counter.tiktoken.encoding_for_model",
        side_effect=ImportError("No module named 'tiktoken'"),
    )
    text = "Hello, world!"
    with pytest.raises(ImportError, match="tiktoken package not found"):
        count_tokens(text, "gpt-4")


def test_count_tokens_error_handling(mocker: MockerFixture) -> None:
    """Test error handling in token counting."""
    # Mock tiktoken encoding
    mock_encoding = mocker.MagicMock()
    mock_encoding.encode.return_value = [1, 2, 3]  # Simulate tokens
    mocker.patch(
        "tiktoken.encoding_for_model",
        side_effect=KeyError("Model not found"),
    )
    mocker.patch(
        "tiktoken.get_encoding",
        return_value=mock_encoding,
    )

    # Test with invalid model (should fall back to base encoding)
    text = "Hello, world!"
    count = count_tokens(text, "invalid-model")
    assert isinstance(count, int)
    assert count > 0

    # Test with invalid fallback encoding
    mocker.patch(
        "tiktoken.get_encoding",
        side_effect=Exception("Invalid encoding"),
    )
    count = count_tokens(text, "invalid-model", fallback_encoding="invalid-encoding")
    assert count == len(text) // 4  # Should fall back to simple estimation
