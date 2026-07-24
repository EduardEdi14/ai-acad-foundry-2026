"""Provider-agnostic chat: lmstudio | openai | anthropic | azure.

One interface, four backends — switching is two lines in .env. The returned
ChatResult always carries the token usage when the provider reports it.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .config import settings


@dataclass
class ChatResult:
    text: str
    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class LLM:
    def __init__(self, provider: str, model: str, client) -> None:
        self.provider = provider
        self.model = model
        self._client = client

    def chat(self, system: str, user: str, temperature: float, max_tokens: int) -> ChatResult:
        if self.provider in ("lmstudio", "openai"):
            kwargs: dict = {
                "model": self.model,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
            # OpenAI's gpt-5.x family renamed the cap; LM Studio still speaks the classic name
            if self.provider == "openai":
                kwargs["max_completion_tokens"] = max_tokens
            else:
                kwargs["max_tokens"] = max_tokens
            r = self._client.chat.completions.create(**kwargs)
            u = getattr(r, "usage", None)
            return ChatResult(
                text=r.choices[0].message.content or "",
                provider=self.provider,
                model=self.model,
                prompt_tokens=getattr(u, "prompt_tokens", None),
                completion_tokens=getattr(u, "completion_tokens", None),
            )

        if self.provider == "anthropic":
            r = self._client.messages.create(
                model=self.model,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": user}],
            )
            return ChatResult(
                text="".join(block.text for block in r.content if block.type == "text"),
                provider=self.provider,
                model=self.model,
                prompt_tokens=r.usage.input_tokens,
                completion_tokens=r.usage.output_tokens,
            )

        # azure — azure-ai-inference ChatCompletionsClient
        r = self._client.complete(
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        u = getattr(r, "usage", None)
        return ChatResult(
            text=r.choices[0].message.content or "",
            provider=self.provider,
            model=self.model,
            prompt_tokens=getattr(u, "prompt_tokens", None),
            completion_tokens=getattr(u, "completion_tokens", None),
        )

    def describe(self) -> dict:
        return {"provider": self.provider, "model": self.model}


@lru_cache(maxsize=1)
def get_llm() -> LLM:
    provider = settings.llm_provider.lower()

    if provider == "lmstudio":
        from openai import OpenAI

        return LLM(provider, settings.lmstudio_model,
                   OpenAI(base_url=settings.lmstudio_base_url, api_key="lm-studio"))

    if provider == "openai":
        from openai import OpenAI

        return LLM(provider, settings.openai_model, OpenAI(api_key=settings.openai_api_key))

    if provider == "anthropic":
        from anthropic import Anthropic

        return LLM(provider, settings.anthropic_model,
                   Anthropic(api_key=settings.anthropic_api_key))

    if provider == "azure":
        if not settings.azure_ai_endpoint:
            raise ValueError(
                "AZURE_AI_ENDPOINT is not set — put your Foundry endpoint in .env "
                "(README § Credentials · Azure Foundry)"
            )
        from azure.ai.inference import ChatCompletionsClient

        client = ChatCompletionsClient(
            endpoint=settings.azure_ai_endpoint,
            credential=_azure_credential(),
            credential_scopes=["https://cognitiveservices.azure.com/.default"],
        )
        return LLM(provider, settings.azure_ai_chat_deployment, client)

    raise ValueError(
        f"LLM_PROVIDER='{provider}' is not supported — use lmstudio, openai, anthropic or azure"
    )


def _azure_credential():
    if settings.azure_ai_auth.lower() == "key":
        from azure.core.credentials import AzureKeyCredential

        return AzureKeyCredential(settings.azure_ai_api_key)
    from azure.identity import DefaultAzureCredential

    return DefaultAzureCredential()
