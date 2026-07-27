#!/usr/bin/env python
"""Invoke the hosted Foundry agent directly — no FastAPI in the way.

    uv run python scripts/invoke_agent.py "Why was my card blocked?"
    uv run python scripts/invoke_agent.py "Why was my card blocked?" --persona lyrical

Useful for proving that the agent lives in Azure and is callable by *anything*,
not only by our backend — which is the whole point of hosting it there.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.foundry_agent import FoundryUnavailable, run  # noqa: E402
from app.agents.persona import PersonaNotFound, load_persona  # noqa: E402
from app.config import settings  # noqa: E402


def main() -> int:
    args = [a for a in sys.argv[1:]]
    persona_name = settings.agent_persona
    if "--persona" in args:
        i = args.index("--persona")
        persona_name = args[i + 1]
        del args[i:i + 2]

    question = " ".join(args) or "In one sentence: what do you do?"

    try:
        persona = load_persona(persona_name)
    except PersonaNotFound as e:
        print(f"✗ {e}")
        return 2

    print(f"→ agent   : {persona.display_name} ({persona.name})")
    print(f"→ agent id: {settings.foundry_agent_id or '(not set)'}")
    print(f"→ question: {question}\n")

    try:
        reply = run(persona, question)
    except FoundryUnavailable as e:
        print(f"✗ {e}")
        return 3
    except Exception as e:                       # noqa: BLE001
        print(f"✗ invocation failed: {type(e).__name__}: {e}")
        return 4

    print(reply.text)
    print(f"\n[mode={reply.mode} model={reply.model} "
          f"tokens={reply.prompt_tokens}/{reply.completion_tokens}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
