"""08 · Failure is the normal case — retry with exponential backoff.

On a shared quota, 429 is not an accident: it is Tuesday. This shows which errors
are worth retrying and which are configuration problems that retrying cannot fix.

    uv run python examples/08_robust_call.py
"""
from __future__ import annotations

import time

from _bootstrap import banner, show_context
from app.config import settings
from azure.ai.inference import ChatCompletionsClient
from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential

banner("08 · resilience: retry the transient, fail fast on the rest")
show_context()

RETRIABLE = {429, 500, 502, 503, 504}

client = ChatCompletionsClient(
    endpoint=settings.azure_ai_endpoint,
    credential=DefaultAzureCredential(),
    credential_scopes=["https://cognitiveservices.azure.com/.default"],
)


def complete_with_retry(attempts: int = 5, **kwargs):
    for attempt in range(attempts):
        try:
            return client.complete(**kwargs)
        except HttpResponseError as e:
            status = e.status_code
            if status not in RETRIABLE:
                print(f"  ✗ HTTP {status} is NOT retriable — this is configuration, not weather.")
                raise
            if attempt == attempts - 1:
                print(f"  ✗ still HTTP {status} after {attempts} attempts — giving up loudly.")
                raise
            wait = 2 ** attempt                      # 1, 2, 4, 8 seconds
            print(f"  … HTTP {status} on attempt {attempt + 1}; waiting {wait}s before retry")
            time.sleep(wait)


print("""
 status        meaning                          correct response
 ───────────── ──────────────────────────────── ─────────────────────────────────
 429           quota exceeded (TPM/RPM)         back off and retry
 500/503       transient service fault          back off and retry
 401 / 403     identity or role problem         fail fast — fix auth
 404           deployment name wrong            fail fast — fix configuration
 finish=length YOUR cap truncated the answer    handle in logic, not by retrying
""")

result = complete_with_retry(
    model=settings.azure_ai_chat_deployment,
    messages=[{"role": "user", "content": "Say 'resilient' and nothing else."}],
    model_extras={"max_completion_tokens": 2000},
)

choice = result.choices[0]
print(f"answer        : {choice.message.content}")
print(f"finish_reason : {choice.finish_reason}   ← 'stop' = the model finished; 'length' = you cut it off")
print(f"tokens        : {result.usage.prompt_tokens} / {result.usage.completion_tokens}")
