"""06 · Structured output — turning a prompt into an interface.

Free text is for humans; applications need fields. Asking nicely works until it
doesn't; constraining generation to a JSON schema works every time.

    uv run python examples/06_structured_output.py
"""
from __future__ import annotations

import json

from _bootstrap import banner, show_context
from app.config import settings
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import JsonSchemaFormat
from azure.identity import DefaultAzureCredential

banner("06 · structured output: schema-constrained JSON")
show_context()

SCHEMA = {
    "type": "object",
    "properties": {
        "beneficiary": {"type": "string"},
        "amount": {"type": "number"},
        "currency": {"type": "string"},
        "urgent": {"type": "boolean"},
    },
    "required": ["beneficiary", "amount", "currency", "urgent"],
    "additionalProperties": False,
}

MESSAGES = [
    "Please send 2,500 lei to Maria Ionescu today, it's urgent.",
    "transfer 90 euros to my landlord Andrei Pop, no rush",
]

client = ChatCompletionsClient(
    endpoint=settings.azure_ai_endpoint,
    credential=DefaultAzureCredential(),
    credential_scopes=["https://cognitiveservices.azure.com/.default"],
)

for message in MESSAGES:
    reply = client.complete(
        model=settings.azure_ai_chat_deployment,
        messages=[
            {"role": "system", "content": "Extract the transfer request from the user's message."},
            {"role": "user", "content": message},
        ],
        response_format=JsonSchemaFormat(name="transfer_request", schema=SCHEMA, strict=True),
        model_extras={"max_completion_tokens": 2000},
    )
    data = json.loads(reply.choices[0].message.content)   # guaranteed to match the schema
    print(f"\nin  : {message}")
    print(f"out : {data}")
    print(f"      beneficiary={data['beneficiary']!r}  amount={data['amount']} {data['currency']}  urgent={data['urgent']}")

print("""
The prompt stopped being a wish and became an interface definition. This is also the
mechanism underneath tool calling: an agent is, mechanically, a model emitting
schema-conforming decisions.
""")
