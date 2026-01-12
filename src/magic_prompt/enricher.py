"""Prompt enrichment logic combining project context with LLM."""

from collections.abc import AsyncGenerator
from typing import Callable

from .groq_client import GroqClient
from .scanner import ProjectContext


SYSTEM_PROMPT_TEMPLATE = """You are a precise, technical prompt engineer. Your job is to transform short user prompts into detailed, accurate prompts that reference the ACTUAL codebase structure provided below.

{project_context}

---

## Your Task

Transform the user's vague prompt into a precise, actionable request. Follow these rules:

### CRITICAL: Be Accurate
- ONLY reference files, directories, classes, and functions that ACTUALLY EXIST in the project context above
- Do NOT invent or assume file names, directories, or APIs that aren't shown
- If the project context doesn't show relevant files, acknowledge this limitation
- Check the file tree and signatures carefully before referencing anything

### Structure the Output
1. Start with a clear statement of the goal
2. List specific files to modify (only if they exist in the context)
3. Describe the changes needed in each file
4. Include relevant technical details from the imports and APIs shown
5. Define acceptance criteria

### What NOT to do
- Don't invent file names or paths not shown in the project
- Don't assume frameworks or libraries not visible in imports
- Don't add unnecessary complexity beyond what the user requested
- Don't include preamble or meta-commentary about the enrichment

Output ONLY the enriched prompt."""


class PromptEnricher:
    """Enriches user prompts using project context and LLM."""

    def __init__(self, groq_client: GroqClient, project_context: ProjectContext):
        """
        Initialize the enricher.

        Args:
            groq_client: Initialized Groq API client
            project_context: Scanned project context
        """
        self.client = groq_client
        self.context = project_context
        self._system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            project_context=project_context.to_prompt_context()
        )

    async def enrich(
        self,
        user_prompt: str,
        log_callback: Callable[[str], None] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Enrich a user prompt with project context.

        Args:
            user_prompt: The short/vague prompt from the user
            log_callback: Optional callback for logging

        Yields:
            Chunks of the enriched prompt as they stream
        """

        def log(msg: str) -> None:
            if log_callback:
                log_callback(msg)

        log(f"Enriching prompt: '{user_prompt[:50]}...'")

        user_message = f"""Transform this prompt into a detailed, accurate request:

"{user_prompt}"

Requirements:
- Reference ONLY files and functions that appear in the project context
- If you need to suggest creating new files, clearly mark them as NEW
- Use the actual directory structure shown, not assumed paths
- Keep the enriched prompt focused on what the user actually asked for"""

        async for chunk in self.client.stream_completion(
            system_prompt=self._system_prompt,
            user_message=user_message,
            log_callback=log_callback,
        ):
            yield chunk
