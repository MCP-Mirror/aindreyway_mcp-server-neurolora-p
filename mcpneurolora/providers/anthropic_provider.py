"""Anthropic provider implementation."""

import logging
from typing import Any, List

from anthropic import AsyncAnthropic

from ..utils.token_counter import count_tokens
from .base_provider import BaseProvider, Message, ProviderConfig

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AnthropicProvider(BaseProvider):
    """Anthropic provider implementation."""

    name = "anthropic"
    client: Any = None

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize provider with configuration."""
        super().__init__(config)
        try:
            # Convert timeout from ms to seconds for Anthropic client
            timeout_seconds = self.config.timeout_ms / 1000
            self.client = AsyncAnthropic(
                api_key=self.config.api_key,
                timeout=timeout_seconds,
            )
            logger.info(
                "Initialized Anthropic provider with model %s",
                self.config.model,
            )
        except ImportError:
            raise ImportError(
                "Anthropic package not found. "
                "Install it with: pip install anthropic"
            )

    def count_tokens(self, content: str) -> int:
        """Count tokens in content.

        Args:
            content: Text content to count tokens for

        Returns:
            Number of tokens in content
        """
        return count_tokens(content, self.config.model, "cl100k_base")

    async def analyze(self, content: str) -> str:
        """Analyze code using Anthropic API."""
        messages = self._prepare_messages(content)
        return await self._make_request(messages)

    async def _send_request(self, messages: List[Message]) -> str:
        """Send request to Anthropic API."""
        if not self.client:
            raise RuntimeError("Anthropic client not initialized")

        try:
            # Convert messages to Anthropic format
            anthropic_messages = [
                {
                    "role": "user" if msg.role == "user" else "assistant",
                    "content": msg.content,
                }
                for msg in messages
            ]

            # Make API request
            response = await self.client.messages.create(
                model=self.config.model,
                messages=anthropic_messages,
                max_tokens=1024,
            )

            # Extract text from response
            if not response.content or not response.content[0].text:
                raise ValueError("Empty response received from Anthropic")

            return str(response.content[0].text)

        except Exception as e:
            logger.error("Error in Anthropic request: %s", str(e))
            raise ValueError(f"Error in Anthropic request: {str(e)}")
