#!/usr/bin/env bash
# The full agent loop from the shell: thread -> message -> run -> answer.
#   ./03-invoke-agent.sh "your question" [persona]
set -euo pipefail

QUESTION="${1:-In one sentence: what do you do?}"
PERSONA="${2:-default}"
NAME="${NAME:-libra-ai-acad-resource}"
PROJECT="${PROJECT:-proj-default}"
API="2025-05-01"
PROJECT_URL="https://$NAME.services.ai.azure.com/api/projects/$PROJECT"
RES="https://ai.azure.com"

rest() {  # rest METHOD PATH [JSON]
  local method="$1" path="$2" json="${3:-}"
  local sep="?"; [[ "$path" == *"?"* ]] && sep="&"
  if [ -z "$json" ]; then
    az rest --method "$method" --url "$PROJECT_URL/$path$sep api-version=$API" --resource "$RES" -o json 2>/dev/null \
      || az rest --method "$method" --url "$PROJECT_URL/$path${sep}api-version=$API" --resource "$RES" -o json
  else
    local tmp; tmp=$(mktemp); printf '%s' "$json" > "$tmp"
    az rest --method "$method" --url "$PROJECT_URL/$path${sep}api-version=$API" --resource "$RES" \
       --headers "Content-Type=application/json" --body "@$tmp" -o json
    rm -f "$tmp"
  fi
}
jq_py() { python -c "import json,sys;d=json.load(sys.stdin);$1"; }

AGENT_ID=$(az rest --method get --url "$PROJECT_URL/assistants?api-version=$API" --resource "$RES" \
           --query "data[?name=='$PERSONA'].id | [0]" -o tsv)
if [ -z "$AGENT_ID" ] || [ "$AGENT_ID" = "None" ]; then
  echo "No hosted agent named '$PERSONA'. Create one first:  ./02-create-agent.sh $PERSONA"; exit 2
fi
echo "agent    : $AGENT_ID"
echo "question : $QUESTION"
echo

echo "[1] POST /threads              - open a conversation"
THREAD=$(rest post "threads" '{}' | jq_py "print(d['id'])")
echo "    thread id: $THREAD"

echo "[2] POST /threads/{id}/messages - add the question"
MSG=$(python -c "import json,sys;print(json.dumps({'role':'user','content':sys.argv[1]}))" "$QUESTION")
rest post "threads/$THREAD/messages" "$MSG" > /dev/null

echo "[3] POST /threads/{id}/runs     - ask the platform to execute"
RUN=$(rest post "threads/$THREAD/runs" "{\"assistant_id\":\"$AGENT_ID\"}" | jq_py "print(d['id'])")
STATUS="queued"
for _ in $(seq 1 90); do
  sleep 1
  STATUS=$(rest get "threads/$THREAD/runs/$RUN" | jq_py "print(d['status'])")
  echo "    status: $STATUS"
  [[ "$STATUS" == "completed" || "$STATUS" == "failed" || "$STATUS" == "cancelled" || "$STATUS" == "expired" ]] && break
done
[ "$STATUS" = "completed" ] || { echo "Run ended as '$STATUS'"; exit 3; }

echo "[4] GET  /threads/{id}/messages - read what the agent wrote"
echo
echo "---------------------------------------------------------------"
rest get "threads/$THREAD/messages" | jq_py \
  "print(next(m for m in d['data'] if m['role']=='assistant')['content'][0]['text']['value'])"
echo "---------------------------------------------------------------"
echo
echo "Four HTTP calls. That is the entire Agent Service protocol."
