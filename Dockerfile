# Repo Expert backend — FastAPI served by uvicorn.
# Multi-stage: install deps with uv into a venv, then run on a slim base.

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies first (cached unless lockfile/manifest change).
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Install the project itself.
COPY src ./src
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


FROM python:3.12-slim-bookworm AS runtime

# Non-root runtime user.
RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

# Bring the built virtualenv and the source.
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/src /app/src

# Port 7860 is the Hugging Face Spaces default for Docker SDK apps.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    REPO_EXPERT_INSTANCE=public \
    PORT=7860

USER appuser

EXPOSE 7860

# Secrets are injected as env vars at run time (never baked into the image).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request,sys; p=os.environ.get('PORT','7860'); sys.exit(0 if urllib.request.urlopen(f'http://localhost:{p}/health').status==200 else 1)"

# Honor $PORT (HF Spaces injects it); falls back to 7860 for local runs.
CMD ["sh", "-c", "uvicorn repo_expert.api.app:app --host 0.0.0.0 --port ${PORT:-7860}"]
