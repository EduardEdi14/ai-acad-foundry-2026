FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /srv

# Dependencies first — cached until pyproject/lock change
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app

EXPOSE 7799

# --reload + the compose bind-mount of ./app = live reload inside the container
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7799", "--reload"]
