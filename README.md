# Repo Expert

> 🇪🇸 ¿Español? Lee [`README.es.md`](README.es.md).

**Agentic RAG that answers questions about any GitHub repo it's pointed at, with inline
citations.** One codebase, two instances selected by config — no code changes to switch:

- **public** — class deliverable pointed at a serious public repo (`fastapi/fastapi`).
- **portfolio** — recruiter demo pointed at Jorge Pulgar's portfolio repos + a Career KB.

Stack: Azure AI Search (hybrid + semantic reranker, Foundry IQ knowledge base) ·
LangGraph (corrective/agentic RAG) · FastAPI · Azure OpenAI. Python 3.12, managed with
[uv](https://docs.astral.sh/uv/).

## What it does

A FastAPI `/ask` endpoint hands the question to a **LangGraph** agent that
routes → retrieves → generates with citations → self-checks grounding → falls back and
retries if the answer isn't supported. Retrieval runs over a **Foundry IQ knowledge base**
on Azure AI Search built from our own custom-chunked indexes. The agent owns the
reasoning; the managed service owns retrieval (build-vs-buy — see
[`ARCHITECTURE.md`](ARCHITECTURE.md)).

## What knowledge it has — three heterogeneous sources

| # | Source | public | portfolio |
|---|---|---|---|
| 1 | Docs / markdown (in KB) | FastAPI docs + README | Markdown across portfolio repos |
| 2 | Source code (in KB, symbol-chunked) | `fastapi/**/*.py` | Python across portfolio repos |
| 3 | **Swapped per instance** | **GitHub issues/PRs** — live via API | **Career KB** — indexed in the KB |

The third source differs in *kind* (live API tool vs indexed knowledge source), satisfying
the ≥3-heterogeneous-sources requirement. The active instance is chosen entirely by config
(`src/repo_expert/config/instance.py`); see [`ARCHITECTURE.md`](ARCHITECTURE.md) for the
full design.

## Requirements

- [uv](https://docs.astral.sh/uv/) (manages Python 3.12 automatically).
- Azure AI Search (agentic-retrieval capable) + Azure OpenAI deployments. A GitHub token
  is needed only for the public instance's live issues source. Provisioning steps:
  [`docs/setup.md`](docs/setup.md).

## Setup

```bash
uv sync                      # install deps into .venv
cp .env.example .env         # then fill in Azure + GitHub keys
```

Select the instance in `.env` (or per-command with `--instance`):

```bash
REPO_EXPERT_INSTANCE=public   # or: portfolio
```

Required keys are documented in [`.env.example`](.env.example). Settings fail-fast: a
missing required variable raises at startup naming the offending variable.

## Run

```bash
# 1. Build the knowledge base from the target repo(s)
uv run repo-expert ingest
uv run repo-expert --instance portfolio ingest   # portfolio instance

# 2. Serve the API (GET /health, POST /ask; interactive docs at /docs)
uv run uvicorn repo_expert.api.app:app --reload

# 3. Ask
curl -s localhost:8000/ask -H 'content-type: application/json' \
  -d '{"question": "How does FastAPI handle dependency injection?"}'
```

`GET /health` reports the active instance, target repo, and per-index document counts.

## Develop

```bash
uv run ruff check .          # lint
uv run pytest                # unit tests (integration tests need .env: -m integration)
```

## Evaluation

A curated Q/A set measures the two things that matter for agentic RAG: **retrieval
relevance** and **groundedness**. Regenerate with `uv run repo-expert eval` (add
`--instance portfolio` for the portfolio set).

**Method**
- *Retrieval relevance* — per question: (a) **routing accuracy**, did the router pick the
  expected source(s); (b) **hit@k**, did a top-k result from the expected source match the
  expected citation (file/section substring) and kind.
- *Groundedness* — run the full agent, then an **independent LLM judge** scores whether
  every claim in the answer is supported by independently-retrieved evidence. The agent's
  own self-grounding flag is also logged.

**Public instance** (`fastapi/fastapi`, n=16 — 5 code, 7 docs, 3 issues, 1 multi-hop):

| Metric | Value |
| --- | --- |
| Routing accuracy | **1.00** |
| Relevance hit@6 | **0.88** (docs 1.0 · code 0.6 · issues 1.0 · mixed 1.0) |
| Faithfulness rate (judge) | **0.75** |
| Mean faithfulness score | **0.89** |
| Agent self-grounded rate | **0.88** |

Full report: [`docs/eval-results-public.md`](docs/eval-results-public.md).

**Portfolio instance** (n=10, career + portfolio-repo questions): **routing 1.0,
relevance hit@6 1.0, faithfulness 1.0**
([`docs/eval-results-portfolio.md`](docs/eval-results-portfolio.md)). Off-topic questions
are declined by the config-driven scope guardrail.

**Analysis / limitations**
- Docs and issues retrieval are strong (1.0); overall hit@6 is 0.88.
- Issues retrieval uses an **LLM query-rewrite**: prose questions are condensed to keywords
  because the GitHub Search API ANDs terms and returns nothing for prose. This lifted issue
  relevance 0.0 → 1.0.
- Code relevance 0.6: exact symbol files aren't always in top-k; symbol-level chunking +
  reranking handles most but not all "where is X defined" lookups.
- The corrective loop catches weak drafts before answering. Public faithfulness rate is
  lower than a KB-only baseline precisely *because* the agent now attempts substantive
  issue answers instead of falling back to the KB — a deliberate trade of caution for
  coverage.
- Groundedness uses an LLM judge (gpt-4o), so scores carry small run-to-run variance.

## Documentation

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — components, data flow, agent graph, decisions.
- [`docs/setup.md`](docs/setup.md) — Azure provisioning.
- [`docs/deploy.md`](docs/deploy.md) — container build + Azure deployment.
- [`docs/phases/README.md`](docs/phases/README.md) — phase-by-phase development log.

## License

For coursework and portfolio demonstration.
