"""05 · One credential, many clients — the answer to "is it one API key?"

Builds several clients from a SINGLE DefaultAzureCredential, each asking for a token
scoped to its own service. Adding a capability means adding a role assignment, not
another secret.

    uv run python examples/05_wiring.py
"""
from __future__ import annotations

from _bootstrap import banner
from app.config import settings
from azure.ai.inference import ChatCompletionsClient, EmbeddingsClient
from azure.identity import DefaultAzureCredential

banner("05 · one identity, many services")

AI_SCOPE = "https://cognitiveservices.azure.com/.default"
ARM_SCOPE = "https://management.azure.com/.default"

credential = DefaultAzureCredential()        # ← ONE object, reused everywhere below

print("""
 surface                     endpoint shape                      scope
 ─────────────────────────── ─────────────────────────────────── ──────────────────────────────
 Manage resources            management.azure.com                management.azure.com/.default
 Chat & embeddings           <res>.services.ai.azure.com         cognitiveservices.azure.com/.default
 Projects, agents            <res>.services.ai.azure.com/api/…   cognitiveservices.azure.com/.default
 Vector search               <svc>.search.windows.net            search.azure.com/.default
 Blob storage                <acct>.blob.core.windows.net        storage.azure.com/.default
""")

chat = ChatCompletionsClient(
    endpoint=settings.azure_ai_endpoint, credential=credential, credential_scopes=[AI_SCOPE]
)
embeddings = EmbeddingsClient(
    endpoint=settings.azure_ai_endpoint, credential=credential, credential_scopes=[AI_SCOPE]
)
print("built ChatCompletionsClient and EmbeddingsClient from the same credential\n")

for label, scope in (("AI services", AI_SCOPE), ("Resource Manager", ARM_SCOPE)):
    token = credential.get_token(scope)
    print(f"  token for {label:<18} … {len(token.token)} chars  (different token, same identity)")

reply = chat.complete(
    model=settings.azure_ai_chat_deployment,
    messages=[{"role": "user", "content": "In one sentence: what is an Azure role assignment?"}],
    model_extras={"max_completion_tokens": 2000},
)
print(f"\nchat  → {reply.choices[0].message.content}")
print(f"embed → {len(embeddings.embed(model=settings.azure_ai_embedding_deployment, input=['x']).data[0].embedding)} dimensions")

print("""
The point: with API keys you would now be holding one secret per service, each needing
storage, rotation and an owner. With Entra you hold ONE identity, and each service is
granted to it by a role assignment an administrator can see and revoke centrally.
""")
