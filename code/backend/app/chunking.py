"""Chunking strategies — the first decision of every RAG pipeline, made visible.

Four strategies, deliberately spanning the sophistication spectrum:

  static    fixed character windows; cheap, ignores meaning (splits mid-sentence)
  sentence  groups of N sentences; trivially readable boundaries
  dynamic   structure-aware packing: paragraphs -> sentences packed to a size
            budget with overlap; never cuts inside a sentence unless forced
  semantic  sentence embeddings; a new chunk starts where adjacent cosine
            similarity drops below a threshold — meaning-aware, costs embeddings
"""
from __future__ import annotations

import math
import re
from typing import Callable

SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")
PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")

EmbedFn = Callable[[list[str]], list[list[float]]]


def split_sentences(text: str) -> list[str]:
    parts = [s.strip() for s in SENTENCE_END.split(text)]
    return [s for s in parts if s]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


# --- strategies ---------------------------------------------------------------

def chunk_static(text: str, size: int, overlap: int) -> list[str]:
    """Fixed windows over raw characters. The baseline that cuts words in half."""
    step = max(1, size - overlap)
    return [text[i : i + size].strip() for i in range(0, len(text), step) if text[i : i + size].strip()]


def chunk_sentence(text: str, per_chunk: int) -> list[str]:
    """Every N sentences become a chunk."""
    sentences = split_sentences(text)
    n = max(1, per_chunk)
    return [" ".join(sentences[i : i + n]) for i in range(0, len(sentences), n)]


def chunk_dynamic(text: str, size: int, overlap: int) -> list[str]:
    """Structure-aware packing: respect paragraphs, pack whole sentences up to
    `size` characters, carry a sentence-tail of ~`overlap` characters forward."""
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if current:
            chunks.append(" ".join(current))
            # overlap: keep trailing sentences up to `overlap` chars for continuity
            tail: list[str] = []
            tail_len = 0
            for s in reversed(current):
                if tail_len + len(s) > overlap:
                    break
                tail.insert(0, s)
                tail_len += len(s) + 1
            current = tail
            current_len = tail_len

    for paragraph in PARAGRAPH_SPLIT.split(text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        for sentence in split_sentences(paragraph):
            # a single sentence larger than the budget: hard-split as last resort
            if len(sentence) > size:
                flush()
                chunks.extend(chunk_static(sentence, size, overlap))
                current, current_len = [], 0
                continue
            if current_len + len(sentence) + 1 > size:
                flush()
            current.append(sentence)
            current_len += len(sentence) + 1
        # paragraph boundary is a natural flush point when near budget
        if current_len > size * 0.7:
            flush()
    if current:
        chunks.append(" ".join(current))
    # drop overlap-only remnants duplicating the previous chunk's tail
    return [c for i, c in enumerate(chunks) if not (i > 0 and c and c in chunks[i - 1])]


def chunk_semantic(text: str, threshold: float, embed_fn: EmbedFn) -> list[str]:
    """Embed every sentence; start a new chunk where the cosine similarity
    between neighbouring sentences falls below `threshold`."""
    sentences = split_sentences(text)
    if len(sentences) <= 1:
        return sentences
    vectors = embed_fn(sentences)
    chunks: list[list[str]] = [[sentences[0]]]
    for i in range(1, len(sentences)):
        if cosine(vectors[i - 1], vectors[i]) < threshold:
            chunks.append([sentences[i]])       # topic shift detected -> new chunk
        else:
            chunks[-1].append(sentences[i])
    return [" ".join(c) for c in chunks]


# --- dispatcher ---------------------------------------------------------------

STRATEGIES = ("static", "dynamic", "sentence", "semantic")


def chunk(
    text: str,
    strategy: str,
    *,
    size: int,
    overlap: int,
    per_chunk: int,
    threshold: float,
    embed_fn: EmbedFn | None = None,
) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if strategy == "static":
        return chunk_static(text, size, overlap)
    if strategy == "sentence":
        return chunk_sentence(text, per_chunk)
    if strategy == "dynamic":
        return chunk_dynamic(text, size, overlap)
    if strategy == "semantic":
        if embed_fn is None:
            raise ValueError("semantic chunking requires an embedding function")
        return chunk_semantic(text, threshold, embed_fn)
    raise ValueError(f"unknown strategy '{strategy}' — expected one of {STRATEGIES}")
