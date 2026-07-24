"""Request/response models — rich on purpose: the responses ARE the lesson."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Strategy = Literal["static", "dynamic", "sentence", "semantic"]


# --- chunking -----------------------------------------------------------------
class ChunkRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{
        "text": "Libra Bank blocks a card after three failed PIN attempts. "
                "A blocked card can be unblocked in the branch after identity verification. "
                "Mortgage early repayment is free of charge in the variable-rate period.",
        "strategy": "dynamic",
        "chunk_size": 120,
        "chunk_overlap": 30,
    }]}}

    text: str = Field(..., description="Raw text to split", min_length=1)
    strategy: Optional[Strategy] = Field(None, description="Defaults to CHUNK_STRATEGY from .env")
    chunk_size: Optional[int] = Field(None, ge=50, description="Target size, characters (≥ 50)")
    chunk_overlap: Optional[int] = Field(None, ge=0, description="Overlap, characters")
    sentences_per_chunk: Optional[int] = Field(None, ge=1, description="'sentence' strategy only")
    semantic_threshold: Optional[float] = Field(None, gt=0, le=1, description="'semantic' strategy only — 0 < t ≤ 1")


class ChunkInfo(BaseModel):
    index: int
    text: str
    chars: int
    approx_tokens: int = Field(description="chars / 4 — a rough but honest estimate")


class ChunkResponse(BaseModel):
    strategy: Strategy
    params_used: dict
    count: int
    chunks: list[ChunkInfo]


# --- ingestion ----------------------------------------------------------------
class IngestRequest(ChunkRequest):
    model_config = {"json_schema_extra": {"examples": [{
        "text": "Libra Bank blocks a card after three failed PIN attempts. "
                "A blocked card can be unblocked in the branch after identity verification. "
                "Mortgage early repayment is free of charge in the variable-rate period.",
        "strategy": "dynamic",
        "source": "retail-faq",
    }]}}

    source: Optional[str] = Field(None, description="Label stored with every chunk (e.g. 'cards-faq')")


class IngestResponse(BaseModel):
    strategy: Strategy
    count: int
    vector_dimension: int
    embedding_preview: list[float] = Field(description="First 8 dimensions of chunk #0 — meaning as numbers")
    embedding_model: dict
    point_ids: list[str]
    chunks: list[ChunkInfo]


# --- retrieval ----------------------------------------------------------------
class SearchRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{
        "query": "my card got frozen, what do I do?",
        "top_k": 3,
    }]}}

    query: str = Field(..., min_length=1)
    top_k: Optional[int] = Field(None, ge=1, le=50)


class SearchHit(BaseModel):
    score: float = Field(description="Cosine similarity — 1.0 is identical direction")
    text: str
    index: Optional[int] = None
    strategy: Optional[str] = None
    source: Optional[str] = None
    id: str


class SearchResponse(BaseModel):
    query: str
    top_k: int
    embedding_model: dict
    query_embedding_preview: list[float]
    hits: list[SearchHit]


# --- generation ---------------------------------------------------------------
class AskRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{
        "question": "What fee does Libra Bank charge for early mortgage repayment?",
        "use_rag": True,
        "top_k": 3,
    }]}}

    question: str = Field(..., min_length=1)
    use_rag: bool = Field(True, description="false = plain LLM; true = retrieve then augment")
    top_k: Optional[int] = Field(None, ge=1, le=50)
    temperature: Optional[float] = Field(None, ge=0, le=2)


class Usage(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class AskResponse(BaseModel):
    answer: str
    augmented: bool
    provider: str
    model: str
    system_prompt: str = Field(description="The system message actually sent")
    prompt_sent: str = Field(description="The exact user prompt sent to the model — compare with/without RAG")
    retrieved: list[SearchHit] = Field(default_factory=list)
    usage: Optional[Usage] = None


# --- ops ----------------------------------------------------------------------
class CollectionInfo(BaseModel):
    exists: bool
    name: str
    points_count: int
    vector_dimension: Optional[int] = None
    distance: Optional[str] = None


class Health(BaseModel):
    status: str
    qdrant: str
    qdrant_url: str
    llm: dict
    embeddings: dict
