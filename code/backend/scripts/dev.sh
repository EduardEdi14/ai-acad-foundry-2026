#!/usr/bin/env bash
# The teaching lane: the API on your machine, Qdrant and the console in Docker.
#
#   ./dev.sh [--port 7799] [--bind-all] [--skip-docker] [--no-reload]
#
# This is the combination that gives you everything without asking anyone to
# install anything they do not have:
#
#   the API      on your machine, under uv - the only process that needs YOUR
#                Azure identity. `az login` writes its token cache into your home
#                directory and DefaultAzureCredential reads it from there, which
#                is what makes the Foundry Agent Service work.
#   the console  in Docker - because students do not have Node installed.
#   Qdrant       in Docker - because it is a database.
#
# The alternative, everything in Docker, needs a service principal to reach the
# Agent Service (scripts/azure/09-create-service-principal.sh). If your tenant
# will not let you create one, this lane is the answer.
set -euo pipefail

PORT=7799
BIND_ALL=0
SKIP_DOCKER=0
NO_RELOAD=0
while [ $# -gt 0 ]; do
  case "$1" in
    --port)        PORT="$2"; shift 2 ;;
    --bind-all)    BIND_ALL=1; shift ;;
    --skip-docker) SKIP_DOCKER=1; shift ;;
    --no-reload)   NO_RELOAD=1; shift ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
done

step() { printf '\n\033[36m[%s] %s\033[0m\n' "$1" "$2"; }
cd "$(dirname "$0")/.."

# AzureCliCredential does not read the token cache itself; it runs `az`. A shell
# whose PATH lacks the executable fails with "Azure CLI not found on path" even
# though you are perfectly well logged in.
step 0 "Azure CLI"
command -v az >/dev/null || { echo "    az not found: https://learn.microsoft.com/cli/azure/install-azure-cli"; exit 1; }
az account show --query "{user:user.name, sub:name}" -o tsv | sed 's/^/    /' \
  || { echo "    not signed in. Run:  az login"; exit 1; }

step 1 "Configuration"
[ -f .env ] || { echo "    no .env here. Start from: cp .env.example .env"; exit 1; }
if grep -qE '^AZURE_AI_AUTH=identity' .env; then
  echo "    AZURE_AI_AUTH=identity  - the API will use your az login"
else
  echo "    AZURE_AI_AUTH is not 'identity' - hosted agents will be unavailable"
  echo "    (that setting is for THIS process; DOCKER_AZURE_AI_AUTH is the container one)"
fi
if grep -qE '^QDRANT_URL=' .env && ! grep -qE '^QDRANT_URL=.*localhost' .env; then
  echo "    QDRANT_URL is not localhost - the API is NOT in the compose network here"
fi

# A container publishing 7799 and a local uvicorn cannot both have it. The usual
# cause is a previous `docker compose up` with the api service still running.
step 2 "Port $PORT"
if (command -v ss >/dev/null && ss -ltn "sport = :$PORT" | grep -q LISTEN) 2>/dev/null; then
  echo "    in use. If it is the api container:  docker compose stop api"
  echo "    otherwise re-run with --port 7801"
  exit 1
fi
echo "    free"

# The override leaves the `api` service out and points the console at
# host.docker.internal instead of the compose network.
step 3 "Qdrant and the console"
if [ "$SKIP_DOCKER" = "1" ]; then
  echo "    skipped"
else
  docker compose -f docker-compose.yml -f docker-compose.host-api.yml up -d
  echo "    console  http://localhost:7800"
  echo "    qdrant   http://localhost:7833/dashboard"
fi

step 4 "API on this machine"
echo "    swagger  http://localhost:$PORT/docs"
echo "    stop with Ctrl+C - the containers keep running"
echo

ARGS=(app.main:app --port "$PORT")
[ "$NO_RELOAD" = "1" ] || ARGS+=(--reload)
# host.docker.internal reaches the host's loopback on Docker Desktop, so the
# default bind is enough there. On Docker Engine for Linux the name resolves to
# the bridge gateway - a real interface - so the server has to listen on it too.
[ "$BIND_ALL" = "1" ] && ARGS+=(--host 0.0.0.0)

exec uv run uvicorn "${ARGS[@]}"
