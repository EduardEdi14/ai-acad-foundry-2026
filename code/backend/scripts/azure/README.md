# Everything, from the command line

The point of this folder: **nothing in this course requires the portal.** Each script
does with `az` what the session pages do with clicks — and each is idempotent, so you
can run it twice safely.

That is the real argument for a cloud platform. It is not that there is a website; it
is that every resource is an API, so an environment is *code* — reviewable, repeatable,
and rebuildable from nothing.

| Script | What it does |
|---|---|
| `01-provision` | Resource group → Foundry (AI Services) resource → chat + embedding deployments → your data-plane role |
| `02-deploy-model` | Deploy **another** model later, or list what your quota allows, or delete a deployment |
| `03-create-agent` | Creates a hosted agent through the Agent Service REST API (`az rest`) |
| `04-invoke-agent` | The full agent loop from the shell: thread → message → run → answer |
| `05-inspect` | Everything you own: deployments, quota, agents, roles |
| `06-teardown` | Deletes the resource group — the one-command cleanup |
| `07-provision-search` | Creates an Azure AI Search service — the managed alternative to the Qdrant container |

Both shells are provided: `.ps1` for PowerShell, `.sh` for bash/zsh.

```powershell
cd code/backend/scripts/azure
./01-provision.ps1                       # accepts -ResourceGroup / -Name / -Location
./02-deploy-model.ps1                    # no args = show what you can deploy
./02-deploy-model.ps1 -Model gpt-4.1-mini -DeploymentName fast -Capacity 20
./03-create-agent.ps1 -Persona lyrical   # reads app/agents/personas/lyrical.json
./04-invoke-agent.ps1 -Question "Why was my card blocked?"
./05-inspect.ps1
./07-provision-search.ps1 -Sku free      # -Keyless for Entra instead of an admin key
```

```bash
cd code/backend/scripts/azure
./01-provision.sh
./02-deploy-model.sh                     # no args = show what you can deploy
./02-deploy-model.sh gpt-4.1-mini fast 20
./03-create-agent.sh lyrical
./04-invoke-agent.sh "Why was my card blocked?"
./07-provision-search.sh libra-ai-acad srch-libra-acad swedencentral free
```

## The same thing in Python

Every script here has a Python twin, so you can show the identical operation through
both surfaces — which is the clearest way to make the point that the CLI is not magic,
just another client of the same REST API:

| Shell | Python |
|---|---|
| `03-create-agent` | `uv run python scripts/deploy_agent.py <persona>` |
| `04-invoke-agent` | `uv run python scripts/invoke_agent.py "question"` |
| `05-inspect` | `uv run python examples/09_list_deployments.py` |

## Notes

- **Quota is per subscription, per region, per model.** `01-provision` picks the first
  chat model you actually have quota for, and says which one it chose. If it finds
  none, it prints the quota table so you can see why.
- **Agent creation is Entra-only** — `az rest` uses your `az login` token. API keys are
  refused by the Agent Service.
- Model deployment names are what your code references. The scripts keep the deployment
  name equal to the model name to avoid a class of confusion.
