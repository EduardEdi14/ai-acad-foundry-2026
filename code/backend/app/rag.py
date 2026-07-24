"""Prompt assembly — the heart of the 'augmented' in RAG, kept fully visible.

The /ask endpoint returns the exact prompt produced here, so the difference
between a plain question and an augmented one is inspectable in Postman.
"""
from __future__ import annotations

SYSTEM_PROMPT = (
    "You are Libra Assist, the internal AI assistant of a retail bank. "
    "Answer precisely and professionally, in English."
)

SYSTEM_PROMPT_RAG = SYSTEM_PROMPT + (
    " Ground every answer in the CONTEXT passages provided. If the context does not "
    "contain the information needed, say so explicitly instead of guessing. "
    "Reference passages as [1], [2], … when you use them."
)


def build_augmented_prompt(question: str, chunks: list[dict]) -> str:
    """Question + retrieved passages -> the final user prompt sent to the model."""
    context = "\n\n".join(
        f"[{i + 1}] (score {c['score']}) {c['text']}" for i, c in enumerate(chunks)
    )
    return (
        "CONTEXT — retrieved passages, most similar first:\n"
        f"{context}\n\n"
        "QUESTION:\n"
        f"{question}"
    )
