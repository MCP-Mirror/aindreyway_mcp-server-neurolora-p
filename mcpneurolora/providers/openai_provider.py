"""OpenAI provider implementation."""

import logging
import sys
from typing import Any, Dict, List, cast

from openai import AsyncOpenAI, OpenAIError
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.chat_completion import ChatCompletion

from ..utils.progress import ProgressTracker
from ..utils.token_counter import count_tokens
from .base_provider import BaseProvider, Message, ProviderConfig

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI provider implementation."""

    name = "openai"
    client: AsyncOpenAI

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize provider with configuration."""
        if "openai" not in sys.modules:
            raise ImportError(
                "OpenAI package not found. Install it with: pip install openai"
            )

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
        return await self._send_request(messages)

    async def _send_request(self, messages: List[Message]) -> str:
        """Send request to OpenAI API."""
        # Create progress tracker
        progress = ProgressTracker(
            prefix="[AI Analysis]",
            total_steps=100,  # Use 100 steps for smoother progress
        )
        await progress.start()

        try:
            # Combine all messages into a single prompt
            openai_messages = [
                cast(
                    ChatCompletionMessageParam,
                    {"role": msg.role, "content": msg.content},
                )
                for msg in messages
            ]

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

                # Get response content
                choices = response.choices
                if not choices:
                    await progress.stop("Failed")
                    raise ValueError("Empty response from OpenAI")

                content = choices[0].message.content
                if not content:
                    await progress.stop("Failed")
                    raise ValueError("Empty message content from OpenAI")

                await progress.stop("Complete")
                return str(content)

            except OpenAIError as e:
                logger.error("OpenAI API error: %s", str(e))
                await progress.stop("Failed")
                raise ValueError(f"OpenAI API error: {str(e)}")

            except Exception as e:
                logger.error("Error during API request: %s", str(e))
                await progress.stop("Failed")
                if isinstance(e, ValueError):
                    raise
                raise ValueError(f"Unexpected error: {str(e)}")

        except Exception as e:
            logger.error("Error in OpenAI _send_request: %s", str(e))
            raise
