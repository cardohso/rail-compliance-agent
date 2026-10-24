# The API (POST /check, GET /health) with the rail assistant's retrieval baked in: its corpus at a
# pinned commit and a vector index built at image build time, so a container needs no network for
# search. The model key is NOT in the image: pass it at run time (-e GEMINI_API_KEY=...).
#
#   docker build -t rail-compliance-agent .
#   docker run --rm -p 8000:8000 --env-file .env rail-compliance-agent
#
# Two stages: the build stage needs git (the rail-rag dependency and its corpus come from GitHub);
# the runtime image does not, and runs as a non-root user.

# ---- build ----------------------------------------------------------------------------------
FROM python:3.12-slim AS build

# Keep in step with RAIL_RAG_REF in .github/workflows/eval.yml and the `rail-rag` pin in pyproject.
ARG RAIL_RAG_REF=d63cc5f37fcc93100b7bc25a61a63d4507d24248

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    FASTEMBED_CACHE_PATH=/models \
    HF_HUB_DISABLE_TELEMETRY=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv

WORKDIR /app
# Dependencies first, so code changes do not reinstall them.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --group local --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --group local --no-editable

# The rail assistant's corpus, pinned, and its index (downloads the embedding model into /models).
RUN git init -q /rail \
    && git -C /rail fetch --depth 1 https://github.com/cardohso/rail-regulation-rag.git "$RAIL_RAG_REF" \
    && git -C /rail checkout -q FETCH_HEAD
RUN RAIL_RAG_DATA_DIR=/rail/data /app/.venv/bin/python -m rail_rag.index

# ---- runtime --------------------------------------------------------------------------------
FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/cardohso/rail-compliance-agent" \
      org.opencontainers.image.description="Checks a train design spec against the EU PRM TSI. Not legal advice." \
      org.opencontainers.image.licenses="MIT"

RUN useradd --create-home --uid 1000 app

COPY --from=build --chown=app:app /app/.venv /app/.venv
# Only what retrieval needs; the index directory must be writable (Qdrant keeps a lock file).
COPY --from=build --chown=app:app /rail/data/sources.yaml /data/rail/sources.yaml
COPY --from=build --chown=app:app /rail/data/processed /data/rail/processed
COPY --from=build --chown=app:app /rail/data/index /data/rail/index
COPY --from=build --chown=app:app /models /models

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    RAIL_RAG_DATA_DIR=/data/rail \
    FASTEMBED_CACHE_PATH=/models \
    HF_HUB_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    SEARCH_BACKEND=local \
    SEARCH_CACHE_DIR=/tmp/cache/search \
    LLM_CACHE_DIR=/tmp/cache/llm

USER app
WORKDIR /home/app

EXPOSE 8000
# /health answers 200 whenever the process is up; its body says whether /check is ready.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"]

CMD ["uvicorn", "rail_compliance.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
