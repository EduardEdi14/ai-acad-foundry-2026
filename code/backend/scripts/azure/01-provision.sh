#!/usr/bin/env bash
# Build a complete Foundry environment from nothing. Idempotent.
#   ./01-provision.sh [resource-group] [resource-name] [location]
set -euo pipefail

RG="${1:-libra-ai-acad}"
NAME="${2:-libra-ai-acad-resource}"
LOCATION="${3:-swedencentral}"
EMBEDDING="text-embedding-3-small"
CAPACITY=50

step() { printf "\n\033[36m[%s] %s\033[0m\n" "$1" "$2"; }

step 0 "Signed-in identity and subscription"
az account show --query "{user:user.name, subscription:name, id:id}" -o tsv | sed 's/^/    /'

step 1 "Resource group '$RG' in $LOCATION"
if [ "$(az group exists --name "$RG")" = "true" ]; then
  echo "    already exists"
else
  az group create --name "$RG" --location "$LOCATION" -o none && echo "    created"
fi

step 2 "Foundry resource '$NAME'"
if az cognitiveservices account show --name "$NAME" --resource-group "$RG" -o none 2>/dev/null; then
  echo "    already exists"
else
  az cognitiveservices account create --name "$NAME" --resource-group "$RG" \
     --location "$LOCATION" --kind AIServices --sku S0 --yes -o none
  echo "    created"
fi

step 3 "Choosing a chat model with available quota"
CHAT=""
for m in gpt-5-mini gpt-4.1-mini gpt-4o-mini gpt-5-nano gpt-4o; do
  free=$(az cognitiveservices usage list --location "$LOCATION" \
         --query "[?name.value=='OpenAI.GlobalStandard.$m'].[limit,currentValue]" -o tsv 2>/dev/null \
         | awk '{printf "%d", $1-$2}')
  free="${free:-0}"
  printf "    %-16s free quota: %s\n" "$m" "$free"
  if [ -z "$CHAT" ] && [ "$free" -ge "$CAPACITY" ]; then CHAT="$m"; fi
done
if [ -z "$CHAT" ]; then
  echo "    No chat model has ${CAPACITY}K TPM free in $LOCATION."
  echo "    Quota is per subscription, per region, per model — lower CAPACITY, change region, or request quota."
  exit 1
fi
echo "    -> using $CHAT"

step 4 "Model deployments"
for model in "$CHAT" "$EMBEDDING"; do
  if az cognitiveservices account deployment show --name "$NAME" --resource-group "$RG" \
       --deployment-name "$model" -o none 2>/dev/null; then
    echo "    $model — already deployed"
  else
    version=$(az cognitiveservices model list --location "$LOCATION" \
              --query "[?kind=='AIServices' && model.name=='$model'] | [-1].model.version" -o tsv)
    az cognitiveservices account deployment create --name "$NAME" --resource-group "$RG" \
       --deployment-name "$model" --model-name "$model" --model-version "$version" \
       --model-format OpenAI --sku-name GlobalStandard --sku-capacity "$CAPACITY" -o none
    echo "    $model ($version) — deployed"
  fi
done

step 5 "Granting yourself the data-plane role"
ME=$(az ad signed-in-user show --query id -o tsv)
RES=$(az cognitiveservices account show --name "$NAME" --resource-group "$RG" --query id -o tsv)
for role in "Cognitive Services User" "Azure AI User"; do
  if [ "$(az role assignment list --assignee "$ME" --scope "$RES" --role "$role" --query "length(@)" -o tsv)" != "0" ]; then
    echo "    '$role' — already assigned"
  else
    az role assignment create --assignee "$ME" --scope "$RES" --role "$role" -o none 2>/dev/null \
      && echo "    '$role' — assigned" || echo "    '$role' — could not assign (may need an administrator)"
  fi
done

cat <<EOF

--- put this in code/backend/.env ------------------------------
LLM_PROVIDER=azure
EMBEDDING_PROVIDER=azure
AZURE_AI_ENDPOINT=https://$NAME.services.ai.azure.com/models
AZURE_AI_AUTH=identity
AZURE_AI_CHAT_DEPLOYMENT=$CHAT
AZURE_AI_EMBEDDING_DEPLOYMENT=$EMBEDDING
AZURE_AI_PROJECT_ENDPOINT=https://$NAME.services.ai.azure.com/api/projects/proj-default
AZURE_RESOURCE_GROUP=$RG
AZURE_FOUNDRY_RESOURCE=$NAME
AZURE_LOCATION=$LOCATION
----------------------------------------------------------------

Verify with:  uv run python examples/02_hello_foundry.py
EOF
