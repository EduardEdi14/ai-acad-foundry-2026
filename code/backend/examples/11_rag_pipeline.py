"""11 · The whole RAG loop in one file — chunk, embed, store, search, answer.

Everything the API does, in sixty readable lines, so the pipeline can be traced end
to end without FastAPI in the way. Needs Qdrant: docker compose up qdrant -d

    uv run python examples/11_rag_pipeline.py
"""
from __future__ import annotations

from _bootstrap import banner, show_context
from app.agents import load_persona
from app.agents.local_agent import run as run_agent
from app.chunking import chunk
from app.embeddings import get_embedder
from app.vectorstore import VectorStore

banner("11 · the RAG pipeline, end to end")
show_context()

DOCUMENT = """
Libra Bank issues debit and credit cards to retail customers. A card is blocked
automatically after three failed PIN attempts, after the fraud engine flags a
suspicious transaction, or at the customer's own request in the mobile application.
A blocked card is unblocked in the branch after identity verification, or through the
call centre using the phone banking password.

Mortgage loans require a down payment of at least fifteen percent for a first home.
Early repayment is free of charge during the variable-rate period; during the
fixed-rate period an early repayment fee of one percent applies.

Term deposits can be opened in RON, EUR or USD, with maturities from one month to two
years. Breaking a deposit before maturity forfeits the accrued interest.
"""

QUESTION = "my card got frozen — what do I do?"

# 1 ── chunk ────────────────────────────────────────────────────────────────────
chunks = chunk(DOCUMENT, "dynamic", size=400, overlap=80, per_chunk=3, threshold=0.75)
print(f"\n1 · chunked into {len(chunks)} pieces")
for i, c in enumerate(chunks):
    print(f"     [{i}] {len(c):>4} chars  {c[:72]}…")

# 2 ── embed ────────────────────────────────────────────────────────────────────
embedder = get_embedder()
vectors = embedder.embed(chunks)
print(f"\n2 · embedded with {embedder.model} → {len(vectors[0])} dimensions each")

# 3 ── store ────────────────────────────────────────────────────────────────────
store = VectorStore()
if not store.ping():
    raise SystemExit("Qdrant is not reachable — run: docker compose up qdrant -d")
store.reset()
store.ensure_collection(len(vectors[0]))
ids = store.upsert(chunks, vectors, "dynamic", "example-11")
print(f"3 · stored {len(ids)} points in collection '{store.collection}'")

# 4 ── search ───────────────────────────────────────────────────────────────────
qvec = embedder.embed([QUESTION])[0]
hits = store.search(qvec, top_k=2)
print(f"\n4 · searched for: {QUESTION!r}")
for h in hits:
    print(f"     score {h['score']:.4f}  {h['text'][:72]}…")

# 5 ── answer ───────────────────────────────────────────────────────────────────
persona = load_persona("default")
reply = run_agent(persona, QUESTION, hits)
print(f"\n5 · answered by '{persona.display_name}':\n")
print(reply.text.strip())
print(f"\n[tokens {reply.prompt_tokens}/{reply.completion_tokens}]")

print("""
Note that step 4 found the right passage although the question says "frozen" and the
document says "blocked" — no shared keyword. That is retrieval in meaning-space, and
it is the reason this pipeline works at all.
""")
