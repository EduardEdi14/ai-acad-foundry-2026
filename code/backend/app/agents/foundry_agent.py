"""The hosted agent — the same persona, living in Azure AI Foundry Agent Service.

Difference from local_agent.py, in one sentence: there, your process owns the
loop; here, Azure owns it. You create an *agent* (a stored definition), open a
*thread* (a conversation), add a message, and start a *run* — the platform
executes it, calls any tools the agent is allowed to use, and writes the answer
back into the thread.

What that buys you: the agent exists independently of your app (other systems can
call it), conversation state is managed for you, tool execution is orchestrated,
and every run is traceable in the portal. What it costs: an Azure dependency and
a preview-era SDK surface.

Requires:  pip install azure-ai-projects
           AZURE_AI_PROJECT_ENDPOINT   (Foundry portal → your project → Overview)
           an identity with the Azure AI User / Developer role on the project
"""
from __future__ import annotations

from functools import lru_cache

from ..config import settings
from .local_agent import AgentReply, build_user_prompt
from .persona import Persona


class FoundryUnavailable(Exception):
    """Raised with an instructive message when the hosted lane cannot be used."""


def _require_config() -> None:
    if not settings.azure_ai_project_endpoint:
        raise FoundryUnavailable(
            "AZURE_AI_PROJECT_ENDPOINT is not set. Copy it from the Foundry portal "
            "(your project → Overview → project endpoint) into .env. "
            "See the Session 4 page, 'Deploying the agent to Foundry'."
        )


@lru_cache(maxsize=1)
def get_project_client():
    """One AIProjectClient, authenticated exactly like every other Azure client."""
    _require_config()
    try:
        from azure.ai.projects import AIProjectClient
    except ImportError as e:  # pragma: no cover - dependency guidance
        raise FoundryUnavailable(
            "The azure-ai-projects package is not installed. Run: uv sync "
            "(or pip install azure-ai-projects)."
        ) from e

    from azure.identity import DefaultAzureCredential

    if settings.azure_ai_auth.lower() == "key":
        raise FoundryUnavailable(
            "The Agent Service requires Microsoft Entra authentication — API keys are "
            "not accepted. Set AZURE_AI_AUTH=identity and run `az login`."
        )

    return AIProjectClient(
        endpoint=settings.azure_ai_project_endpoint,
        credential=DefaultAzureCredential(),
    )


def deploy(persona: Persona, model: str | None = None) -> dict:
    """Create (or update) the hosted agent from a persona file. Returns its id.

    Run this once per persona — or after editing the JSON — via
    `python scripts/deploy_agent.py <persona>`.
    """
    client = get_project_client()
    model = model or settings.azure_ai_chat_deployment
    instructions = persona.system_prompt(grounded=True)

    agents = client.agents
    existing = None
    try:
        for a in agents.list_agents():
            if getattr(a, "name", None) == persona.name:
                existing = a
                break
    except Exception:
        existing = None  # listing is optional — creation still works

    if existing is not None:
        agent = agents.update_agent(
            agent_id=existing.id,
            model=model,
            name=persona.name,
            description=persona.description,
            instructions=instructions,
        )
        action = "updated"
    else:
        agent = agents.create_agent(
            model=model,
            name=persona.name,
            description=persona.description,
            instructions=instructions,
        )
        action = "created"

    return {
        "action": action,
        "agent_id": agent.id,
        "name": persona.name,
        "model": model,
        "instructions_preview": instructions[:280],
    }


def run(
    persona: Persona,
    question: str,
    chunks: list[dict] | None = None,
    agent_id: str | None = None,
) -> AgentReply:
    """Invoke the hosted agent: thread → message → run → read the answer."""
    client = get_project_client()
    agent_id = agent_id or settings.foundry_agent_id
    if not agent_id:
        raise FoundryUnavailable(
            "FOUNDRY_AGENT_ID is not set. Deploy the agent first: "
            "`python scripts/deploy_agent.py " + persona.name + "` and copy the printed id into .env."
        )

    user = build_user_prompt(question, chunks or [])
    agents = client.agents

    thread = agents.threads.create()
    agents.messages.create(thread_id=thread.id, role="user", content=user)
    run_obj = agents.runs.create_and_process(thread_id=thread.id, agent_id=agent_id)

    status = getattr(run_obj, "status", None)
    if str(status).lower().endswith("failed"):
        raise FoundryUnavailable(
            f"The run failed on Azure's side: {getattr(run_obj, 'last_error', 'no detail')}"
        )

    answer = ""
    for message in agents.messages.list(thread_id=thread.id):
        if getattr(message, "role", None) != "assistant":
            continue
        for part in getattr(message, "content", []) or []:
            text = getattr(getattr(part, "text", None), "value", None)
            if text:
                answer = text
                break
        if answer:
            break

    usage = getattr(run_obj, "usage", None)
    return AgentReply(
        text=answer or "(the run produced no assistant message)",
        mode="foundry",
        persona=persona.name,
        system_prompt="(stored in Foundry with the agent definition)",
        prompt_sent=user,
        provider="azure-foundry-agent",
        model=settings.azure_ai_chat_deployment,
        prompt_tokens=getattr(usage, "prompt_tokens", None),
        completion_tokens=getattr(usage, "completion_tokens", None),
    )
