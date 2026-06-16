# Architecture — Repo Expert

Agentic RAG that answers questions about a GitHub repository with inline citations.
One codebase; two instances selected by config (`public`, `portfolio`). This document
describes the components, the data flow, the agent graph, the three knowledge sources,
and the key design decisions.

---

## 1. Build-vs-buy boundary

The headline design choice (Option C) splits the system into a *bought* managed
retrieval layer and a *built* reasoning + ingestion layer.

| | Component | Responsibility |
|---|---|---|
| **Buy** | Azure AI Search (Foundry IQ knowledge base) | Hybrid (vector + keyword) retrieval and semantic reranking over our indexes. **Reasoning effort kept low** so the managed service retrieves but does not own the agentic loop. |
| **Build** | Custom code-aware chunking + indexes | Symbol-level code chunks and section-level markdown chunks, embedded and uploaded by us. |
| **Build** | LangGraph orchestration | Router → retrieve → generate → grounding → fallback. The corrective/self-grounding loop is ours — the CV-relevant piece. |
| **Build** | Live GitHub issues tool | Issues/PRs queried live via the GitHub Search API, outside the KB (public instance only). |

Rationale: the agentic *reasoning* (routing, fallback, self-correction) lives in our
LangGraph, not in the managed retrieval service. The KB is a strong retriever; the agent
is the brain.

---

## 2. Components

```
                          ┌──────────────────────────────┐
   repo-expert ingest     │        Ingestion (build)     │
   ───────────────────▶   │  fetch → chunk → embed →     │
                          │  upload → build KB sources   │
                          └───────────────┬──────────────┘
                                          │ writes
                                          ▼
                          ┌──────────────────────────────┐
                          │   Azure AI Search (buy)      │
                          │  docs index · code index ·   │
                          │  career index (portfolio)    │
                          │  → Foundry IQ knowledge base │
                          └───────────────┬──────────────┘
                                          │ retrieves
   POST /ask              ┌───────────────▼──────────────┐      ┌────────────────────┐
   ───────────────────▶   │   LangGraph agent (build)    │ ───▶ │ GitHub issues API  │
                          │  router → retrieve →         │ live │ (public instance)  │
   FastAPI backend        │  generate → grounding →      │ tool └────────────────────┘
                          │  fallback loop               │
                          └───────────────┬──────────────┘
                                          │ uses
                                          ▼
                          ┌──────────────────────────────┐
                          │       Azure OpenAI (buy)     │
                          │  embeddings · routing ·      │
                          │  generation · grounding judge│
                          └──────────────────────────────┘
```

| Module | Path | Role |
|---|---|---|
| Config | `src/repo_expert/config/` | `Settings` (env/secrets) + `InstanceConfig` (the only thing that differs per instance). |
| Ingestion | `src/repo_expert/ingestion/` | `pipeline.ingest`: fetch repo → chunk docs/code/career → embed → upload → create KB sources + KB. |
| Retrieval | `src/repo_expert/retrieval/` | `registry` resolves active retrievers; `kb` (Azure AI Search) + `issues` (live GitHub). |
| Agent | `src/repo_expert/agent/` | LangGraph `graph` + `agent.ask` entrypoint. |
| API | `src/repo_expert/api/` | FastAPI app exposing `GET /health` and `POST /ask`. |
| CLI | `src/repo_expert/cli.py` | `repo-expert ingest` and `repo-expert eval`. |
| Eval | `src/repo_expert/eval/` | Retrieval-relevance + groundedness harness and report writer. |

---

## 3. Data flow

### Ingestion (`repo-expert ingest`)
1. **Fetch** each target repo (`ingestion/fetch.py`).
2. **Chunk** — markdown by section (`markdown.py`), code by symbol with code-aware
   chunking (`code.py`), career doc by entry (`career.py`, portfolio only). Path globs
   from `InstanceConfig` control scope and embedding cost.
3. **Embed** chunks via Azure OpenAI (`embed.py`).
4. **Upload** to Azure AI Search indexes (`upload.py` → docs / code / career indexes).
5. **Build** Foundry IQ knowledge sources + knowledge base over the indexes
   (`knowledge.py`).

### Query (`POST /ask`)
1. **router** — picks the minimal set of sources (`kb`, `issues`) for the question.
   Single-source instances skip the LLM call.
2. **retrieve** — runs each routed retriever (`top=6`). KB hits Azure AI Search
   (hybrid + semantic rerank); issues hits the live GitHub Search API (with an LLM
   query-rewrite to keywords).
3. **generate** — answers using only the numbered sources, citing inline as `[n]`.
   The instance `scope_prompt` (if any) is appended to scope answers.
4. **grounding** — an LLM verifies every claim is supported by the sources.
5. **fallback** — if ungrounded and attempts remain, widen the route to all sources and
   loop back to retrieve. Otherwise end.

---

## 4. Agent graph

Source: `docs/agent-graph.mmd` (regenerate with `agent.export_graph`).

```mermaid
graph TD;
	__start__([__start__]):::first
	router(router)
	retrieve(retrieve)
	generate(generate)
	grounding(grounding)
	fallback(fallback)
	__end__([__end__]):::last
	__start__ --> router;
	fallback --> retrieve;
	generate --> grounding;
	grounding -. end .-> __end__;
	grounding -. revise .-> fallback;
	retrieve --> generate;
	router --> retrieve;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc
```

The corrective loop (`grounding → fallback → retrieve`) runs at most `MAX_ATTEMPTS = 2`
times before answering with the best draft.

---

## 5. The three heterogeneous knowledge sources

Two sources are shared; the third is swapped per instance via `InstanceConfig.source3`.

| # | Source | Kind | public instance | portfolio instance |
|---|---|---|---|---|
| 1 | Docs / markdown | section-chunked text, in KB | FastAPI English docs + README | Markdown across Jorge's portfolio repos |
| 2 | Source code | symbol-chunked code, in KB | `fastapi/**/*.py` | Python across portfolio repos |
| 3 | **Swapped** | — | **GitHub issues/PRs**, live via API, outside the KB | **Career KB**, a local markdown doc indexed into the KB |

- The third source differs in *kind*, not just content: a **live API tool** vs an
  **indexed knowledge source**. This satisfies the class requirement of ≥3 heterogeneous
  sources while exercising both the build (live tool) and buy (indexed) paths.
- In the portfolio instance the career doc (`docs/jorge-pulgar-career-rag.md`) is folded
  into the KB as a third index, so the registry registers no separate retriever — routing
  collapses to `kb` only and the agent skips the router LLM call.

---

## 6. Config-driven targeting

Switching instance = changing config, not code. `InstanceConfig` (`config/instance.py`)
selects:

- `target_repos` — which repo(s) to ingest and answer about.
- `docs_index` / `code_index` / `source3_index` — which Azure AI Search indexes to use.
- `source3` — `issues` (live) or `career_kb` (indexed).
- `docs_globs` / `code_globs` / `exclude_globs` — ingestion scope (cost control).
- `scope_prompt` — optional guardrail appended to generation (portfolio declines
  off-topic questions).

Everything downstream (ingestion, retrieval, agent, API health) reads from this object
and stays instance-agnostic. Active instance is chosen by `REPO_EXPERT_INSTANCE` or the
`--instance` CLI flag.

---

## 7. Key decisions

- **KB reasoning effort = low.** The managed service retrieves; the agentic headline
  (routing, fallback, grounding) stays in our LangGraph so it is demonstrably *ours*.
- **Issues query-rewrite.** The GitHub Search API ANDs terms and returns nothing for
  prose, so questions are condensed to keywords first — lifted issue relevance 0.0 → 1.0.
- **Self-grounding over blind generation.** An independent LLM check gates answers; a
  weak draft triggers a wider retrieval pass before responding.
- **Career KB folded into the index** (not a live tool) for the portfolio instance,
  because career content is static and benefits from hybrid + semantic rerank.
- **Fail-fast settings.** Missing required env vars raise at load with the offending
  variable named.

---

## 8. Tech stack

Python 3.12 · uv · FastAPI · LangGraph · Azure AI Search (hybrid + semantic rerank,
Foundry IQ KB) · Azure OpenAI (embeddings + routing + generation + grounding judge) ·
GitHub Search API. See `README.md` for setup and run instructions.
