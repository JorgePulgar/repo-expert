# Repo Expert

Agentic RAG that answers questions about any GitHub repo it's pointed at, with
citations. One codebase, two instances selected by config:

- **public** — class deliverable pointed at a serious public repo (FastAPI).
- **portfolio** — recruiter demo pointed at Jorge's portfolio repos + a Career KB.

Stack: Azure AI Search (hybrid + semantic reranker) · LangGraph (corrective/agentic
RAG) · FastAPI · Azure OpenAI.

> 🚧 Early development. This is a minimal run stub; the full bilingual README and
> architecture docs land in Phase 7. Development is organized in phases under
> [`docs/phases/`](docs/phases/README.md).

## Requirements
- [uv](https://docs.astral.sh/uv/) (manages Python 3.12 automatically)

## Setup
```bash
uv sync                      # install deps into .venv
cp .env.example .env         # then fill in Azure + GitHub keys
```

## Select the instance
Set in `.env`:
```bash
REPO_EXPERT_INSTANCE=public   # or: portfolio
```

## Develop
```bash
uv run ruff check .          # lint
uv run pytest                # tests
```

CLI ingestion and the API server arrive in Phases 1 and 4. See
[`docs/phases/README.md`](docs/phases/README.md) for the roadmap and status.
