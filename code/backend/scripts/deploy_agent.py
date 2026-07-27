#!/usr/bin/env python
"""Publish a persona to the Azure AI Foundry Agent Service.

    uv run python scripts/deploy_agent.py lyrical

Reads app/agents/personas/<name>.json, creates (or updates) an agent with the
same name in your Foundry project, and prints the agent id to put in .env.

Prerequisites
    AZURE_AI_PROJECT_ENDPOINT   in .env   (Foundry portal → project → Overview)
    AZURE_AI_CHAT_DEPLOYMENT    in .env   (the deployment the agent will run on)
    az login                              (Entra auth — keys are not accepted here)
    Role: Azure AI User (or Developer) on the project
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.foundry_agent import FoundryUnavailable, deploy  # noqa: E402
from app.agents.persona import PersonaNotFound, available_names, load_persona  # noqa: E402
from app.config import settings  # noqa: E402


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else settings.agent_persona
    try:
        persona = load_persona(name)
    except PersonaNotFound as e:
        print(f"✗ {e}")
        return 2

    print(f"→ deploying persona '{persona.name}' ({persona.display_name})")
    print(f"  project : {settings.azure_ai_project_endpoint or '(not set)'}")
    print(f"  model   : {settings.azure_ai_chat_deployment}")

    try:
        result = deploy(persona)
    except FoundryUnavailable as e:
        print(f"✗ {e}")
        return 3
    except Exception as e:                       # noqa: BLE001 - surface anything
        print(f"✗ deployment failed: {type(e).__name__}: {e}")
        return 4

    print(f"\n✓ agent {result['action']}")
    print(f"  id   : {result['agent_id']}")
    print(f"  name : {result['name']}")
    print("\nNext:")
    print(f"  1. put this in .env →  FOUNDRY_AGENT_ID={result['agent_id']}")
    print("  2. set               →  AGENT_MODE=foundry")
    print('  3. call /ask with    →  {"question": "...", "agent_mode": "foundry"}')
    print(f"\n  (personas available: {', '.join(available_names())})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
