#!/usr/bin/env bash
# Deploy an additional model into an existing Foundry resource, from the CLI only.
#   ./02-deploy-model.sh                      # list what you can deploy
#   ./02-deploy-model.sh gpt-4.1-mini         # deploy it
#   ./02-deploy-model.sh gpt-4.1-mini fast 20 # custom deployment name and capacity
set -euo pipefail

MODEL="${1:-}"
DEPLOYMENT="${2:-${1:-}}"
CAPACITY="${3:-50}"
RG="${RG:-libra-ai-acad}"
NAME="${NAME:-libra-ai-acad-resource}"
LOCATION="${LOCATION:-swedencentral}"
SKU="${SKU:-GlobalStandard}"

head() { printf "\n\033[36m%s\033[0m\n%s\n" "$1" "----------------------------------------------------------------"; }

head "CURRENT DEPLOYMENTS in $NAME"
az cognitiveservices account deployment list --name "$NAME" --resource-group "$RG" \
  --query "[].{deployment:name, model:properties.model.name, sku:sku.name, tpm:sku.capacity, state:properties.provisioningState}" -o table

free_quota() {
  az cognitiveservices usage list --location "$LOCATION" \
    --query "[?name.value=='OpenAI.$SKU.$1'].[limit,currentValue]" -o tsv 2>/dev/null \
    | awk '{printf "%d", $1-$2}'
}

if [ -z "$MODEL" ]; then
  head "AVAILABLE IN $LOCATION (with your remaining quota)"
  az cognitiveservices model list --location "$LOCATION" \
    --query "[?kind=='AIServices'].model.name" -o tsv | sort -u \
    | grep -E 'gpt|embedding|phi|mistral|llama|deepseek' \
    | grep -vE 'audio|realtime|transcribe|image|sora|codex|dalle' \
    | while read -r m; do
        f=$(free_quota "$m"); f="${f:-0}"
        [ "$f" -gt 0 ] && printf "  %-28s free quota: %sK TPM\n" "$m" "$f"
      done
  echo
  echo "Quota is per subscription, per region, per model — a model with 0 free quota"
  echo "cannot be deployed here even though it appears in the catalog."
  echo
  echo "Deploy one with:  ./02-deploy-model.sh <model> [deployment-name] [capacity]"
  exit 0
fi

FREE=$(free_quota "$MODEL"); FREE="${FREE:-0}"
if [ "$FREE" -le 0 ]; then
  echo "No free quota for $MODEL ($SKU) in $LOCATION. Pick another model or region."; exit 1
fi
if [ "$FREE" -lt "$CAPACITY" ]; then
  echo "Only ${FREE}K TPM free; reducing capacity from ${CAPACITY}K to ${FREE}K."
  CAPACITY="$FREE"
fi

VERSION=$(az cognitiveservices model list --location "$LOCATION" \
  --query "[?kind=='AIServices' && model.name=='$MODEL'] | [-1].model.version" -o tsv)
[ -n "$VERSION" ] || { echo "Model '$MODEL' is not offered in $LOCATION."; exit 1; }

head "DEPLOYING $MODEL -> deployment '$DEPLOYMENT'"
echo "  version  : $VERSION"
echo "  sku      : $SKU"
echo "  capacity : ${CAPACITY}K tokens/minute"
echo

az cognitiveservices account deployment create --name "$NAME" --resource-group "$RG" \
  --deployment-name "$DEPLOYMENT" --model-name "$MODEL" --model-version "$VERSION" \
  --model-format OpenAI --sku-name "$SKU" --sku-capacity "$CAPACITY" -o none

echo "Deployed."
az cognitiveservices account deployment show --name "$NAME" --resource-group "$RG" \
  --deployment-name "$DEPLOYMENT" \
  --query "{deployment:name, model:properties.model.name, state:properties.provisioningState, tpm:sku.capacity}" -o yaml

cat <<EOF

Use it from code by NAME:
  .env  ->  AZURE_AI_CHAT_DEPLOYMENT=$DEPLOYMENT
  or per call:  client.complete(model="$DEPLOYMENT", ...)

It is also visible now in ai.azure.com -> Models + endpoints.
EOF
