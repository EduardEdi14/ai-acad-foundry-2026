# RAG Teaching API

A backend built to *show* Retrieval-Augmented Generation, endpoint by endpoint:
chunk text with four selectable strategies, embed and store in **Qdrant**, retrieve
with visible **similarity scores**, and answer questions **with or without
augmentation** — every response exposes the pipeline's intermediate artifacts,
including the exact final prompt sent to the model.

```
text ─► POST /chunk ─► POST /ingest ─► Qdrant ─► POST /search ─► POST /ask
        (strategies)   (embeddings)              (scores)        (± augmentation)
```

- **API:** FastAPI + uvicorn (live reload), port **7799**
- **Vector DB:** Qdrant in Docker, ports **7833** (HTTP/dashboard) / **7834** (gRPC)
- **Swagger UI:** http://localhost:7799/docs · ReDoc: `/redoc`
- **Postman:** import `postman/rag-teaching-api.postman_collection.json`
- **Deps:** managed with [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`)

## Run it — option A: everything local

```bash
cd code/backend
cp .env.example .env               # then edit — see Credentials below
docker compose up qdrant -d        # just the DB
uv sync                            # create .venv from uv.lock
uv run uvicorn app.main:app --reload --port 7799
```

## Run it — option B: everything in Docker

```bash
cd code/backend
docker compose up --build
```

The app container overrides `QDRANT_URL` automatically and bind-mounts `./app`,
so **live reload works inside the container too** — edit a file, watch it restart.
Note for Docker + Azure keyless auth: `az login` doesn't exist inside the container,
so either use `AZURE_AI_AUTH=key` there, or run the API locally (option A) for the
identity lane.

Qdrant has a visual dashboard: http://localhost:7833/dashboard — great on a shared screen.

## The demo, in order

| Step | Call | What to look at |
|---|---|---|
| 1 | `GET /health` | Everything green, which providers are active |
| 2 | `POST /chunk` ×4 strategies | Same text, different boundaries — static cuts mid-sentence, semantic follows meaning |
| 3 | `POST /ingest` | Chunks became vectors: dimension, first 8 numbers of an embedding |
| 4 | `GET /collection` | What Qdrant now holds |
| 5 | `POST /search` | Paraphrased query still finds the right chunk — cosine scores, descending |
| 6 | `POST /ask` `use_rag=false` | The model guesses (or refuses) — inspect `prompt_sent` |
| 7 | `POST /ask` `use_rag=true` | Grounded answer with [1] [2] citations — compare `prompt_sent` now |
| 8 | `DELETE /collection` | Clean slate for the next group |

Chunking strategies (`strategy` in the request body): `static` (fixed windows),
`sentence` (N sentences per chunk), `dynamic` (paragraph/sentence-aware packing with
overlap), `semantic` (sentence embeddings; new chunk where adjacent cosine similarity
drops below `semantic_threshold` — needs the embedding provider configured).

## Choosing providers

Two `.env` lines switch everything; restart (or let reload pick it up):

```
LLM_PROVIDER=lmstudio | openai | anthropic | azure
EMBEDDING_PROVIDER=lmstudio | openai | azure      # Anthropic has no embeddings API
```

Chat and embeddings are independent — Claude can answer while Azure embeds.
**Embedding dimensions are a commitment**: if you switch embedding models after
ingesting, `/ingest` will refuse with a 409 (different models → incomparable
vector spaces). `DELETE /collection` and re-ingest.

## Credentials — step by step

### Azure Foundry (the course lane)

1. You need a Foundry resource with two deployments (`gpt-5.1`,
   `text-embedding-3-small`). Full click-by-click from an empty account:
   `docs/ref-foundry.html` in this repo (or the course session pages).
2. Find the **endpoint**: Foundry portal ([ai.azure.com](https://ai.azure.com)) →
   your project → **Overview** → copy the endpoint that looks like
   `https://<resource>.services.ai.azure.com/models` → put it in `AZURE_AI_ENDPOINT`.
3. **Auth, keyless (recommended, local runs):** keep `AZURE_AI_AUTH=identity`, then
   `az login` once in your terminal ([install the CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
   if needed). Your identity needs the *Cognitive Services User* (or *Azure AI User*)
   role on the resource.
4. **Auth, key (for Docker):** portal → your Foundry resource → **Keys and
   Endpoint** → copy Key 1 → `AZURE_AI_AUTH=key` and `AZURE_AI_API_KEY=...`.
   Treat the key like a password; it is why `.env` is gitignored.
5. `AZURE_AI_CHAT_DEPLOYMENT` / `AZURE_AI_EMBEDDING_DEPLOYMENT` must equal your
   **deployment names** (not model names) — ours match: `gpt-5.1`,
   `text-embedding-3-small`.

### OpenAI

1. Create an account at [platform.openai.com](https://platform.openai.com).
2. **Settings → Billing** → add a payment method or a small prepaid credit
   ($5 is plenty for a workshop).
3. **API keys** ([platform.openai.com/api-keys](https://platform.openai.com/api-keys)) →
   *Create new secret key* → copy it **now** (it is shown once) → `OPENAI_API_KEY=sk-...`.
4. Models: `OPENAI_MODEL` (chat) and `OPENAI_EMBEDDING_MODEL` — the defaults are
   sensible; any current chat model works.

### Anthropic (Claude — chat only)

1. Create an account at [console.anthropic.com](https://console.anthropic.com).
2. **Billing** → add credit. 3. **API keys** → *Create key* → copy → `ANTHROPIC_API_KEY=sk-ant-...`.
4. `ANTHROPIC_MODEL=claude-sonnet-5` is the current default; remember Anthropic
   provides **no embeddings API** — pair it with `EMBEDDING_PROVIDER=lmstudio|openai|azure`.

### LM Studio (local gemma — free, no account, works offline)

1. Download LM Studio from [lmstudio.ai](https://lmstudio.ai) and install.
2. In-app **Discover** tab → search `gemma` → download a size your machine handles
   (the 4B class runs on most laptops).
3. Also download an **embedding model** — search `nomic-embed-text`.
4. **Developer / Local Server** tab → start the server (default port **1234**).
5. Copy the exact model identifiers shown by LM Studio into `LMSTUDIO_MODEL` and
   `LMSTUDIO_EMBEDDING_MODEL`; set both providers to `lmstudio`.
6. Docker note: from inside the container the host's LM Studio is
   `http://host.docker.internal:1234/v1` (see the commented line in docker-compose.yml).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `503 Qdrant is not reachable` | `docker compose up qdrant -d`; check `QDRANT_URL` (local = `http://localhost:7833`) |
| `409` on `/ingest` (dimension mismatch) | You changed embedding models — `DELETE /collection`, re-ingest |
| `502 Embedding/LLM call failed … 401` | Wrong/expired key, or (azure identity) run `az login`; check the role |
| `502 … Connection refused` on lmstudio | LM Studio server not started, or wrong base URL from Docker |
| Azure works locally, fails in Docker | Identity lane needs `az login` — use `AZURE_AI_AUTH=key` in containers |
| Port already in use | All ports are configurable: `API_PORT`, compose port mappings |
