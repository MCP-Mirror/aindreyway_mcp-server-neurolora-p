"""OpenAI provider implementation."""

import logging
from typing import Any, Dict, List, cast

from openai import AsyncOpenAI, OpenAIError
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.chat_completion import ChatCompletion

from ..utils.token_counter import count_tokens
from .base_provider import BaseProvider, Message, ProviderConfig

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI provider implementation."""

    name = "openai"
    client: AsyncOpenAI

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize provider with configuration."""
        super().__init__(config)
        # Convert timeout from ms to seconds for OpenAI client
        timeout_seconds = self.config.timeout_ms / 1000
        self.client = AsyncOpenAI(
            api_key=self.config.api_key,
            timeout=timeout_seconds,
        )

    def count_tokens(self, content: str) -> int:
        """Count tokens in content.

        Args:
            content: Text content to count tokens for

        Returns:
            Number of tokens in content
        """
        return count_tokens(content, self.config.model)

    async def analyze(self, content: str) -> str:
        """Analyze code using OpenAI API."""
        messages = self._prepare_messages(content)
        return await self._make_request(messages)

    async def _send_request(self, messages: List[Message]) -> str:
        """Send request to OpenAI API."""
        try:
            # Convert messages to OpenAI format
            openai_messages = [
                cast(
                    ChatCompletionMessageParam,
                    {"role": msg.role, "content": msg.content},
                )
                for msg in messages
            ]

            try:
                # Prepare API parameters
                params: Dict[str, Any] = {
                    "model": self.config.model,
                    "messages": openai_messages,
                }

                try:
                    response = cast(
                        ChatCompletion,
                        await self.client.chat.completions.create(**params),
                    )
                except Exception as e:
                    logger.error("Error during API request: %s", str(e))
                    raise

                # Get response content
                choices = response.choices
                if not choices:
                    raise ValueError("Empty response from OpenAI")

                content = choices[0].message.content
                if not content:
                    raise ValueError("Empty message content from OpenAI")

                return str(content)

            except OpenAIError as e:
                raise ValueError(f"OpenAI API error: {str(e)}")
            except Exception as e:
                raise ValueError(f"Unexpected error: {str(e)}")

        except ImportError:
            raise ImportError(
                "OpenAI package not found. Install it with: pip install openai"
            )
