"""Gemini provider implementation."""

# mypy: ignore-errors

import asyncio
import logging
from typing import Any, cast

import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse

from ..utils.progress import ProgressTracker
from ..utils.token_counter import count_tokens
from .base_provider import BaseProvider, Message, ProviderConfig

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """Google Gemini provider implementation."""

    name = "gemini"
    default_model = "gemini-2.0-flash-exp"
    model: Any = None

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize Gemini provider."""
        super().__init__(config=config)
        logger.info("Initializing Gemini provider")
        logger.info(
            "API key from config: %s",
            (self.config.api_key[:10] + "..." if self.config.api_key else "None"),
        )
        logger.info("Model from config: %s", self.config.model or self.default_model)

        logger.info("Configuring Gemini with API key")
        genai.configure(api_key=self.config.api_key)

        logger.info("Creating GenerativeModel instance")
        model_name = self.config.model or self.default_model
        self.model = genai.GenerativeModel(model_name)
        logger.info("GenerativeModel instance created with model: %s", model_name)

    def count_tokens(self, content: str) -> int:
        """Count tokens in content.

        Args:
            content: Text content to count tokens for

        Returns:
            Number of tokens in content
        """
        return count_tokens(content, self.config.model, "cl100k_base")

    async def analyze(self, content: str) -> str:
        """Analyze code using Google Gemini API."""
        logger.info(
            "Starting Gemini analysis: model=%s, content_length=%d",
            self.config.model or self.default_model,
            len(content),
        )

        messages = self._prepare_messages(content)
        return await self._send_request(messages)

    async def _send_request(self, messages: list[Message]) -> str:
        """Send request to Gemini API."""
        try:
            # Combine all messages into a single prompt
            prompt = " ".join(msg.content for msg in messages)
            content_length = len(prompt)
            logger.debug("Prompt length: %d", content_length)

            # Create progress tracker with content length for adaptive timing
            progress = ProgressTracker(
                prefix="[AI Analysis]",
                content_length=content_length,
                total_steps=100,  # Use 100 steps for smoother progress
            )
            await progress.start()

            try:
                # Make request with timeout from config
                logger.debug("Sending request to Gemini API")
                timeout_seconds = self.config.timeout_ms / 1000
                response = await asyncio.wait_for(
                    self.model.generate_content_async(prompt),
                    timeout=timeout_seconds,
                )
                response = cast(GenerateContentResponse, response)
                text = str(response.text)
                await progress.stop("Complete")

                logger.debug("Response length: %d", len(text))
                return text

            except asyncio.TimeoutError:
                await progress.stop("Timeout")
                timeout_minutes = self.config.timeout_ms / 60000
                logger.error("Request timed out after %.1f minutes", timeout_minutes)
                raise ValueError(
                    f"Request timed out after {timeout_minutes:.1f} minutes"
                )

            except Exception as e:
                await progress.stop("Failed")
                raise e

        except Exception as e:
            logger.error("Error in Gemini _send_request: %s", str(e))
            raise
