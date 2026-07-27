"""02 · The first authenticated call — eight lines, every one earning its place.

    uv run python examples/02_hello_foundry.py
"""
from __future__ import annotations

from _bootstrap import banner, show_context
from app.llm import get_llm

banner("02 · hello, Foundry")
show_context()

llm = get_llm()
result = llm.chat(
    system="You are a precise assistant. Answer in two sentences.",
    user="What does an LLM gateway add on top of a raw model API?",
    temperature=0.2,
    max_tokens=2000,
)

print(f"\n{result.text}\n")
print(f"provider : {result.provider}")
print(f"model    : {result.model}          ← this is your DEPLOYMENT name, not 'the model'")
print(f"tokens   : {result.prompt_tokens} in / {result.completion_tokens} out   ← the meter, on every response")
print("\nThere is no API key in this file. The call authenticated as YOU.")
