"""04 · Meaning as geometry — cosine similarity between phrases.

Four phrases, one matrix. Predict which pair wins before the numbers print.

    uv run python examples/04_embeddings.py
"""
from __future__ import annotations

import math

from _bootstrap import banner, show_context
from app.embeddings import get_embedder

banner("04 · embeddings: meaning becomes numbers")
show_context()

PHRASES = [
    "my card is blocked",
    "frozen debit card",
    "mortgage interest rate",
    "the weather in Cluj",
]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


embedder = get_embedder()
vectors = embedder.embed(PHRASES)

print(f"\nmodel      : {embedder.model}")
print(f"dimensions : {len(vectors[0])}")
print(f"first 8    : {[round(x, 5) for x in vectors[0][:8]]}\n")

print("cosine similarity — 1.0 means identical direction:\n")
width = max(len(p) for p in PHRASES)
print(" " * (width + 2) + "  ".join(f"{i:>6}" for i in range(len(PHRASES))))
for i, phrase in enumerate(PHRASES):
    row = "  ".join(f"{cosine(vectors[i], vectors[j]):>6.3f}" for j in range(len(PHRASES)))
    print(f"{i} {phrase:<{width}}  {row}")

best = max(
    ((i, j) for i in range(len(PHRASES)) for j in range(i + 1, len(PHRASES))),
    key=lambda p: cosine(vectors[p[0]], vectors[p[1]]),
)
print(f"\nclosest pair: '{PHRASES[best[0]]}' ↔ '{PHRASES[best[1]]}'")
print("They share almost no words — yet they are neighbours. That property is the")
print("entire engine behind semantic search, and therefore behind RAG.")
