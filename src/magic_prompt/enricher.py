"""Prompt enrichment logic combining project context with LLM."""

from collections.abc import AsyncGenerator
from typing import Callable

from .groq_client import GroqClient
from .scanner import ProjectContext
from .retriever import TfidfRetriever, score_and_sort_signatures
from .modes.pseudocode import (
    PSEUDOCODE_SYSTEM_PROMPT_TEMPLATE,
    PSEUDOCODE_USER_TEMPLATE,
)
from .modes.elaboration import (
    ELABORATION_SYSTEM_PROMPT_TEMPLATE,
    ELABORATION_USER_TEMPLATE,
)


STANDARD_SYSTEM_PROMPT_TEMPLATE = """You are a precise, technical prompt engineer. Your job is to transform short user prompts into detailed, accurate prompts that reference the ACTUAL codebase structure provided below.

{project_context}

---

## Your Task

Transform the user's vague prompt into a precise, actionable request. Follow these rules:

### CRITICAL: File Relevance Scores
- Files are listed with relevance percentages (e.g., `[95% relevant]`) based on their match to the user's query
- **PRIORITIZE files with higher relevance scores** when suggesting modifications
- Files with scores ≥80% are highly likely to be directly relevant
- Files with scores 50-79% may contain supporting code
- Files with scores <50% are context-only and should rarely be primary targets

### CRITICAL: Be Accurate
- ONLY reference files, directories, classes, and functions that ACTUALLY EXIST in the project context above
- Do NOT invent or assume file names, directories, or APIs that aren't shown
- If the project context doesn't show relevant files, acknowledge this limitation
- Check the file tree and signatures carefully before referencing anything

### Structure the Output
1. Start with a clear statement of the goal
2. List specific files to modify, **prioritizing those with higher relevance scores**
3. Describe the changes needed in each file
4. Include relevant technical details from the imports and APIs shown
5. Define acceptance criteria

### What NOT to do
- Don't invent file names or paths not shown in the project
- Don't assume frameworks or libraries not visible in imports
- Don't add unnecessary complexity beyond what the user requested
- Don't include preamble or meta-commentary about the enrichment
- Don't focus on low-relevance files when high-relevance alternatives exist

Output ONLY the enriched prompt."""

STANDARD_USER_TEMPLATE = """Transform this prompt into a detailed, accurate request:

"{user_prompt}"

Requirements:
- Reference ONLY files and functions that appear in the project context
- If you need to suggest creating new files, clearly mark them as NEW
- Use the actual directory structure shown, not assumed paths
- Keep the enriched prompt focused on what the user actually asked for"""


class PromptEnricher:
    """Enriches user prompts using project context and LLM."""

    def __init__(
        self,
        groq_client: GroqClient,
        project_context: ProjectContext,
        mode: str = "standard",
        retrieval_mode: str = "tfidf",
        top_k: int = 100,
    ):
        """
        Initialize the enricher.

        Args:
            groq_client: Initialized Groq API client
            project_context: Scanned project context
            mode: Enrichment mode (standard, pseudocode, elaboration)
            retrieval_mode: How to filter files - "tfidf", "heuristic", or "none"
            top_k: Number of top files to include after retrieval (ignored if retrieval_mode="none")
        """
        self.client = groq_client
        self.context = project_context
        self.mode = mode
        self.retrieval_mode = retrieval_mode
        self.top_k = top_k
        self._retriever: TfidfRetriever | None = None

        # Select templates based on mode
        if mode == "pseudocode":
            self._system_template = PSEUDOCODE_SYSTEM_PROMPT_TEMPLATE
            self._user_template = PSEUDOCODE_USER_TEMPLATE
        elif mode == "elaboration":
            self._system_template = ELABORATION_SYSTEM_PROMPT_TEMPLATE
            self._user_template = ELABORATION_USER_TEMPLATE
        else:
            self._system_template = STANDARD_SYSTEM_PROMPT_TEMPLATE
            self._user_template = STANDARD_USER_TEMPLATE

    def _get_retriever(self) -> TfidfRetriever:
        """Lazy-load the TF-IDF retriever."""
        if self._retriever is None:
            self._retriever = TfidfRetriever()
        return self._retriever

    def _build_filtered_context(
        self,
        user_prompt: str,
        log_callback: Callable[[str], None] | None = None,
    ) -> ProjectContext:
        """
        Build a filtered ProjectContext based on query relevance.

        Args:
            user_prompt: The user's query.
            log_callback: Optional logging callback.

        Returns:
            A new ProjectContext with filtered signatures.
        """

        def log(msg: str) -> None:
            if log_callback:
                log_callback(msg)

        original_count = len(self.context.signatures)

        # Mode: none - include all files (no filtering)
        if self.retrieval_mode == "none":
            log(f"Retrieval mode: none. Including all {original_count} files.")
            return self.context

        # Step 1: Heuristic sorting (always applied for tfidf and heuristic modes)
        log(f"Scoring {original_count} files by relevance...")
        sorted_sigs = score_and_sort_signatures(
            self.context.signatures,
            user_prompt,
            self.context.root_path,
        )

        # Mode: heuristic - just use sorted top_k
        if self.retrieval_mode == "heuristic":
            if len(sorted_sigs) > self.top_k:
                filtered_sigs = sorted_sigs[: self.top_k]
                log(f"Selected top {self.top_k} files by heuristic scoring.")
            else:
                filtered_sigs = sorted_sigs
                log(f"Including all {len(filtered_sigs)} files (below top_k limit).")
        # Mode: tfidf - apply TF-IDF similarity on top of heuristic sorting
        elif self.retrieval_mode == "tfidf":
            if len(sorted_sigs) > self.top_k:
                retriever = self._get_retriever()
                filtered_sigs = retriever.retrieve(
                    user_prompt,
                    sorted_sigs,
                    root_path=self.context.root_path,
                    top_k=self.top_k,
                    log_callback=log_callback,
                )
            else:
                filtered_sigs = sorted_sigs
                log(f"Including all {len(filtered_sigs)} files (below top_k limit).")
        else:
            # Unknown mode, fall back to no filtering
            log(f"Unknown retrieval mode '{self.retrieval_mode}', including all files.")
            filtered_sigs = sorted_sigs

        log(f"Selected {len(filtered_sigs)} files from {original_count}.")

        # Create new context with filtered signatures
        return ProjectContext(
            root_path=self.context.root_path,
            file_tree=self.context.file_tree,
            config_files=self.context.config_files,
            signatures=filtered_sigs,
            total_files=self.context.total_files,
            total_dirs=self.context.total_dirs,
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

        log(
            f"Enriching prompt (mode: {self.mode}, retrieval: {self.retrieval_mode}): '{user_prompt[:50]}...'"
        )

        # Build filtered context based on the user's prompt
        filtered_context = self._build_filtered_context(user_prompt, log_callback)

        # Build the system prompt with the filtered context
        system_prompt = self._system_template.format(
            project_context=filtered_context.to_prompt_context()
        )

        user_message = self._user_template.format(user_prompt=user_prompt)

        async for chunk in self.client.stream_completion(
            system_prompt=system_prompt,
            user_message=user_message,
            log_callback=log_callback,
        ):
            yield chunk
