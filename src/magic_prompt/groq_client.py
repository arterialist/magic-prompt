"""Groq API client for streaming completions."""

import os
from collections.abc import AsyncGenerator
from typing import Callable

from groq import AsyncGroq, Groq


class GroqClient:
    """Wrapper for Groq API with streaming support."""

    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(self, api_key: str | None = None):
        """
        Initialize the Groq client.

        Args:
            api_key: Optional API key. If not provided, uses GROQ_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not provided and not found in environment")

        self._client = AsyncGroq(api_key=self.api_key)
        self._sync_client = Groq(api_key=self.api_key)

    async def stream_completion(
        self,
        system_prompt: str,
        user_message: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        log_callback: Callable[[str], None] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat completion from Groq.

        Args:
            system_prompt: System message for context
            user_message: User's prompt to enrich
            model: Model to use (defaults to llama-3.3-70b-versatile)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            log_callback: Optional callback for logging

        Yields:
            Chunks of the completion as they arrive
        """
        model = model or self.DEFAULT_MODEL

        def log(msg: str) -> None:
            if log_callback:
                log_callback(msg)

        log(f"Calling Groq API (model: {model})...")

        try:
            stream = await self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            log("Completion finished")

        except Exception as e:
            log(f"Error: {e}")
            raise

    def test_connection(self) -> bool:
        """Test the API connection with a minimal request."""
        try:
            response = self._sync_client.chat.completions.create(
                model=self.DEFAULT_MODEL,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
            )
            return bool(response.choices)
        except Exception:
            return False
