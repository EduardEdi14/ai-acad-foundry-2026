#!/usr/bin/env bash
# Give the container an identity of its own, so the whole application can run in
# Docker with no `az login` and no API key.
#
#   ./09-create-service-principal.sh [name] [resource-group] [years]
#
# A container cannot read your `az login`: that token cache lives in your home
# directory and the container has its own filesystem. So a container on a laptop
# is anonymous, falls back to an API key, and loses everything that requires
# Microsoft Entra - the Foundry Agent Service and every control-plane call.
#
# A service principal fixes that. DefaultAzureCredential tries EnvironmentCredential
# first, so three variables in .env are all it takes - no code changes anywhere.
# In Azure you would use a managed identity instead and have no secret at all.
#
# Idempotent: if the principal exists its secret is reset rather than erroring.
set -euo pipefail

NAME=${1:-sp-libra-acad-container}
RG=${2:-libra-ai-acad}
YEARS=${3:-1}

step() { printf '\n\033[36m[%s] %s\033[0m\n' "$1" "$2"; }

step 0 "Signed-in identity"
az account show --query '{user:user.name, subscription:name, tenant:tenantId}' -o tsv | tr '\t' '\n' | sed 's/^/    /'

SCOPE=$(az group show --name "$RG" --query id -o tsv)
echo "    scope        : $RG"

# Scoped to the resource group, not the subscription. Everything this application
# touches lives in one group, so the identity has no reach beyond it.
step 1 "Service principal '$NAME'"
EXISTING=$(az ad sp list --display-name "$NAME" --query "[0].appId" -o tsv)

# `|| true` so that a permission failure reaches the explanation below instead of
# being swallowed by `set -e` with nothing but the raw Azure error on screen.
if [ -n "$EXISTING" ]; then
  echo "    exists ($EXISTING) - resetting its secret"
  SP=$(az ad sp credential reset --id "$EXISTING" --years "$YEARS" -o json) || SP=""
else
  SP=$(az ad sp create-for-rbac --name "$NAME" --years "$YEARS" \
         --role "Cognitive Services User" --scopes "$SCOPE" -o json) || SP=""
fi

read -r APP_ID PASSWORD TENANT <<<"$(printf '%s' "${SP:-\{\}}" | python3 -c \
  'import sys,json; d=json.load(sys.stdin); print(d.get("appId",""), d.get("password",""), d.get("tenant",""))')"

# Creating a service principal is a DIRECTORY operation, not a subscription one. Owning a
# subscription does not imply the right to register an application in the tenant, and most
# managed tenants (universities, banks) switch that right off for ordinary users. sudo
# changes nothing - the permission lives in Entra.
if [ -z "$APP_ID" ]; then
  TENANT_ID=$(az account show --query tenantId -o tsv)
  USER_NAME=$(az account show --query user.name -o tsv)
  cat >&2 <<EOF

  Could not create the service principal.

  If the error above says 'Insufficient privileges', this is a tenant policy, not a
  problem with this script. Ask whoever administers tenant $TENANT_ID for ONE of:

    - the 'Application Developer' Entra role for $USER_NAME, or
    - Entra ID > Users > User settings > 'Users can register applications' = Yes, or
    - a service principal created for you, and its appId / secret / tenant

  Until then the container falls back to key authentication, which is enough for chat,
  embeddings, speech, Azure AI Search and every local agent. Only the hosted Foundry
  Agent Service and the Azure control-plane panel need Entra:

    DOCKER_AZURE_AI_AUTH=key      (the default in .env)

EOF
  exit 1
fi

if [ -z "$EXISTING" ]; then echo "    created ($APP_ID)"; fi

# The object id is what role assignments use - it is NOT the same as the app id.
OBJECT_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv)

# One role per capability. Read them as a list of what the container may do.
step 2 "Role assignments"
for ROLE in "Cognitive Services User" "Azure AI User" "Search Index Data Contributor"; do
  HELD=$(az role assignment list --assignee "$OBJECT_ID" --scope "$SCOPE" \
           --query "[?roleDefinitionName=='$ROLE'] | length(@)" -o tsv)
  if [ "$HELD" = "0" ]; then
    if az role assignment create --assignee-object-id "$OBJECT_ID" \
         --assignee-principal-type ServicePrincipal \
         --role "$ROLE" --scope "$SCOPE" -o none 2>/dev/null; then
      echo "    granted  : $ROLE"
    else
      echo "    SKIPPED  : $ROLE (you may lack permission to assign it)"
    fi
  else
    echo "    already  : $ROLE"
  fi
done

step 3 "Configuration"
ENV_FILE="$(dirname "$0")/../../.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "    no .env found - here are the values:"
  printf '\n  DOCKER_AZURE_AI_AUTH=identity\n  AZURE_CLIENT_ID=%s\n  AZURE_CLIENT_SECRET=%s\n  AZURE_TENANT_ID=%s\n\n' \
    "$APP_ID" "$PASSWORD" "$TENANT"
else
  python3 - "$ENV_FILE" "$APP_ID" "$PASSWORD" "$TENANT" <<'PY'
import pathlib, re, sys
path, app_id, password, tenant = sys.argv[1:5]
p = pathlib.Path(path)
text = p.read_text(encoding="utf-8")
for key, value in (("DOCKER_AZURE_AI_AUTH", "identity"), ("AZURE_CLIENT_ID", app_id),
                   ("AZURE_CLIENT_SECRET", password), ("AZURE_TENANT_ID", tenant)):
    line = f"{key}={value}"
    text, n = re.subn(rf"(?m)^{key}=.*$", line, text)
    if not n:
        text = text.rstrip("\n") + "\n" + line + "\n"
p.write_text(text, encoding="utf-8")
print("    written to", path)
PY
  echo "    secret shown once by Azure and never again - it is only in .env now"
fi

step 4 "Next"
cat <<'EOF'
    The whole stack can now run in Docker, keyless:

      cd code/backend
      docker compose up -d --build

    Then prove the container has a real identity - the call that was failing
    before, because a key cannot reach the Agent Service:

      curl http://localhost:7799/agents
      #  look for:  "foundry": { "available": true, "reason": null }

    Console: http://localhost:7800

    Role assignments take a few seconds to propagate. If the first call reports
    unavailable, wait a minute and repeat it before changing anything.
EOF
