#!/usr/bin/env bash
# Create a hosted agent in Foundry Agent Service, from the shell, with no SDK.
#   ./02-create-agent.sh [persona] [resource-name] [project]
set -euo pipefail

PERSONA="${1:-default}"
NAME="${2:-libra-ai-acad-resource}"
PROJECT="${3:-proj-default}"
MODEL="${MODEL:-gpt-5-mini}"
API="2025-05-01"
PROJECT_URL="https://$NAME.services.ai.azure.com/api/projects/$PROJECT"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FILE="$HERE/../../app/agents/personas/$PERSONA.json"
[ -f "$FILE" ] || { echo "No persona '$PERSONA'. Available:"; ls "$HERE/../../app/agents/personas" | sed 's/\.json$//;s/^/  /'; exit 2; }

# compose instructions exactly as app/agents/persona.py does
INSTRUCTIONS=$(python - "$FILE" <<'PY'
import json, sys
p = json.load(open(sys.argv[1], encoding="utf-8"))
parts = [p["instructions"].strip()]
if p.get("style_rules"):
    parts.append("Style rules you must follow:\n" + "\n".join(f"- {r}" for r in p["style_rules"]))
if p.get("require_citations", True):
    parts.append("You are given CONTEXT passages retrieved from the bank's own documents. "
                 "Base your answer on those passages. Cite the passages you use as [1], [2], ... .")
print("\n\n".join(parts))
PY
)
DESCRIPTION=$(python -c "import json,sys;print(json.load(open(sys.argv[1],encoding='utf-8')).get('description',''))" "$FILE")

echo
echo "Agent to create"
echo "  persona : $PERSONA"
echo "  model   : $MODEL"
echo "  project : $PROJECT_URL"
echo

BODY=$(mktemp)
python - "$MODEL" "$PERSONA" "$DESCRIPTION" "$INSTRUCTIONS" > "$BODY" <<'PY'
import json, sys
model, name, description, instructions = sys.argv[1:5]
print(json.dumps({"model": model, "name": name,
                  "description": description, "instructions": instructions}))
PY

EXISTING=$(az rest --method get --url "$PROJECT_URL/assistants?api-version=$API" \
           --resource "https://ai.azure.com" \
           --query "data[?name=='$PERSONA'].id | [0]" -o tsv 2>/dev/null || true)

if [ -n "$EXISTING" ] && [ "$EXISTING" != "None" ]; then
  echo "Updating existing agent $EXISTING ..."
  URL="$PROJECT_URL/assistants/$EXISTING?api-version=$API"
else
  echo "Creating agent ..."
  URL="$PROJECT_URL/assistants?api-version=$API"
fi

RESULT=$(az rest --method post --url "$URL" --resource "https://ai.azure.com" \
         --headers "Content-Type=application/json" --body "@$BODY" -o json)
rm -f "$BODY"

AGENT_ID=$(echo "$RESULT" | python -c "import json,sys;print(json.load(sys.stdin)['id'])")
echo
echo "OK  agent id : $AGENT_ID"
echo
echo "Next:"
echo "  .env  ->  FOUNDRY_AGENT_ID=$AGENT_ID"
echo "  .env  ->  AGENT_MODE=foundry"
echo "  or    ->  ./03-invoke-agent.sh \"your question\" $PERSONA"
