"""07 · Streaming — perceived latency is a design choice.

A long answer takes seconds to generate, but the first token arrives quickly.
Streaming is the difference between an app that feels broken and one that feels alive.

    uv run python examples/07_streaming.py
"""
from __future__ import annotations

import time

from _bootstrap import banner, show_context
from app.config import settings
from azure.ai.inference import ChatCompletionsClient
from azure.identity import DefaultAzureCredential

banner("07 · streaming: tokens as they are produced")
show_context()

client = ChatCompletionsClient(
    endpoint=settings.azure_ai_endpoint,
    credential=DefaultAzureCredential(),
    credential_scopes=["https://cognitiveservices.azure.com/.default"],
)

question = "Explain, step by step, how an IBAN is structured and validated."
print(f"\nQ: {question}\n")

started = time.perf_counter()
first_token_at: float | None = None
chunks = 0

stream = client.complete(
    model=settings.azure_ai_chat_deployment,
    messages=[{"role": "user", "content": question}],
    stream=True,
    model_extras={"max_completion_tokens": 2000},
)

for update in stream:
    if not update.choices:
        continue
    piece = update.choices[0].delta.content
    if piece:
        if first_token_at is None:
            first_token_at = time.perf_counter() - started
        chunks += 1
        print(piece, end="", flush=True)

total = time.perf_counter() - started
print("\n")
print(f"time to first token : {first_token_at:.2f} s   ← what the user actually feels")
print(f"total time          : {total:.2f} s")
print(f"stream updates      : {chunks}")
print("\nWithout streaming the user stares at nothing for the full duration. Same model,")
print("same cost, entirely different product.")
