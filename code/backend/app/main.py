"""RAG Teaching API — every response exposes the pipeline's intermediate steps.

Demo order:  /health -> /chunk -> /ingest -> /collection -> /search -> /ask
Swagger UI:  /docs        ReDoc: /redoc
"""
from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from . import chunking
from .agents import foundry_agent, local_agent
from .agents.persona import PersonaNotFound, available_names, load_persona, list_personas, PERSONA_DIR
from .config import settings
from .embeddings import get_embedder
from .llm import get_llm
from .schemas import (
    AgentInfo, AgentListResponse, AskRequest, AskResponse, ChunkInfo, ChunkRequest,
    ChunkResponse, CollectionInfo, Health, IngestRequest, IngestResponse, PersonaSummary,
    ScrapeRequest, ScrapeResponse, SearchHit, SearchRequest, SearchResponse, SpeakRequest,
    TranscribeResponse, Usage,
)
from .services import speech, web
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
        agents={"mode": settings.agent_mode,
                "default_persona": settings.agent_persona,
                "available": available_names(),
                "foundry_agent_id": settings.foundry_agent_id or None},
        speech={"configured": bool(settings.azure_speech_key and settings.azure_speech_region),
                "region": settings.azure_speech_region or None,
                "voice": settings.azure_speech_voice},
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
    """The finale: an **agent** answers, with or without retrieval.

    Three dials to demonstrate, one at a time:
      * `use_rag`      — false = the model alone; true = retrieve, then augment.
      * `agent`        — which persona shapes the answer (edit its JSON and re-ask!).
      * `agent_mode`   — `local` runs the loop here; `foundry` calls the hosted agent.

    `system_prompt` and `prompt_sent` always show exactly what went to the model.
    """
    retrieved: list[SearchHit] = []

    # ---- which persona? -----------------------------------------------------
    persona_name = req.agent or settings.agent_persona
    try:
        persona = load_persona(persona_name)
    except PersonaNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))

    # ---- retrieval (unchanged behaviour, now feeding the agent) -------------
    if req.use_rag:
        _require_qdrant()
        if not store.info()["exists"]:
            raise HTTPException(status_code=404,
                                detail="use_rag=true but the collection is empty — POST /ingest first, "
                                       "or set use_rag=false for a plain LLM answer.")
        top_k = req.top_k or settings.top_k
        qvec = _embed([req.question])[0]
        retrieved = [SearchHit(**h) for h in store.search(qvec, top_k)]

    chunks = [h.model_dump() for h in retrieved]
    mode = (req.agent_mode or settings.agent_mode).lower()

    # ---- run the agent ------------------------------------------------------
    try:
        if mode == "foundry":
            reply = foundry_agent.run(persona, req.question, chunks)
        else:
            reply = local_agent.run(persona, req.question, chunks, temperature=req.temperature)
    except foundry_agent.FoundryUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502,
                            detail=f"Agent run failed (mode={mode}, provider={settings.llm_provider}): {e}")

    return AskResponse(
        answer=reply.text,
        augmented=req.use_rag,
        provider=reply.provider,
        model=reply.model,
        agent=AgentInfo(
            name=persona.name, display_name=persona.display_name,
            description=persona.description, mode=reply.mode,
            temperature=persona.temperature, style_rules=persona.style_rules,
        ),
        system_prompt=reply.system_prompt,
        prompt_sent=reply.prompt_sent,
        retrieved=retrieved,
        usage=Usage(prompt_tokens=reply.prompt_tokens, completion_tokens=reply.completion_tokens),
    )


# --- agents -------------------------------------------------------------------
@app.get("/agents", response_model=AgentListResponse, tags=["5 · agents"])
def agents_list() -> AgentListResponse:
    """Every persona currently on disk. Add a JSON file and it appears here —
    no restart. This is the list `/ask?agent=…` accepts."""
    personas = list_personas()
    return AgentListResponse(
        active_mode=settings.agent_mode,
        default_persona=settings.agent_persona,
        personas_dir=str(PERSONA_DIR),
        count=len(personas),
        personas=[PersonaSummary(**p.summary()) for p in personas],
    )


@app.get("/agents/{name}", tags=["5 · agents"])
def agent_detail(name: str) -> dict:
    """One persona, including **the exact system prompt** its JSON produces —
    grounded and ungrounded. The clearest way to see JSON become behaviour."""
    try:
        persona = load_persona(name)
    except PersonaNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        **persona.summary(),
        "system_prompt_plain": persona.system_prompt(grounded=False),
        "system_prompt_grounded": persona.system_prompt(grounded=True),
        "file": str(PERSONA_DIR / f"{name}.json"),
    }


@app.post("/agents/{name}/deploy", tags=["5 · agents"])
def agent_deploy(name: str) -> dict:
    """Publish this persona to the Azure AI Foundry **Agent Service**.

    The same thing `python scripts/deploy_agent.py <name>` does — exposed here so
    it can be demonstrated from Swagger. Requires AZURE_AI_PROJECT_ENDPOINT and
    an Entra identity with the Azure AI User role on the project.
    """
    try:
        persona = load_persona(name)
    except PersonaNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    try:
        result = foundry_agent.deploy(persona)
    except foundry_agent.FoundryUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Deployment to Foundry failed: {e}")
    result["next_step"] = (
        f"Put FOUNDRY_AGENT_ID={result['agent_id']} in .env, then call /ask with "
        f'"agent_mode": "foundry".'
    )
    return result


# --- tools / specialist services ----------------------------------------------
@app.post("/tools/web-fetch", response_model=ScrapeResponse, tags=["6 · tools"])
def web_fetch(req: ScrapeRequest) -> ScrapeResponse:
    """Fetch a page and strip it to text — **the do-it-yourself lane**.

    Read the `warnings` array: it lists everything this naive approach could not
    handle (JavaScript rendering, bot walls, consent banners, non-HTML formats).
    That list is the argument for a managed grounding tool.
    """
    try:
        result = web.scrape(req.url, max_chars=req.max_chars or 20000)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Fetch failed: {e}")
    return ScrapeResponse(**result.__dict__)


@app.post("/tools/speak", tags=["6 · tools"],
          responses={200: {"content": {"audio/wav": {}}, "description": "WAV audio"}})
def speak(req: SpeakRequest):
    """Text → speech (Azure AI Speech). Returns a WAV file you can play or download."""
    try:
        audio = speech.synthesize(req.text, req.voice)
    except speech.SpeechUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Speech synthesis failed: {e}")
    return Response(content=audio, media_type="audio/wav",
                    headers={"Content-Disposition": 'inline; filename="libra-assist.wav"'})


@app.post("/tools/transcribe", response_model=TranscribeResponse, tags=["6 · tools"])
async def transcribe(file: UploadFile = File(..., description="WAV, 16 kHz mono, under ~60 s")):
    """Speech → text (Azure AI Speech). Upload the WAV you just generated and
    watch it come back as text — the round trip in two calls."""
    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")
    try:
        result = speech.transcribe(audio, content_type=file.content_type or "audio/wav")
    except speech.SpeechUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {e}")
    return TranscribeResponse(**result)
