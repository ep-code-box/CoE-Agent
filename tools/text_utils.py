"""Utility helpers for post-processing text responses."""
from __future__ import annotations

import textwrap


def synthesize_answer(query: str, snippets: list[str]) -> str:
    """Generate a concise answer leveraging the retrieved snippets."""

    if not snippets:
        return "No supporting documents were located. Please provide additional detail."

    teaser = snippets[0].strip()
    remaining = " ".join(snippet.strip() for snippet in snippets[1:])
    combined = f"Question: {query}\nContext: {teaser} {remaining}".strip()
    return textwrap.shorten(combined, width=320, placeholder=" ...")
