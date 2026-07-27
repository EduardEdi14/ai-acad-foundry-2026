"""09 · The control plane from Python — what actually exists in your resource.

Everything the portal shows you is an API call. This one asks Azure Resource Manager
to list your model deployments, using the same identity as every other script.

    uv run python examples/09_list_deployments.py
"""
from __future__ import annotations

import httpx

from _bootstrap import banner
from app.config import settings
from azure.identity import DefaultAzureCredential

banner("09 · the control plane: listing your deployments")

if not (settings.azure_resource_group and settings.azure_foundry_resource):
    raise SystemExit(
        "Set AZURE_RESOURCE_GROUP and AZURE_FOUNDRY_RESOURCE in .env first "
        "(they are the coordinates of your Foundry resource)."
    )

credential = DefaultAzureCredential()
token = credential.get_token("https://management.azure.com/.default")   # ← the ARM scope

subscription = httpx.get(
    "https://management.azure.com/subscriptions",
    params={"api-version": "2022-12-01"},
    headers={"Authorization": f"Bearer {token.token}"},
    timeout=30,
).json()["value"][0]

sub_id = subscription["subscriptionId"]
print(f"subscription : {subscription['displayName']}  ({sub_id})")
print(f"resource     : {settings.azure_foundry_resource}  in  {settings.azure_resource_group}\n")

url = (
    f"https://management.azure.com/subscriptions/{sub_id}"
    f"/resourceGroups/{settings.azure_resource_group}"
    f"/providers/Microsoft.CognitiveServices/accounts/{settings.azure_foundry_resource}"
    f"/deployments"
)
print(f"GET {url}\n     ?api-version=2023-05-01\n")

response = httpx.get(
    url,
    params={"api-version": "2023-05-01"},
    headers={"Authorization": f"Bearer {token.token}"},
    timeout=30,
)
response.raise_for_status()

print(f"{'deployment':<28} {'model':<26} {'sku':<16} {'TPM':>5}  state")
print("─" * 92)
for item in response.json().get("value", []):
    props = item.get("properties", {})
    model = props.get("model", {})
    sku = item.get("sku", {})
    print(f"{item['name']:<28} {model.get('name', '?'):<26} {sku.get('name', '?'):<16} "
          f"{sku.get('capacity', '?'):>5}  {props.get('provisioningState')}")

print("""
That is the same list the portal renders — the portal is just another client of this
API. Anything you can see, you can script; anything you can script, a pipeline can run.
""")
