"""Request/response models — rich on purpose: the responses ARE the lesson."""
from __future__ import annotations

from typing import Literal, Optional  # noqa: F401  (Literal used by AskRequest)

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
    title: Optional[str] = Field(None, description="Document title, from the corpus front-matter")
    product: Optional[str] = Field(None, description="e.g. 'cards', 'mortgages', 'accounts'")
    audience: Optional[str] = Field(None, description="e.g. 'retail', 'business'")
    effective: Optional[str] = Field(None, description="Effective date, e.g. '2026-01-01'")
    version: Optional[str] = Field(None, description="Document version, e.g. '2'")


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
    score_threshold: Optional[float] = Field(
        None, ge=0, le=1,
        description="Drop hits scoring below this cosine similarity — weak matches are "
                    "omitted instead of being returned as if they were relevant",
    )
    product: Optional[str] = Field(None, description="Filter: only chunks with this metadata product")
    audience: Optional[str] = Field(None, description="Filter: only chunks with this metadata audience")
    effective: Optional[str] = Field(None, description="Filter: only chunks with this exact effective date")
    source: Optional[str] = Field(None, description="Filter: only chunks from this source")


class SearchHit(BaseModel):
    score: float = Field(description="Cosine similarity — 1.0 is identical direction")
    text: str
    index: Optional[int] = None
    strategy: Optional[str] = None
    source: Optional[str] = None
    title: Optional[str] = None
    product: Optional[str] = None
    audience: Optional[str] = None
    effective: Optional[str] = None
    version: Optional[str] = None
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
        "agent": "lyrical",
    }]}}

    question: str = Field(..., min_length=1)
    use_rag: bool = Field(True, description="false = plain LLM; true = retrieve then augment")
    top_k: Optional[int] = Field(None, ge=1, le=50)
    score_threshold: Optional[float] = Field(
        None, ge=0, le=1,
        description="Drop retrieved chunks below this cosine similarity before augmenting",
    )
    product: Optional[str] = Field(None, description="Filter retrieval to this metadata product")
    audience: Optional[str] = Field(None, description="Filter retrieval to this metadata audience")
    effective: Optional[str] = Field(None, description="Filter retrieval to this exact effective date")
    source: Optional[str] = Field(None, description="Filter retrieval to this source")
    temperature: Optional[float] = Field(None, ge=0, le=2)
    agent: Optional[str] = Field(
        None,
        description="Persona name from app/agents/personas/ — try 'default', 'lyrical', "
                    "'compliance', 'teller'. Falls back to AGENT_PERSONA in .env.",
    )
    agent_mode: Optional[Literal["local", "foundry"]] = Field(
        None, description="local = the loop runs here; foundry = the hosted Agent Service"
    )


class AgentInfo(BaseModel):
    name: str
    display_name: str
    description: str
    mode: str = Field(description="Where this run executed: local or foundry")
    temperature: Optional[float] = None
    style_rules: list[str] = Field(default_factory=list)


class HostedAgent(BaseModel):
    agent_id: str
    name: str
    model: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[int] = None
    instructions_preview: Optional[str] = None


class PersonaSummary(BaseModel):
    name: str
    display_name: str
    description: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    style_rules: list[str] = Field(default_factory=list)
    require_citations: bool = True
    refuse_when_unsupported: bool = True
    reasoning_effort: Optional[str] = None
    tools: list[str] = Field(default_factory=list)
    default_product: Optional[str] = Field(
        None, description="When set, /ask scopes retrieval to this metadata `product` unless the request overrides it"
    )
    runs_on: Literal["local", "both", "foundry", "unknown"] = Field(
        "local",
        description="local = JSON file only · both = also hosted in Foundry · "
                    "foundry = hosted only, no local file · unknown = cannot ask Foundry",
    )
    hosted: Optional[HostedAgent] = None


class FoundryAvailability(BaseModel):
    available: bool
    reason: Optional[str] = Field(
        None, description="Why the Agent Service could not be queried, when it could not"
    )


class AgentListResponse(BaseModel):
    active_mode: str
    default_persona: str
    personas_dir: str
    count: int
    personas: list[PersonaSummary]
    foundry: FoundryAvailability
    hosted_only: list[PersonaSummary] = Field(
        default_factory=list,
        description="Agents that exist in Foundry with no local persona file — "
                    "created in the portal, or from a file since deleted",
    )


class AzureDeployment(BaseModel):
    name: str
    model: Optional[str] = None
    version: Optional[str] = None
    sku: Optional[str] = None
    capacity: Optional[int] = None
    state: Optional[str] = None


class AzureDeployments(BaseModel):
    available: bool
    reason: Optional[str] = None
    items: list[AzureDeployment] = Field(default_factory=list)


class AzureStatus(BaseModel):
    configured: bool
    auth: str = Field(description="identity (Entra) or key")
    auth_note: Optional[str] = None
    resource: Optional[str] = None
    resource_group: Optional[str] = None
    project: Optional[str] = None
    location: Optional[str] = None
    subscription_id: Optional[str] = None
    inference_endpoint: Optional[str] = None
    project_endpoint: Optional[str] = None
    openai_endpoint: Optional[str] = None
    chat_deployment: Optional[str] = None
    embedding_deployment: Optional[str] = None
    foundry_url: Optional[str] = None
    portal_url: Optional[str] = None
    deployments: AzureDeployments


class Usage(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class AskResponse(BaseModel):
    answer: str
    augmented: bool
    provider: str
    model: str
    agent: Optional[AgentInfo] = Field(None, description="Which persona shaped this answer")
    system_prompt: str = Field(description="The system message actually sent")
    prompt_sent: str = Field(description="The exact user prompt sent to the model — compare with/without RAG")
    retrieved: list[SearchHit] = Field(default_factory=list)
    product_filter: Optional[str] = Field(
        None, description="The `product` filter actually applied to retrieval — from the request, "
                          "or from the persona's `default_product` when the request left it unset"
    )
    nothing_relevant: bool = Field(
        False,
        description="true when use_rag was on but every hit fell below score_threshold, or the "
                    "filter matched nothing — the model was not called with weak/no context",
    )
    usage: Optional[Usage] = None


# --- tools / services ---------------------------------------------------------
class ScrapeRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{
        "url": "https://learn.microsoft.com/azure/ai-foundry/what-is-azure-ai-foundry",
    }]}}

    url: str = Field(..., description="Page to fetch and strip to text")
    max_chars: Optional[int] = Field(None, ge=200, le=200000)


class ScrapeResponse(BaseModel):
    url: str
    status_code: int
    title: Optional[str] = None
    text: str
    chars: int
    approx_tokens: int
    warnings: list[str] = Field(description="Everything the naive approach could not handle")
    stats: dict


class SpeakRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{
        "text": "Your card was blocked after three failed PIN attempts.",
    }]}}

    text: str = Field(..., min_length=1, max_length=3000)
    voice: Optional[str] = Field(None, description="Neural voice name; defaults to AZURE_SPEECH_VOICE")


class TranscribeResponse(BaseModel):
    status: Optional[str] = None
    text: str
    confidence: Optional[float] = None
    duration_seconds: Optional[float] = None
    language: Optional[str] = None


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
    agents: dict = Field(default_factory=dict)
    speech: dict = Field(default_factory=dict)
