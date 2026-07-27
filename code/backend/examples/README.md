# Lesson scripts

Every code sample shown in the session pages, as a runnable script. They are numbered
in teaching order and each one prints what it is doing, so they read well on a shared
screen.

```bash
cd code/backend
uv sync
az login                       # keyless auth; see 01_whoami.py
uv run python examples/01_whoami.py
```

| # | Script | Session | Shows |
|---|---|---|---|
| 01 | `01_whoami.py` | S4 · Lab A | The identity chain: a real token, its expiry, which credential answered |
| 02 | `02_hello_foundry.py` | S2 | The first authenticated chat call, line by line |
| 03 | `03_tokens.py` | S1 | Tokenization — why Romanian costs more than English |
| 04 | `04_embeddings.py` | S1 · S5 | Meaning as geometry: cosine similarity between phrases |
| 05 | `05_wiring.py` | S4 · wiring | One credential, many clients, one scope per service |
| 06 | `06_structured_output.py` | S3 | Schema-constrained JSON — a prompt as an interface |
| 07 | `07_streaming.py` | S3 | Tokens arriving as they are generated |
| 08 | `08_robust_call.py` | S3 | Exponential backoff; which errors are worth retrying |
| 09 | `09_list_deployments.py` | S4 | The control plane: what exists in your resource |
| 10 | `10_agent_local.py` | S4 | A persona file becomes behaviour, without the API |
| 11 | `11_rag_pipeline.py` | S5 | The whole RAG loop in one file: chunk → embed → search → answer |

Scripts 01–09 need only the model deployments. 10 uses `app/agents/personas/`.
11 additionally needs Qdrant running (`docker compose up qdrant -d`).

All of them read `.env` through `app.config`, so they follow whatever provider you have
configured — including LM Studio if you want to run the whole set offline.
