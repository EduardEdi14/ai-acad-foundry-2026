"""Azure AI Search — the managed alternative to our Qdrant collection.

Same pipeline, different store: the chunks and vectors produced by `chunking.py`
and `embeddings.py` go in unchanged. What the managed service adds is what
Session 4 argues for — keyword search alongside vectors, filters over metadata,
and a place to put access rules — none of which pure vector similarity gives you.

We call the REST API with httpx rather than installing the SDK, for the same
reason as everywhere else in this app: the wire is the lesson.

Config:  AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_INDEX, AZURE_SEARCH_KEY
         (a key is used when present; otherwise the Entra identity, which needs
          the Search Index Data Contributor role)
"""
from __future__ import annotations

import httpx

from ..config import settings

API_VERSION = "2024-07-01"
SCOPE = "https://search.azure.com/.default"
TIMEOUT = 30.0


class SearchUnavailable(Exception):
    """Raised with instructions when Azure AI Search is not configured."""


def _require() -> str:
    if not settings.azure_search_endpoint:
        raise SearchUnavailable(
            "Azure AI Search is not configured. Create a service and set "
            "AZURE_SEARCH_ENDPOINT (and AZURE_SEARCH_KEY, or grant your identity the "
            "'Search Index Data Contributor' role). "
            "scripts/azure/07-provision-search.ps1 does all of it."
        )
    return settings.azure_search_endpoint.rstrip("/")


def _headers() -> dict:
    if settings.azure_search_key:
        return {"api-key": settings.azure_search_key, "Content-Type": "application/json"}
    try:
        from azure.identity import DefaultAzureCredential
    except ImportError as e:                     # pragma: no cover
        raise SearchUnavailable("azure-identity is not installed — run: uv sync") from e
    token = DefaultAzureCredential().get_token(SCOPE).token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _call(method: str, path: str, json: dict | None = None, params: dict | None = None) -> dict:
    url = f"{_require()}/{path.lstrip('/')}"
    response = httpx.request(
        method, url,
        params={"api-version": API_VERSION, **(params or {})},
        headers=_headers(), json=json, timeout=TIMEOUT,
    )
    if response.status_code >= 400:
        raise SearchUnavailable(
            f"Azure AI Search returned HTTP {response.status_code} for {method} {path}: "
            f"{response.text[:300]}"
        )
    return response.json() if response.content else {}


def describe() -> dict:
    """Health/status view that never raises."""
    if not settings.azure_search_endpoint:
        return {"configured": False, "endpoint": None, "index": settings.azure_search_index,
                "auth": None, "documents": None}
    info = {
        "configured": True,
        "endpoint": settings.azure_search_endpoint,
        "index": settings.azure_search_index,
        "auth": "key" if settings.azure_search_key else "identity",
        "documents": None,
    }
    try:
        info["documents"] = count()
    except Exception as e:                       # noqa: BLE001
        info["error"] = str(e)[:200]
    return info


def ensure_index(dimensions: int) -> dict:
    """Create the index if it does not exist.

    The schema is the point of the exercise: `text` is *searchable* so BM25 can
    match words, `vector` carries the embedding for similarity, and `source` and
    `allowed_groups` are *filterable* — which is how a bank restricts what a given
    reader may retrieve. None of that exists in a plain vector collection.
    """
    index = settings.azure_search_index
    definition = {
        "name": index,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
            {"name": "text", "type": "Edm.String", "searchable": True, "analyzer": "standard.lucene"},
            {"name": "source", "type": "Edm.String", "filterable": True, "facetable": True},
            {"name": "strategy", "type": "Edm.String", "filterable": True},
            {"name": "allowed_groups", "type": "Collection(Edm.String)", "filterable": True},
            {
                "name": "vector", "type": "Collection(Edm.Single)",
                "searchable": True, "dimensions": dimensions,
                "vectorSearchProfile": "default-profile",
            },
        ],
        "vectorSearch": {
            "algorithms": [{"name": "hnsw-config", "kind": "hnsw"}],
            "profiles": [{"name": "default-profile", "algorithm": "hnsw-config"}],
        },
        "semantic": {
            "configurations": [{
                "name": "default-semantic",
                "prioritizedFields": {"prioritizedContentFields": [{"fieldName": "text"}]},
            }]
        },
    }
    _call("PUT", f"indexes/{index}", definition)
    return {"index": index, "dimensions": dimensions}


def upload(chunks: list[str], vectors: list[list[float]], source: str,
           strategy: str, allowed_groups: list[str] | None = None) -> int:
    """Push chunks with stable ids, so re-uploading replaces instead of duplicating."""
    groups = allowed_groups or ["all-staff"]
    documents = [
        {
            "@search.action": "mergeOrUpload",
            "id": f"{source}-{i}",
            "text": text,
            "source": source,
            "strategy": strategy,
            "allowed_groups": groups,
            "vector": vector,
        }
        for i, (text, vector) in enumerate(zip(chunks, vectors))
    ]
    result = _call("POST", f"indexes/{settings.azure_search_index}/docs/index",
                   {"value": documents})
    return len(result.get("value", documents))


def count() -> int:
    data = _call("GET", f"indexes/{settings.azure_search_index}/docs/$count")
    return data if isinstance(data, int) else int(data or 0)


def query(text: str, vector: list[float] | None = None, top: int = 3,
          filter_expression: str | None = None, semantic: bool = False) -> list[dict]:
    """Keyword, vector, or both at once — the hybrid search Session 4 describes.

    Passing both `text` and `vector` is what makes it hybrid: the service runs each
    and fuses the rankings, so exact terms and paraphrases both land.
    """
    body: dict = {"top": top, "select": "id,text,source,strategy"}
    if text:
        body["search"] = text
    if vector:
        body["vectorQueries"] = [{
            "kind": "vector", "vector": vector, "fields": "vector", "k": top,
        }]
    if filter_expression:
        body["filter"] = filter_expression
    if semantic:
        body["queryType"] = "semantic"
        body["semanticConfiguration"] = "default-semantic"

    data = _call("POST", f"indexes/{settings.azure_search_index}/docs/search", body)
    return [
        {
            "id": d.get("id"),
            "score": round(float(d.get("@search.score", 0)), 4),
            "reranker_score": d.get("@search.rerankerScore"),
            "text": d.get("text", ""),
            "source": d.get("source"),
            "strategy": d.get("strategy"),
        }
        for d in data.get("value", [])
    ]


def delete_index() -> bool:
    _call("DELETE", f"indexes/{settings.azure_search_index}")
    return True
