"""Base provider abstraction for code analysis.

This module provides the base infrastructure for AI providers that analyze
code.
It includes:
- Configuration management with environment variables
- Token counting and limit validation
- Progress tracking during analysis
- Response format validation and fixing
- Standardized error handling and logging

Each provider (OpenAI, Anthropic, Gemini) should inherit from BaseProvider
and implement the required abstract methods.
"""

import abc
import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, List, Optional, TypedDict

from ..utils.progress import ProgressTracker

logger = logging.getLogger(__name__)


def get_env_int(key: str, default: int) -> int:
    """Get integer value from environment with default.

    Args:
        key: Environment variable name
        default: Default value if environment variable is not set or invalid

    Returns:
        int: Value from environment or default if not found/invalid

    Example:
        >>> get_env_int("MAX_TOKENS", 1000)
        # Returns 1000 if MAX_TOKENS is not set
        # Returns int value if MAX_TOKENS is set and valid
        # Returns 1000 and logs warning if MAX_TOKENS is set but invalid
    """
    value = os.environ.get(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(
            "Invalid value for %s: %s, using default: %d", key, value, default
        )
        return default


# Configuration with defaults
DEFAULT_TOKEN_RATIO = get_env_int("DEFAULT_TOKEN_RATIO", 4)
PROGRESS_STEPS = {
    "START": get_env_int("PROGRESS_START", 10),
    "PREPARING": get_env_int("PROGRESS_PREPARING", 20),
    "SENDING": get_env_int("PROGRESS_SENDING", 30),
    "RECEIVING": get_env_int("PROGRESS_RECEIVING", 60),
    "VALIDATING": get_env_int("PROGRESS_VALIDATING", 80),
    "COMPLETE": get_env_int("PROGRESS_COMPLETE", 100),
}


@dataclass
class Message:
    """Universal message format for all providers.

    This class represents a standardized message format that all providers
    must use when communicating with their respective APIs.

    Attributes:
        role: The role of the message sender (e.g., "user", "assistant")
        content: The actual content of the message
    """

    role: str
    content: str


class ProviderMessage(TypedDict):
    """Provider message format."""

    role: str
    content: str


@dataclass
class ProviderConfig:
    """Configuration for AI provider.

    This class handles the configuration required for each AI provider,
    including API keys, model selection, and provider-specific
    parameters.

    Attributes:
        api_key: The API key for authentication with the provider
        model: The specific model to use (e.g., "gpt-4", "claude-2")
        extra_params: Optional provider-specific parameters

    Raises:
        ValueError: If api_key or model is empty
    """

    api_key: str
    model: str
    timeout_ms: int = 300000  # Default 5 minutes
    extra_params: Optional[Dict[str, Any]] = (
        None  # For model-specific settings
    )

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not self.api_key:
            raise ValueError("API key is required")
        if not self.model:
            raise ValueError("Model is required")


class BaseProvider(abc.ABC):
    """Base class for AI providers.

    This abstract class defines the interface that all AI providers must
    implement.
    It provides common functionality for:
    - Token management and limiting
    - Progress tracking
    - Response validation and formatting
    - Error handling and logging

    Each provider must implement:
    - analyze(): Main method for code analysis
    - count_tokens(): Provider-specific token counting
    - _send_request(): Provider-specific API communication

    The class handles:
    - Token limit validation
    - Progress tracking during analysis
    - Response format validation
    - Standard error handling and logging
    """

    name: ClassVar[str]

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize provider with configuration.

        Sets up the provider with the given configuration and initializes
        the progress tracker for monitoring analysis progress.

        Args:
            config: Provider configuration including API key and model

        Logs:
            Info: Provider initialization with model name
        """
        self.config = config
        self.progress_tracker = ProgressTracker(
            total_steps=100, prefix="[AI Analysis]"
        )
        logger.info(
            "Initialized %s provider with model %s", self.name, config.model
        )

    @abc.abstractmethod
    async def analyze(self, content: str) -> str:
        """Analyze code and return improvements.

        This is the main entry point for code analysis. Each provider must
        implement this method to analyze the given code using their
        specific API.

        Args:
            content: The code content to analyze

        Returns:
            str: Analysis results in the standard format:
                1. [ ] ISSUE SEVERITY
                   Description and suggested improvements

        Raises:
            ValueError: If the content exceeds token limits
            Exception: For provider-specific errors
        """
        pass

    @staticmethod
    def validate_response(response: str) -> bool:
        """Validate response format.

        Checks if response follows the required format:
        1. [ ] ISSUE SEVERITY
        """
        if not response:
            return False

        # Basic format validation
        lines = response.split("\n")
        for line in lines:
            if line.strip().startswith("1. [ ] ISSUE"):
                return True
        return False

    def _fix_response_format(self, response: str) -> str:
        """Try to fix response format if possible."""
        if not response.strip().startswith("1. [ ]"):
            response = "1. [ ] ISSUE IMPROVE\n\n" + response
        return response

    @abc.abstractmethod
    def count_tokens(self, content: str) -> int:
        """Count tokens in content using provider-specific tokenizer.

        Args:
            content: Text content to count tokens for

        Returns:
            Number of tokens in content
        """
        pass

    def _check_token_limit(self, content: str) -> None:
        """Check if content exceeds model's token limit.

        Args:
            content: Content to check

        Raises:
            ValueError: If content exceeds token limit
        """
        if not self.config.extra_params:
            return

        token_limit = self.config.extra_params.get("token_limit")
        if not token_limit:
            return

        try:
            # Get exact token count using provider tokenizer
            token_count = self.count_tokens(content)

            if token_count > token_limit:
                raise ValueError(
                    f"Content size ({token_count:,} tokens) exceeds model "
                    f"{self.config.model} token limit ({token_limit:,}).\n"
                    "Please either:\n"
                    "1. Reduce content size by selecting fewer files\n"
                    "2. Use a model with a higher token limit\n"
                    "3. Split content into smaller chunks"
                )
        except Exception as e:
            # Fallback to estimation if tokenizer fails
            logger.warning(
                "Token counting failed for model %s: %s. Using estimation.",
                self.config.model,
                str(e),
            )
            estimated_tokens = len(content) // DEFAULT_TOKEN_RATIO

            if estimated_tokens > token_limit:
                msg = (
                    f"Estimated size ({estimated_tokens:,} tokens) may exceed "
                    f"model {self.config.model} limit ({token_limit:,} tokens)"
                )
                raise ValueError(
                    f"{msg}.\nPlease either:\n"
                    "1. Reduce the content size by selecting fewer files\n"
                    "2. Use a model with a higher token limit\n"
                    "3. Split the content into smaller chunks"
                )

    def _prepare_messages(self, content: str) -> List[Message]:
        """Prepare messages in a standard format with token limit check."""
        # Check token limit before preparing messages
        self._check_token_limit(content)
        return [Message(role="user", content=content)]

    async def _make_request(self, messages: List[Message]) -> str:
        """Make request to AI provider with token management."""
        try:
            # Start progress tracking
            await self.progress_tracker.start()
            await self.progress_tracker.update(PROGRESS_STEPS["START"])

            # Prepare request
            await self.progress_tracker.update(PROGRESS_STEPS["PREPARING"])

            # Send request with timeout
            await self.progress_tracker.update(PROGRESS_STEPS["SENDING"])
            # Convert timeout from ms to seconds
            timeout_seconds = self.config.timeout_ms / 1000
            try:
                response = await asyncio.wait_for(
                    self._send_request(messages),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                await self.progress_tracker.stop("Timeout")
                timeout_minutes = self.config.timeout_ms / 60000
                raise ValueError(
                    f"Request timed out after {timeout_minutes:.1f} minutes"
                )

            # Process response
            await self.progress_tracker.update(PROGRESS_STEPS["RECEIVING"])
            if not response:
                raise ValueError(
                    f"Empty response received from {self.name} provider. "
                    "This may indicate:\n"
                    "1. A network connectivity issue\n"
                    "2. An API rate limit being exceeded\n"
                    "3. The model failing to generate a response\n"
                    "Please try again or check the API status."
                )

            # Validate and fix format
            await self.progress_tracker.update(PROGRESS_STEPS["VALIDATING"])
            if not self.validate_response(response):
                logger.warning(
                    "Response format validation failed for model %s",
                    self.config.model,
                )
                response = self._fix_response_format(response)

            # Complete
            await self.progress_tracker.update(PROGRESS_STEPS["COMPLETE"])
            await self.progress_tracker.stop("Analysis complete")
            return response

        except Exception as e:
            logger.error(
                "%s analysis failed with model %s: %s",
                self.name,
                self.config.model,
                str(e),
            )
            await self.progress_tracker.stop(f"Error: {str(e)}")
            raise

    @abc.abstractmethod
    async def _send_request(self, messages: List[Message]) -> str:
        """Send request to provider API."""
        pass
