"""Groq API client for streaming completions."""

import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Callable

from groq import AsyncGroq, Groq


@dataclass
class TokenUsage:
    """Token usage statistics from API call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class GroqClient:
    """Wrapper for Groq API with streaming support."""

    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        """
        Initialize the Groq client.

        Args:
            api_key: Optional API key. If not provided, uses GROQ_API_KEY env var.
            model: Optional model name. Defaults to llama-3.3-70b-versatile.
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not provided and not found in environment")

        self.model = model or self.DEFAULT_MODEL
        self._client = AsyncGroq(api_key=self.api_key)
        self._sync_client = Groq(api_key=self.api_key)

        # Token usage tracking
        self.last_usage: TokenUsage | None = None
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_requests: int = 0

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
        model = model or self.model

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

                # Capture usage from final chunk
                if chunk.usage:
                    self.last_usage = TokenUsage(
                        prompt_tokens=chunk.usage.prompt_tokens,
                        completion_tokens=chunk.usage.completion_tokens,
                        total_tokens=chunk.usage.total_tokens,
                    )
                    self.total_prompt_tokens += chunk.usage.prompt_tokens
                    self.total_completion_tokens += chunk.usage.completion_tokens
                    self.total_requests += 1
                    log(
                        f"Tokens: {chunk.usage.total_tokens} (prompt: {chunk.usage.prompt_tokens}, completion: {chunk.usage.completion_tokens})"
                    )

            log("Completion finished")

        except Exception as e:
            log(f"Error: {e}")
            raise

    def get_session_stats(self) -> str:
        """Get formatted session statistics."""
        total = self.total_prompt_tokens + self.total_completion_tokens
        return f"Session: {self.total_requests} requests, {total} tokens"

    def test_connection(self) -> bool:
        """Test the API connection with a minimal request."""
        try:
            response = self._sync_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
            )
            return bool(response.choices)
        except Exception:
            return False

    def get_available_models(self) -> list[str]:
        """
        Fetch available models from Groq API.

        Returns:
            List of model IDs. Returns empty list on error.
        """
        try:
            models = self._sync_client.models.list()
            return [m.id for m in models.data]
        except Exception as e:
            # Fallback to default if API fails
            print(f"Error fetching models: {e}")
            return []
