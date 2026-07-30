FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /srv

# Dependencies first — cached until pyproject/lock change
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app

EXPOSE 7799

# A shippable default: the code is IN the image, and the server does not watch the
# filesystem for edits. Development puts --reload back through `command:` in
# docker-compose.yml, where the source is also bind-mounted — the two belong
# together, and neither belongs in an image you push to a registry.
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7799"]
