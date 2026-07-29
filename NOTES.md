Responses:
1. 1536 ( vector_dimension = 1536)
2. 0.1055, 0.119 and 0.2232 were the scores obtained. The vector retrieval algorithm will always return the closest mathematical match from the database. The extremely low scores (ex. 0.2232) clearly indicate that the retrieved passages have no semantic relevance to the query. In practice, such a low score acts as a threshold, telling the system that it lacks the required information and should refuse to answer rather than hallucinate/invent an answer.
3. When use_rag is true, the system automatically injects a CONTEXT block containing the top retrieved text passages from Qdrant ([1], [2], [3]) directly into the prompt_sent. Additionally, instructions are added to the system prompt telling the model to base its response strictly on those passages and cite them using [1], [2], etc. This significantly increases the prompt_tokens (to 367 tokens in this run) compared to a standard query.
4. Current status in Docker: Currently, runs_on shows as "unknown" (with "foundry.available": false) because under Docker/key authentication, the API cannot query the Azure Agent Service directly.  Capable environments: It can run locally (local), and can also run on Foundry (both / local + Foundry) once AZURE_AI_PROJECT_ENDPOINT is configured and identity authentication (az login) is used.  How I know: I determined this by inspecting the runs_on and foundry fields in the JSON response from GET /agents (List agents in Folder 5), as well as checking the agent badges in the web console. 
![alt text](image.png)

---

# Assignment 3 — Part 4 & Part 5

## Ingestion improvements (Part 4)

**#1 — Stable chunk ids.** `app/vectorstore.py`, `stable_point_id()`. Previously
`upsert()` gave every chunk a fresh `uuid.uuid4()`, so re-ingesting a document
added brand-new points instead of replacing the old ones — the collection grew
without bound and duplicate chunks competed with each other at search time
(exactly the symptom in the a3.md troubleshooting table: "ingesting the same
document twice doubles the hits"). The id is now `uuid5(NAMESPACE_URL,
"libra-rag:{source}:{index}")` — deterministic from the document's `source` and
its chunk index, so the same document chunked the same way always upserts onto
the same points.

**#2 — Real metadata.** `app/vectorstore.py` (`METADATA_FIELDS`, `upsert()`,
`search()`), `app/schemas.py` (`IngestRequest`/`SearchHit`), and the loader
(`scripts/load_corpus.py`). Every document in `data/` already carried a
front-matter header (`title`, `product`, `audience`, `effective`, `version`);
previously nothing captured it past the file. The loader now parses it and
`/ingest` stores it in the Qdrant payload, so every retrieved chunk can say
*which* document, product and effective date it came from — required for the
metadata filters in Part 5, and for telling the 2025 and 2026 fee schedules apart.

### Before/after — real numbers

Ingesting the whole corpus (`uv run python scripts/load_corpus.py --reset`)
produces 17 points across 12 documents. Re-running the loader again with no
`--reset`:

| | points before | points after re-ingest |
|---|---|---|
| Before (random uuid4 ids) | 17 | 34 (every chunk duplicated) |
| After (stable ids) | 17 | 17 (unchanged — same points, replaced in place) |

The "before" row is the documented behaviour this repo shipped with (see the
troubleshooting table in `docs/assignments/a3.md`); the "after" row is what
`GET /collection` actually returned after re-running the loader twice in a row
on 2026-07-29 against the live Azure Foundry deployment.

## Retrieval improvements (Part 5)

**#1 — Score threshold.** `app/main.py` (`/search`, `/ask`), `app/vectorstore.py`
`search()` (passes Qdrant's native `score_threshold` to `query_points`). Below
the floor, `/search` simply omits the hit; `/ask` goes further — if *every* hit
falls below the threshold (or a filter matches nothing), it returns
`nothing_relevant: true` and a fixed refusal message **without calling the LLM
at all**, instead of falling back to an ungrounded guess.

Demonstrated with the group-C question *"what is the interest rate on your
student loans"* (Libra Bank does not offer student loans — nothing in the
corpus should answer this):

- `POST /search` with no threshold: top hit scores 0.4011 (`02_early_repayment_fee`)
  — retrieval returns something, and it looks plausible enough to be dangerous.
- `POST /search {"score_threshold": 0.45}`: 0 hits.
- `POST /ask {"use_rag": true, "score_threshold": 0.45}`: `nothing_relevant: true`,
  answer = *"Nothing relevant found in the knowledge base for this question."*,
  no tokens spent (`usage.prompt_tokens: null`) — measured live, 2026-07-29.

**#2 — Metadata filters.** `app/vectorstore.py` `_build_filter()` (Qdrant
`Filter`/`FieldCondition`/`MatchValue` on the payload), `app/schemas.py`
(`product`/`audience`/`effective`/`source` on `SearchRequest`/`AskRequest`).
Solves exactly the near-duplicate case the corpus was built to contain:

Query *"what is the monthly account maintenance fee"*, `top_k=4`, no filter:

| score | source | effective |
|---|---|---|
| 0.553 | `06_fees_2026` | 2026-01-01 |
| 0.553 | `05_fees_2025` | 2025-01-01 |
| 0.4215 | `07_account_types_table` | 2026-03-01 |
| 0.3263 | `02_early_repayment_fee` | 2026-02-01 |

The 2025 and 2026 fee schedules tie at 0.553 — cosine similarity has no idea
one of them is stale. Same query with `{"effective": "2026-01-01"}`:

| score | source | effective |
|---|---|---|
| 0.553 | `06_fees_2026` | 2026-01-01 |
| 0.2864 | `10_phishing_and_security` | 2026-01-01 |
| 0.2154 | `09_onboarding_process` | 2026-01-01 |

The stale 2025 schedule no longer competes.

## What is still wrong / next steps

- The score-threshold refusal in `/ask` is a hard cutoff on the *top* score
  only implicitly (Qdrant drops every hit below the floor, so "nothing left"
  and "the best hit was weak" collapse into the same signal) — a persona-level
  `min_score` tunable per agent would let a stricter persona (e.g.
  `compliance`) refuse more eagerly than `lyrical`.
- Metadata filters require the caller to already know the right `effective`
  date; a "latest version wins" default (picking the highest `version` per
  `product`+`audience` when no filter is given) would fix the near-duplicate
  case without the caller having to ask for it explicitly.
- No hybrid/keyword search yet (Part 5 improvement #3) — exact tokens like
  IBANs or product codes still rely on the embedding alone.
