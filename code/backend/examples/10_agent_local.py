"""10 · Behaviour is data — the same question through every persona.

No API, no server: just the persona files and the model. Edit any JSON in
app/agents/personas/ and re-run to see the effect immediately.

    uv run python examples/10_agent_local.py
    uv run python examples/10_agent_local.py "Why was my card blocked?"
"""
from __future__ import annotations

import sys

from _bootstrap import banner, show_context
from app.agents import list_personas
from app.agents.local_agent import run

banner("10 · one question, four personalities")
show_context()

QUESTION = " ".join(sys.argv[1:]) or "What fee applies to early mortgage repayment?"

# Pretend retrieval already happened — this is what /ask passes to the agent.
CONTEXT = [{
    "score": 0.91,
    "text": ("Mortgage early repayment is free of charge in the variable-rate period, "
             "while during the fixed-rate period an early repayment fee of one percent applies."),
}]

print(f"\nQ: {QUESTION}")
print(f"(one retrieved passage supplied as context)\n")

for persona in list_personas():
    reply = run(persona, QUESTION, CONTEXT)
    print("─" * 76)
    print(f"{persona.display_name}  ·  temperature {persona.temperature}  ·  {persona.description}")
    print("─" * 76)
    print(reply.text.strip())
    print(f"\n[tokens {reply.prompt_tokens}/{reply.completion_tokens}]\n")

print("Same model, same context, same question. Only a JSON file differed — and the")
print("Python never changed. That is why prompts belong in version-controlled data.")
