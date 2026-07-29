#!/usr/bin/env bash
# Create an Azure AI Search service — the managed alternative to the Qdrant container.
#
#   ./07-provision-search.sh [resource-group] [name] [location] [sku]
#
# Idempotent: every step checks before it creates. The index itself is created by
# the application (POST /tools/azure-search/sync), because its vector field has to
# match the dimension of whatever embedding model you deployed.
set -euo pipefail

RG=${1:-libra-ai-acad}
NAME=${2:-srch-libra-acad}
LOCATION=${3:-swedencentral}
SKU=${4:-basic}          # free | basic | standard

step() { printf '\n\033[36m[%s] %s\033[0m\n' "$1" "$2"; }

step 0 "Signed-in identity and subscription"
az account show --query '{user:user.name, subscription:name, id:id}' -o tsv | tr '\t' '\n' | sed 's/^/    /'

step 1 "Resource group '$RG'"
if [ "$(az group exists --name "$RG")" = "true" ]; then
  echo "    exists"
else
  az group create --name "$RG" --location "$LOCATION" -o none
  echo "    created in $LOCATION"
fi

# free  : 1 index, 50 MB, no SLA, one per subscription — enough for this course
# basic : 15 indexes, 2 GB, SLA, ~EUR 70/month
# The sku CANNOT be changed later; you delete and recreate.
step 2 "Search service '$NAME' (sku: $SKU)"
if az search service show --name "$NAME" --resource-group "$RG" -o none 2>/dev/null; then
  echo "    exists"
else
  az search service create \
    --name "$NAME" --resource-group "$RG" \
    --sku "$SKU" --location "$LOCATION" \
    --partition-count 1 --replica-count 1 \
    --auth-options aadOrApiKey --aad-auth-failure-mode http403 -o none
  echo "    created — this takes a minute or two"
fi

ENDPOINT="https://$NAME.search.windows.net"

# Two lanes, exactly like the Foundry resource: an admin key is simple and works
# inside a container, but it is a secret with full read/write on every index.
step 3 "Admin key"
KEY=$(az search admin-key show --service-name "$NAME" --resource-group "$RG" --query primaryKey -o tsv)
echo "    ${KEY:0:6}… (read/write on every index)"

step 4 "Configuration — paste into code/backend/.env"
cat <<EOF

  AZURE_SEARCH_ENDPOINT=$ENDPOINT
  AZURE_SEARCH_INDEX=libra-docs
  AZURE_SEARCH_KEY=$KEY

EOF

step 5 "Next"
cat <<'EOF'
    The service is empty. Create and fill the index from the app:

      POST http://localhost:7799/tools/azure-search/sync
           { "text": "...", "strategy": "sentence", "source": "handbook" }

    then compare the three retrieval modes:

      POST /tools/azure-search/query  { "query": "...", "mode": "keyword" }
      POST /tools/azure-search/query  { "query": "...", "mode": "vector"  }
      POST /tools/azure-search/query  { "query": "...", "mode": "hybrid"  }
EOF
