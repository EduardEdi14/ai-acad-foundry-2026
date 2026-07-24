"""Provider-agnostic embeddings: lmstudio | openai | azure.

Anthropic is deliberately absent — it offers no embeddings API; use any of the
other three for vectors even when Claude answers the chat side.
"""
from __future__ import annotations

from functools import lru_cache

from .config import settings


class Embedder:
    def __init__(self, provider: str, model: str, client) -> None:
        self.provider = provider
        self.model = model
        self._client = client

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.provider in ("lmstudio", "openai"):
            result = self._client.embeddings.create(model=self.model, input=texts)
            return [item.embedding for item in result.data]
        # azure — azure-ai-inference EmbeddingsClient
        result = self._client.embed(model=self.model, input=texts)
        return [item.embedding for item in result.data]

    def describe(self) -> dict:
        return {"provider": self.provider, "model": self.model}


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    provider = settings.embedding_provider.lower()

    if provider == "lmstudio":
        from openai import OpenAI

        client = OpenAI(base_url=settings.lmstudio_base_url, api_key="lm-studio")
        return Embedder(provider, settings.lmstudio_embedding_model, client)

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        return Embedder(provider, settings.openai_embedding_model, client)

    if provider == "azure":
        if not settings.azure_ai_endpoint:
            raise ValueError(
                "AZURE_AI_ENDPOINT is not set — put your Foundry endpoint in .env "
                "(README § Credentials · Azure Foundry)"
            )
        from azure.ai.inference import EmbeddingsClient

        client = EmbeddingsClient(
            endpoint=settings.azure_ai_endpoint,
            credential=_azure_credential(),
            credential_scopes=["https://cognitiveservices.azure.com/.default"],
        )
        return Embedder(provider, settings.azure_ai_embedding_deployment, client)

    raise ValueError(
        f"EMBEDDING_PROVIDER='{provider}' is not supported — use lmstudio, openai or azure"
    )


def _azure_credential():
    if settings.azure_ai_auth.lower() == "key":
        from azure.core.credentials import AzureKeyCredential

        return AzureKeyCredential(settings.azure_ai_api_key)
    from azure.identity import DefaultAzureCredential

    return DefaultAzureCredential()
