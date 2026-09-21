# Repo Expert

> 🇪🇸 ¿Español? Lee [`README.es.md`](README.es.md).

**Agentic RAG that answers questions about any GitHub repo it's pointed at, with inline
citations.** One codebase, two instances selected by config — no code changes to switch:

- **public** — class deliverable pointed at a serious public repo (`fastapi/fastapi`).
- **portfolio** — recruiter demo pointed at Jorge Pulgar's portfolio repos + a Career KB.

Stack: Qdrant Cloud (vector search + free server-side inference) · RRF fusion · LangGraph
(corrective/agentic RAG) · FastAPI · Azure OpenAI `gpt-5-mini`. Deployed on Azure Container Apps
(scale-to-zero). Python 3.12, managed with [uv](https://docs.astral.sh/uv/). Recurring cost
~$0–1/month.

**Live (portfolio instance):**
`https://ca-repo-expert.delightfulgrass-0e92a824.swedencentral.azurecontainerapps.io`
— [`/health`](https://ca-repo-expert.delightfulgrass-0e92a824.swedencentral.azurecontainerapps.io/health)
· [`/docs`](https://ca-repo-expert.delightfulgrass-0e92a824.swedencentral.azurecontainerapps.io/docs).
Scale-to-zero means the first request after an idle period takes a few seconds to wake.

## What it does

A FastAPI `/ask` endpoint hands the question to a **LangGraph** agent that
routes → retrieves → generates with citations → self-checks grounding → falls back and
retries if the answer isn't supported. Retrieval runs **vector search over Qdrant Cloud**
collections built from our own custom-chunked content, fused across docs/code/career. The
agent owns the reasoning and the fusion; the managed service owns vector storage +
embedding (build-vs-buy — see [`ARCHITECTURE.md`](ARCHITECTURE.md)).

### The retrieval pipeline, and why each part exists

Every piece below was added to fix a failure that was observed, not anticipated. The
rationale matters more than the list, so each one says what broke.

| Step | What it does | Why |
|---|---|---|
| **Section chunking** | one chunk per markdown heading, heading repeated on every piece, long sections split on sentence boundaries | the embedding model truncates at ~256 tokens **silently**; 12 of 22 career sections overflowed and their tails were unsearchable |
| **Multilingual embeddings** | `intfloat/multilingual-e5-small`, with `query:`/`passage:` prefixes | the previous model was English-only. The corpus is English, visitors ask in Spanish: *"What projects has Jorge built?"* returned 6/6 career chunks, the same question in Spanish returned 6/6 unrelated text |
| **Weighted fusion** | slots shared between collections in proportion to how well each matches, measured against the score spread for that query | plain RRF ranks *within* a collection, so every collection's #1 tied and the merge became a fixed quota — 2 of 6 slots each, whatever was asked |
| **Neighbour expansion** | a hit is widened with the chunks either side of it (`seq` ± 1), merged into its own text | splitting sections means an answer can straddle a boundary; merging rather than appending keeps the `[n]` numbering aligned with the citation list |
| **Gated query rewrite** | short, acronym-bearing and follow-up questions are rewritten into a self-contained question before embedding | "ML" does not embed near "machine learning". Rewriting *everything* made it worse — the expansion read like a keyword list and matched tables of contents — so it is gated |
| **Conversation memory** | prior turns are replayed as chat turns; the client sends them back each request | `/ask` is stateless by design, so any replica can serve any turn and nothing is stored server-side |

Measured effect on the portfolio set: **hit@6 0.8 → 1.0** (career 0.6 → 1.0). See
[`docs/eval-qdrant-vs-azure.md`](docs/eval-qdrant-vs-azure.md) for the full delta, including
a caveat about which part of the faithfulness gain was a measurement fix rather than a
quality gain.

### Abuse protection

`/ask` is unauthenticated and spends money on every call — three LLM round trips: routing,
generation, grounding judge. It is rate-limited to **10 questions per hour per IP**,
returning `429` with `Retry-After`, rejected *before* any LLM call so a throttled request
costs nothing. `/health` is deliberately exempt, so the chat page can warm the
scale-to-zero container for free.

> **CORS is not the protection here.** It is enforced by browsers only; a script calling
> the endpoint directly ignores it. The rate limit is what guards the credit.

## What knowledge it has — three heterogeneous sources

| # | Source | public | portfolio |
|---|---|---|---|
| 1 | Docs / markdown (in Qdrant) | FastAPI docs + README | Markdown across portfolio repos |
| 2 | Source code (in Qdrant, symbol-chunked) | `fastapi/**/*.py` | Python across portfolio repos |
| 3 | **Swapped per instance** | **GitHub issues/PRs** — live via API | **Career KB** — indexed in Qdrant |

The third source differs in *kind* (live API tool vs indexed knowledge source), satisfying
the ≥3-heterogeneous-sources requirement. The active instance is chosen entirely by config
(`src/repo_expert/config/instance.py`); see [`ARCHITECTURE.md`](ARCHITECTURE.md) for the
full design.

## Requirements

- [uv](https://docs.astral.sh/uv/) (manages Python 3.12 automatically).
- A Qdrant Cloud free-tier cluster (with server-side inference) + an Azure OpenAI
  `gpt-5-mini` deployment. A GitHub token is needed only for the public instance's live
  issues source. Provisioning steps: [`docs/setup.md`](docs/setup.md).

## Setup

```bash
uv sync                      # install deps into .venv
cp .env.example .env         # then fill in Qdrant + Azure OpenAI + GitHub keys
```

Select the instance in `.env` (or per-command with `--instance`):

```bash
REPO_EXPERT_INSTANCE=public   # or: portfolio
```

Required keys are documented in [`.env.example`](.env.example). Settings fail-fast: a
missing required variable raises at startup naming the offending variable.

## Run

```bash
# 1. Create the Qdrant collections, then ingest the target repo(s)
uv run repo-expert provision
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
| Relevance hit@6 | **1.00** (docs 1.0 · code 1.0 · issues 1.0 · mixed 1.0) |
| Faithfulness rate (judge) | **0.94** |
| Mean faithfulness score | **0.94** |
| Agent self-grounded rate | **1.00** |

Full report: [`docs/eval-results-public.md`](docs/eval-results-public.md).

> ⚠️ **These public-instance numbers were measured on `gpt-4o-mini` (2026-06) and have not
> been re-run since the move to `gpt-5-mini`.** Re-running them needs a working
> `GITHUB_TOKEN` for the live issues source; the portfolio numbers below are current.

**Portfolio instance** (n=10, career + portfolio-repo questions, re-run 2026-09-21):
**routing 1.0, relevance hit@6 1.0 (career 1.0 · mixed 1.0), faithfulness 1.0**
([`docs/eval-results-portfolio.md`](docs/eval-results-portfolio.md)). Off-topic questions
are declined by the config-driven scope guardrail. See the model-change note below for why
faithfulness moved.

**Analysis / limitations** (Qdrant stack; full Azure→Qdrant comparison in
[`docs/eval-qdrant-vs-azure.md`](docs/eval-qdrant-vs-azure.md)):
- The migration to Qdrant + a cheaper LLM **improved** the public instance: hit@6
  0.88 → 1.0, code relevance 0.6 → 1.0, faithfulness 0.75 → 0.94 — at ~75× lower cost.
- **RRF fusion** drives the code gain: code chunks score lower than prose on cosine, so a
  global score sort starved them; fusing collections by rank fixes it.
- Issues retrieval uses an **LLM query-rewrite**: prose questions are condensed to keywords
  because the GitHub Search API ANDs terms and returns nothing for prose (0.0 → 1.0).
- The career-recall regression (1.0 → 0.6) recorded here since June is **fixed**: it was
  never the token window, it was the language. `all-MiniLM-L6-v2` is English-only, the
  career document is English and the chat is used in Spanish, so Spanish questions could
  not reach it. `multilingual-e5-small` restores career recall to 1.0.
- Groundedness uses an LLM judge (gpt-5-mini), so scores carry run-to-run variance. The
  judge no longer runs at `temperature=0` — gpt-5-mini only accepts its default — so
  variance is higher than in earlier runs.
- **2026-09-21 retrieval overhaul:** multilingual embeddings, weighted fusion instead of a
  fixed per-collection quota, section splitting, corpus curation and conversation memory.
  Part of the faithfulness gain is a **measurement fix** — the judge had been retrieving
  less evidence than the generator used. Full delta and caveat:
  [`docs/eval-qdrant-vs-azure.md`](docs/eval-qdrant-vs-azure.md).

## Documentation

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — components, data flow, agent graph, decisions.
- [`docs/setup.md`](docs/setup.md) — Qdrant + Azure OpenAI provisioning.
- [`docs/deploy.md`](docs/deploy.md) — container build + Azure Container Apps deployment.
- [`docs/eval-qdrant-vs-azure.md`](docs/eval-qdrant-vs-azure.md) — backend-migration eval deltas.
- [`docs/phases/README.md`](docs/phases/README.md) — phase-by-phase development log.

## License

For coursework and portfolio demonstration.
