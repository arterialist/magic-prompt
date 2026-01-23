"""Smart retrieval for relevant files using TF-IDF and heuristics."""

import math
import re
import time
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .scanner import FileSignature


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words."""
    return re.findall(r"\w+", text.lower())


def calculate_keyword_score(sig: "FileSignature", query: str) -> float:
    """
    Score a file based on keyword overlap with the query in path and content.

    Args:
        sig: FileSignature object.
        query: User's prompt/query.

    Returns:
        A score between 0 and 1.
    """
    query_tokens = set(tokenize(query))
    if not query_tokens:
        return 0.0

    # Tokenize full path for standard matching
    path_tokens = set(tokenize(sig.path))

    # Also split by separator to identify explicit directory names
    path_segments = set(p.lower() for p in sig.path.split("/"))

    # Tokenize content (classes + functions)
    content_text = " ".join(sig.classes + sig.functions)
    content_tokens = set(tokenize(content_text))

    score = 0.0
    for token in query_tokens:
        # Check against path identifiers (highest weight)
        if token in path_segments:
            score += 3.0
        elif token + "s" in path_segments or (
            token.endswith("s") and token[:-1] in path_segments
        ):
            score += 2.5  # Plural/Singular match on distinct segment

        # Check against standard path tokens
        elif token in path_tokens:
            score += 1.0

        # Check against content (high weight)
        elif token in content_tokens:
            score += 2.0
        # Partial match in content (e.g. "connect" in "handleConnectOAuth")
        elif any(token in t for t in content_tokens):
            score += 1.0

    # Normalize score
    # Max possible score per token is ~3.0. We normalize by query length.
    normalized_score = score / (len(query_tokens) * 3.0)

    return min(normalized_score, 1.0)


def calculate_recency_score(
    file_path: str, root_path: str, max_age_days: int = 30
) -> float:
    """
    Score a file based on how recently it was modified.

    Args:
        file_path: Relative path to file.
        root_path: Project root directory.
        max_age_days: Files older than this get score 0.

    Returns:
        A score between 0 and 1.
    """
    try:
        full_path = Path(root_path) / file_path
        mtime = full_path.stat().st_mtime
        age_seconds = time.time() - mtime
        age_days = age_seconds / 86400

        if age_days >= max_age_days:
            return 0.0

        return 1.0 - (age_days / max_age_days)
    except (OSError, FileNotFoundError):
        return 0.0


def calculate_heuristic_score(
    sig: "FileSignature", query: str, root_path: str
) -> float:
    """
    Calculate combined heuristic relevance score.

    Args:
        sig: FileSignature object.
        query: User's prompt.
        root_path: Project root directory.

    Returns:
        Combined score between 0 and 1.
    """
    keyword_score = calculate_keyword_score(sig, query)
    recency_score = calculate_recency_score(sig.path, root_path)

    return keyword_score * 0.8 + recency_score * 0.2


def score_and_sort_signatures(
    signatures: list["FileSignature"],
    query: str,
    root_path: str,
) -> list["FileSignature"]:
    """
    Score and sort signatures by heuristic relevance.

    Args:
        signatures: List of FileSignature objects.
        query: User's prompt.
        root_path: Project root directory.

    Returns:
        Sorted list of FileSignature objects (highest relevance first).
    """
    if not query:
        return signatures

    scored = []
    for sig in signatures:
        score = calculate_heuristic_score(sig, query, root_path)
        scored.append((score, sig))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [sig for _, sig in scored]


class TfidfRetriever:
    """TF-IDF based retriever using pure Python (no external dependencies)."""

    def __init__(self):
        """Initialize the TF-IDF retriever."""
        self._idf: dict[str, float] = {}
        self._doc_count = 0

    def _signature_to_text(self, sig: "FileSignature") -> str:
        """Convert a FileSignature to searchable text."""
        parts = [sig.path]
        if sig.docstring:
            parts.append(sig.docstring)
        if sig.classes:
            parts.extend(sig.classes)
        if sig.functions:
            parts.extend(sig.functions)
        return " ".join(parts)

    def _compute_tf(self, tokens: list[str]) -> dict[str, float]:
        """Compute term frequency for a document."""
        if not tokens:
            return {}
        counts = Counter(tokens)
        total = len(tokens)
        return {term: count / total for term, count in counts.items()}

    def _compute_idf(self, documents: list[list[str]]) -> dict[str, float]:
        """Compute inverse document frequency across all documents."""
        doc_count = len(documents)
        if doc_count == 0:
            return {}

        # Count how many documents contain each term
        term_doc_counts: dict[str, int] = {}
        for doc in documents:
            unique_terms = set(doc)
            for term in unique_terms:
                term_doc_counts[term] = term_doc_counts.get(term, 0) + 1

        # Compute IDF: log(N / (1 + df)) to avoid division by zero
        idf = {}
        for term, df in term_doc_counts.items():
            idf[term] = math.log(doc_count / (1 + df))

        return idf

    def _compute_tfidf_vector(
        self, tokens: list[str], idf: dict[str, float]
    ) -> dict[str, float]:
        """Compute TF-IDF vector for a document."""
        tf = self._compute_tf(tokens)
        return {term: tf_val * idf.get(term, 0) for term, tf_val in tf.items()}

    def _cosine_similarity(
        self, vec1: dict[str, float], vec2: dict[str, float]
    ) -> float:
        """Compute cosine similarity between two sparse vectors."""
        # Get all terms
        all_terms = set(vec1.keys()) | set(vec2.keys())
        if not all_terms:
            return 0.0

        # Dot product
        dot = sum(vec1.get(t, 0) * vec2.get(t, 0) for t in all_terms)

        # Magnitudes
        mag1 = math.sqrt(sum(v * v for v in vec1.values()))
        mag2 = math.sqrt(sum(v * v for v in vec2.values()))

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return dot / (mag1 * mag2)

    def retrieve(
        self,
        query: str,
        candidates: list["FileSignature"],
        root_path: str = "",
        top_k: int = 30,
        log_callback=None,
    ) -> list["FileSignature"]:
        """
        Retrieve the most relevant file signatures using Hybrid TF-IDF + Heuristic.

        Args:
            query: User's prompt/query.
            candidates: List of FileSignature objects to search.
            root_path: Project root directory (needed for heuristic).
            top_k: Number of top results to return.
            log_callback: Optional logging callback.

        Returns:
            Top-k most relevant FileSignature objects.
        """
        if not candidates:
            return []

        if len(candidates) <= top_k:
            return candidates

        def log(msg: str) -> None:
            if log_callback:
                log_callback(msg)

        log(f"Computing Hybrid relevance for {len(candidates)} files...")

        # Tokenize all documents
        doc_tokens = [tokenize(self._signature_to_text(sig)) for sig in candidates]
        query_tokens = tokenize(query)

        # Compute IDF across all documents + query
        all_docs = doc_tokens + [query_tokens]
        idf = self._compute_idf(all_docs)

        # Compute TF-IDF vectors
        query_vector = self._compute_tfidf_vector(query_tokens, idf)

        # Compute similarities
        scored = []
        for i, doc_toks in enumerate(doc_tokens):
            # 1. TF-IDF Score
            doc_vector = self._compute_tfidf_vector(doc_toks, idf)
            tfidf_score = self._cosine_similarity(query_vector, doc_vector)

            # 2. Heuristic Score (only if root_path available, otherwise 0)
            heuristic_score = 0.0
            if root_path:
                heuristic_score = calculate_heuristic_score(
                    candidates[i], query, root_path
                )

            # 3. Hybrid Blend
            # We weight heuristic very heavily (0.95) to prioritize structural matches
            # (path segments, function names) over raw keyword density which favors small files.
            final_score = (tfidf_score * 0.05) + (heuristic_score * 0.95)
            candidates[i]._debug_score = final_score

            scored.append((final_score, candidates[i]))

        # Sort by similarity (descending) and get top-k
        scored.sort(key=lambda x: x[0], reverse=True)
        top_results = [sig for _, sig in scored[:top_k]]

        log(f"Selected top {top_k} files by Hybrid relevance.")

        return top_results


# Alias for backward compatibility
EmbeddingRetriever = TfidfRetriever
