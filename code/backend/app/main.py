"""RAG Teaching API — every response exposes the pipeline's intermediate steps.

Demo order:  /health -> /chunk -> /ingest -> /collection -> /search -> /ask
Swagger UI:  /docs        ReDoc: /redoc
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import chunking, rag
from .config import settings
from .embeddings import get_embedder
from .llm import get_llm
from .schemas import (
    AskRequest, AskResponse, ChunkInfo, ChunkRequest, ChunkResponse, CollectionInfo,
    Health, IngestRequest, IngestResponse, SearchHit, SearchRequest, SearchResponse, Usage,
)
from .vectorstore import DimensionMismatch, VectorStore

app = FastAPI(
    title="RAG Teaching API",
    description=(
        "A backend built to *show* Retrieval-Augmented Generation, step by step: "
        "chunk text (four strategies), embed and store in Qdrant, retrieve with "
        "similarity scores, and answer with or without augmentation — the exact "
        "final prompt is always returned. Libra Bank Academy · AI Engineering on Azure."
    ),
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

store = VectorStore()


# --- helpers ------------------------------------------------------------------
def _chunk_params(req: ChunkRequest) -> dict:
    return {
        "strategy": (req.strategy or settings.chunk_strategy).lower(),
        "size": req.chunk_size or settings.chunk_size,
        "overlap": req.chunk_overlap if req.chunk_overlap is not None else settings.chunk_overlap,
        "per_chunk": req.sentences_per_chunk or settings.sentences_per_chunk,
        "threshold": req.semantic_threshold or settings.semantic_threshold,
    }


def _do_chunk(req: ChunkRequest) -> tuple[list[str], dict]:
    p = _chunk_params(req)
    embed_fn = None
    if p["strategy"] == "semantic":
        embed_fn = _embedder().embed
    try:
        pieces = chunking.chunk(
            req.text, p["strategy"], size=p["size"], overlap=p["overlap"],
            per_chunk=p["per_chunk"], threshold=p["threshold"], embed_fn=embed_fn,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return pieces, p


def _chunk_infos(pieces: list[str]) -> list[ChunkInfo]:
    return [
        ChunkInfo(index=i, text=t, chars=len(t), approx_tokens=max(1, round(len(t) / 4)))
        for i, t in enumerate(pieces)
    ]


def _embedder():
    try:
        return get_embedder()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Embedding provider not usable: {e}")


def _embed(texts: list[str]) -> list[list[float]]:
    try:
        return _embedder().embed(texts)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Embedding call failed ({settings.embedding_provider}): {e}",
        )


def _require_qdrant() -> None:
    if not store.ping():
        raise HTTPException(
            status_code=503,
            detail=f"Qdrant is not reachable at {settings.qdrant_url} — "
                   f"start it with: docker compose up qdrant -d",
        )


# --- ops ----------------------------------------------------------------------
@app.get("/health", response_model=Health, tags=["ops"])
def health() -> Health:
    return Health(
        status="ok",
        qdrant="ok" if store.ping() else "unreachable",
        qdrant_url=settings.qdrant_url,
        llm={"provider": settings.llm_provider,
             "model": {"lmstudio": settings.lmstudio_model, "openai": settings.openai_model,
                       "anthropic": settings.anthropic_model,
                       "azure": settings.azure_ai_chat_deployment}.get(settings.llm_provider, "?")},
        embeddings={"provider": settings.embedding_provider,
                    "model": {"lmstudio": settings.lmstudio_embedding_model,
                              "openai": settings.openai_embedding_model,
                              "azure": settings.azure_ai_embedding_deployment}.get(
                                  settings.embedding_provider, "?")},
    )


@app.get("/config", tags=["ops"])
def config() -> dict:
    def mask(v: str) -> str:
        return (v[:6] + "…" + v[-4:]) if len(v) > 12 else ("set" if v else "not set")

    return {
        "chunking": {"strategy": settings.chunk_strategy, "chunk_size": settings.chunk_size,
                     "chunk_overlap": settings.chunk_overlap,
                     "sentences_per_chunk": settings.sentences_per_chunk,
                     "semantic_threshold": settings.semantic_threshold},
        "retrieval": {"top_k": settings.top_k, "collection": settings.qdrant_collection,
                      "qdrant_url": settings.qdrant_url},
        "generation": {"provider": settings.llm_provider,
                       "temperature": settings.llm_temperature,
                       "max_tokens": settings.llm_max_tokens},
        "providers": {
            "lmstudio": {"base_url": settings.lmstudio_base_url, "model": settings.lmstudio_model,
                         "embedding_model": settings.lmstudio_embedding_model},
            "openai": {"api_key": mask(settings.openai_api_key), "model": settings.openai_model,
                       "embedding_model": settings.openai_embedding_model},
            "anthropic": {"api_key": mask(settings.anthropic_api_key),
                          "model": settings.anthropic_model},
            "azure": {"endpoint": settings.azure_ai_endpoint or "not set",
                      "auth": settings.azure_ai_auth,
                      "api_key": mask(settings.azure_ai_api_key),
                      "chat_deployment": settings.azure_ai_chat_deployment,
                      "embedding_deployment": settings.azure_ai_embedding_deployment},
        },
    }


# --- chunking (no storage) ----------------------------------------------------
@app.post("/chunk", response_model=ChunkResponse, tags=["1 · chunking"])
def chunk_only(req: ChunkRequest) -> ChunkResponse:
    """Split text and LOOK at the result — nothing is stored. Try the same text
    with all four strategies and compare the boundaries."""
    pieces, p = _do_chunk(req)
    return ChunkResponse(strategy=p["strategy"], params_used=p, count=len(pieces),
                         chunks=_chunk_infos(pieces))


# --- ingestion ----------------------------------------------------------------
@app.post("/ingest", response_model=IngestResponse, tags=["2 · ingestion"])
def ingest(req: IngestRequest) -> IngestResponse:
    """Chunk -> embed -> store in Qdrant. The response shows the chunks, the
    vector dimension, and a peek at the first embedding."""
    _require_qdrant()
    pieces, p = _do_chunk(req)
    if not pieces:
        raise HTTPException(status_code=422, detail="No chunks produced — is the text empty?")
    vectors = _embed(pieces)
    dim = len(vectors[0])
    try:
        store.ensure_collection(dim)
    except DimensionMismatch as e:
        raise HTTPException(status_code=409, detail=str(e))
    ids = store.upsert(pieces, vectors, p["strategy"], req.source)
    return IngestResponse(
        strategy=p["strategy"], count=len(pieces), vector_dimension=dim,
        embedding_preview=[round(x, 5) for x in vectors[0][:8]],
        embedding_model=_embedder().describe(), point_ids=ids, chunks=_chunk_infos(pieces),
    )


@app.get("/collection", response_model=CollectionInfo, tags=["2 · ingestion"])
def collection_info() -> CollectionInfo:
    _require_qdrant()
    return CollectionInfo(**store.info())


@app.delete("/collection", tags=["2 · ingestion"])
def collection_reset() -> dict:
    """Wipe everything — the clean slate between demos."""
    _require_qdrant()
    return {"deleted": store.reset(), "collection": settings.qdrant_collection}


# --- retrieval ----------------------------------------------------------------
@app.post("/search", response_model=SearchResponse, tags=["3 · retrieval"])
def search(req: SearchRequest) -> SearchResponse:
    """Embed the query, return the nearest chunks with their cosine similarity
    scores — retrieval with the curtain open."""
    _require_qdrant()
    if not store.info()["exists"]:
        raise HTTPException(status_code=404, detail="Collection is empty — POST /ingest first.")
    top_k = req.top_k or settings.top_k
    qvec = _embed([req.query])[0]
    hits = store.search(qvec, top_k)
    return SearchResponse(
        query=req.query, top_k=top_k, embedding_model=_embedder().describe(),
        query_embedding_preview=[round(x, 5) for x in qvec[:8]],
        hits=[SearchHit(**h) for h in hits],
    )


# --- generation ---------------------------------------------------------------
@app.post("/ask", response_model=AskResponse, tags=["4 · generation"])
def ask(req: AskRequest) -> AskResponse:
    """The finale: answer a question with or without augmentation. Flip `use_rag`
    and compare `prompt_sent` and the answers — that difference IS RAG."""
    temperature = req.temperature if req.temperature is not None else settings.llm_temperature
    retrieved: list[SearchHit] = []

    if req.use_rag:
        _require_qdrant()
        if not store.info()["exists"]:
            raise HTTPException(status_code=404,
                                detail="use_rag=true but the collection is empty — POST /ingest first, "
                                       "or set use_rag=false for a plain LLM answer.")
        top_k = req.top_k or settings.top_k
        qvec = _embed([req.question])[0]
        retrieved = [SearchHit(**h) for h in store.search(qvec, top_k)]
        system = rag.SYSTEM_PROMPT_RAG
        prompt = rag.build_augmented_prompt(req.question, [h.model_dump() for h in retrieved])
    else:
        system = rag.SYSTEM_PROMPT
        prompt = req.question

    try:
        result = get_llm().chat(system=system, user=prompt,
                                temperature=temperature, max_tokens=settings.llm_max_tokens)
    except Exception as e:
        raise HTTPException(status_code=502,
                            detail=f"LLM call failed ({settings.llm_provider}): {e}")

    return AskResponse(
        answer=result.text, augmented=req.use_rag, provider=result.provider,
        model=result.model, system_prompt=system, prompt_sent=prompt, retrieved=retrieved,
        usage=Usage(prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens),
    )
