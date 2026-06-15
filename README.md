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

## Run
```bash
uv run repo-expert ingest            # build the knowledge base from the target repo
uv run uvicorn repo_expert.api.app:app   # serve /ask and /health (see /docs)
uv run repo-expert eval              # run the evaluation, write docs/eval-results.*
```

## Evaluation

A curated set of **16 questions** (5 code, 7 docs, 3 issues, 1 multi-hop) measures the
two things that matter for agentic RAG. Full report:
[`docs/eval-results.md`](docs/eval-results.md) · regenerate with `uv run repo-expert eval`.

**Method**
- *Retrieval relevance* — for each question: (a) **routing accuracy**, did the router
  pick the expected source(s); (b) **hit@k**, did a top-k result from the expected
  source match the expected citation (file/section substring) and kind.
- *Groundedness* — run the full agent, then an **independent LLM judge** scores whether
  every claim in the answer is supported by independently-retrieved evidence. We also
  log the agent's own self-grounding flag.

**Baseline (public / fastapi/fastapi, n=16)**

| Metric | Value |
| --- | --- |
| Routing accuracy | **1.00** |
| Relevance hit@6 | **0.69** (docs 1.0 · code 0.6 · issues 0.0 · mixed 1.0) |
| Faithfulness rate (judge) | **0.88** |
| Mean faithfulness score | **0.95** |
| Agent self-grounded rate | **0.81–0.88** |

**Analysis / limitations**
- **Docs retrieval is strong (1.0); groundedness is high (0.95 mean)** — the corrective
  loop catches weak drafts (e.g. code/issue questions trigger fallback to a second
  source before answering).
- **Issues relevance is 0.0**: full natural-language questions are passed verbatim to the
  GitHub Search API, which expects keywords and returns nothing. Despite this, those
  questions still get *faithful* answers because the agent falls back to the KB. Planned
  fix: an LLM **query-rewrite** step for the issues tool.
- **Code relevance 0.6**: exact symbol files aren't always in the top-k; symbol-level
  chunking + reranking handles most but not all "where is X defined" lookups.
- Groundedness uses an LLM judge (gpt-4o), so scores carry small run-to-run variance.
