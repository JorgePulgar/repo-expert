# Phase 1 — Ingestion & Foundry IQ Knowledge Base

**Branch:** `feature/phase-1-ingestion` · **Status:** 🟡 in progress

## Context
Turn a target repo into a **Foundry IQ knowledge base**. We keep custom, code-aware
chunking (the engineering signal) and attach our own indexes to Foundry IQ as
**"existing search index" knowledge sources**. The KB then provides managed agentic
retrieval (planning, source selection, rerank, citations) that our LangGraph layer wraps
in Phase 3.

Two indexed sources are built here: **(1) docs/markdown** and **(2) source code**
(symbol-level chunking), each pushed to an Azure AI Search index, then registered as
knowledge sources on one knowledge base. The third source (live GitHub issues) is **not**
in the KB — it's a live tool added in Phase 2.

## Architecture decision (option C: build-vs-buy)
- **Buy:** Foundry IQ / Azure AI Search agentic retrieval = retrieval backend over indexed content.
- **Build:** custom chunking + the knowledge sources/index schema; LangGraph orchestration + grounding (Phase 3); live issues tool (Phase 2).
- **Avoid double planning:** set KB **retrieval reasoning effort = low/minimal**; the headline agentic reasoning lives in our LangGraph (Phase 3).

## Why this phase exists
Retrieval quality is capped by chunking + index quality. Owning the index (not letting
the indexer auto-chunk Blob) keeps code-aware, file/line-cited chunks AND lets us plug
into Foundry IQ — proving the build-vs-buy judgment.

## Prerequisites
- Phase 0 complete (config + settings).
- Azure AI Search service that **supports agentic retrieval** (knowledge bases).
- Azure OpenAI: an **embedding** deployment + a **query-planning** chat deployment
  (gpt-4o / gpt-4.1 / gpt-5 series — only these are supported for KB query planning).
- Microsoft Foundry (new) project (portal) OR plan to create KB programmatically.

## Tasks
- [x] **P1-T1** — Provision Azure AI Search (agentic-capable) + Foundry project + Azure OpenAI deployments; record endpoints/keys in `.env`.
  - Commit: `docs(p1): document Foundry IQ + AI Search provisioning [P1-T1]`
  - DoD: services reachable; embedding + query-planning deployments exist; steps written down.
- [x] **P1-T2** — Repo fetcher: clone/pull target repo to local `data/`.
  - Commit: `feat(p1): repo fetcher for target repo [P1-T2]`
  - DoD: given config, repo content present locally; idempotent re-run.
- [x] **P1-T3** — Markdown chunker (split by heading hierarchy; keep section path + source URL).
  - Commit: `feat(p1): markdown chunker by heading [P1-T3]`
  - DoD: README + docs/ chunked; each chunk has title, section path, file path, repo-relative link.
- [x] **P1-T4** — Code-aware chunker (AST/symbol units: function/class with file + line span).
  - Commit: `feat(p1): code-aware chunker (symbol-level) [P1-T4]`
  - DoD: source chunked into symbol units with `file_path` + `start_line`/`end_line`.
- [x] **P1-T5** — Embedding step (Azure OpenAI) for chunks; batched + rate-limit safe.
  - Commit: `feat(p1): embed chunks via azure openai [P1-T5]`
  - DoD: vectors produced for both sources; retries/backoff on 429.
- [x] **P1-T6** — Define AI Search index schemas (docs index + code index): vector + keyword fields, semantic config.
  - Commit: `feat(p1): ai search index schemas (docs, code) [P1-T6]`
  - DoD: indexes created with the fields Foundry IQ needs to reference them as knowledge sources.
- [x] **P1-T7** — Uploader: push chunks+vectors to the indexes; upsert by stable id.
  - Commit: `feat(p1): index uploader with upsert [P1-T7]`
  - DoD: re-running updates rather than duplicates; counts logged.
- [x] **P1-T8** — Create **knowledge sources** ("existing search index" type) for docs + code, with descriptions for source selection.
  - Commit: `feat(p1): foundry iq knowledge sources for docs and code [P1-T8]`
  - DoD: two knowledge sources exist, each with a description guiding the KB router (e.g. "code index for how-is-X-implemented").
- [x] **P1-T9** — Create the **Foundry IQ knowledge base** referencing both sources (basic GA KB; no LLM attached — LangGraph owns reasoning. LLM query planning + reasoning-effort tuning are preview-only in GA SDK 12.0.0).
  - Commit: `feat(p1): foundry iq knowledge base over docs+code [P1-T9]`
  - DoD: KB exists; `knowledge_base_retrieve` returns grounded results with citations for a test query. (Note: references expose `title` + `docKey`=chunk id; resolve full citation via index lookup in Phase 2 — `sourceData` returns null in GA.)
- [ ] **P1-T10** — `ingest` CLI (`uv run repo-expert ingest`): fetch → chunk → embed → upload → (re)build KB, driven by active config.
  - Commit: `feat(p1): ingest cli entrypoint [P1-T10]`
  - DoD: one command takes the active instance from clean state to a queryable KB.

## Exit criteria
- KB answers a test query over the FastAPI repo with citations (file/line + doc section).
- Index names + KB name come from instance config (no hard-coding).
- KB reasoning effort = low (planning reserved for LangGraph).
- `uv run repo-expert ingest` reproducible. Update master index; open Phase 2.
