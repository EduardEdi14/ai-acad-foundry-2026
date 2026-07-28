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


def deploy_one(name: str) -> int:
    try:
        persona = load_persona(name)
    except PersonaNotFound as e:
        print(f"✗ {e}")
        return 2

    print(f"→ deploying persona '{persona.name}' ({persona.display_name})")
    try:
        result = deploy(persona)
    except FoundryUnavailable as e:
        print(f"✗ {e}")
        return 3
    except Exception as e:                       # noqa: BLE001 - surface anything
        print(f"✗ deployment failed: {type(e).__name__}: {e}")
        return 4

    portal = result.get("portal", {})
    print(f"  ✓ agent service : {result['action']}  ({result['agent_id']})")
    print(f"  ✓ portal        : {portal.get('action', '?')}"
          + (f"  — {portal['error']}" if portal.get("error") else ""))
    return 0


def main() -> int:
    args = sys.argv[1:]
    print(f"  project : {settings.azure_ai_project_endpoint or '(not set)'}")
    print(f"  model   : {settings.azure_ai_chat_deployment}\n")

    if args and args[0] in ("--all", "-a"):
        names = available_names()
        print(f"deploying all {len(names)} personas: {', '.join(names)}\n")
        failures = 0
        for name in names:
            failures += 1 if deploy_one(name) else 0
        print(f"\n{len(names) - failures}/{len(names)} deployed.")
        print("They are now runnable (agent_mode=foundry) and visible in the Foundry portal.")
        return 1 if failures else 0

    code = deploy_one(args[0] if args else settings.agent_persona)
    if code:
        return code

    print("\nNext:")
    print('  · run it     →  /ask with {"agent": "<name>", "agent_mode": "foundry"}')
    print("  · see it     →  ai.azure.com → your project → Agents")
    print(f"  · deploy all →  uv run python scripts/deploy_agent.py --all")
    print(f"\n  (personas available: {', '.join(available_names())})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
