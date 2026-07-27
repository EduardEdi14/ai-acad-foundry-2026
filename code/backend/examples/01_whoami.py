"""01 · Who am I? — proving the identity chain works, before any model is involved.

If this prints a token and an expiry, then your sign-in, the CLI, your Python
environment and DefaultAzureCredential are all correct. Every later failure is
about permissions or endpoints, not about your machine.

    uv run python examples/01_whoami.py
"""
from __future__ import annotations

from datetime import datetime, timezone

from _bootstrap import banner  # noqa: F401
from azure.identity import DefaultAzureCredential

SCOPES = {
    "Azure AI services (chat, embeddings)": "https://cognitiveservices.azure.com/.default",
    "Azure Resource Manager (control plane)": "https://management.azure.com/.default",
}

banner("01 · the identity chain")

credential = DefaultAzureCredential()
print("credential :", type(credential).__name__)
print("\nDefaultAzureCredential tries sources in order and uses the first that answers:")
print("  env vars → managed identity → VS Code → Azure CLI → Azure PowerShell")
print("  On your laptop it is the Azure CLI: your `az login` IS the credential.\n")

for label, scope in SCOPES.items():
    try:
        token = credential.get_token(scope)
        expires = datetime.fromtimestamp(token.expires_on, tz=timezone.utc)
        minutes = (expires - datetime.now(timezone.utc)).total_seconds() / 60
        print(f"✓ {label}")
        print(f"    scope   : {scope}")
        print(f"    token   : {len(token.token)} characters")
        print(f"    expires : {expires:%Y-%m-%d %H:%M:%S} UTC  (in {minutes:.0f} minutes)\n")
    except Exception as e:
        print(f"✗ {label}\n    {type(e).__name__}: {str(e)[:160]}\n")

print("Note the expiry: this is the short-lived credential that replaces a permanent")
print("API key. Nothing durable is stored in your project — there is nothing to leak.")
