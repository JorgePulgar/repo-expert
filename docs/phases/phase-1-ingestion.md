# Phase 1 — Config & Ingestion

**Branch:** `feature/phase-1-ingestion` · **Status:** ⬜ not started

## Context
Turn a target repo into searchable knowledge. Two of the three sources are built here:
**(1) docs/markdown** and **(2) source code** with code-aware chunking, both pushed into
**Azure AI Search** indexes. Ingestion is config-driven: point at the repo named in the
active instance config, produce indexes whose names come from that config.

## Why this phase exists
Retrieval quality is capped by chunking quality. Markdown and code need different
strategies: docs by heading/section; code by symbol (function/class) so "how is X
implemented?" returns whole, coherent units with file/line metadata for citations.

## Prerequisites
- Phase 0 complete (config + settings).
- Azure AI Search service provisioned (free/basic tier OK). **Provisioning task below.**
- Azure OpenAI embedding deployment available.

## Tasks
- [ ] **P1-T1** — Provision Azure AI Search service + record endpoint/key in `.env`.
  - Commit: `docs(p1): document Azure AI Search provisioning [P1-T1]`
  - DoD: service reachable; keys in `.env`; steps written in ARCHITECTURE/setup notes.
- [ ] **P1-T2** — Repo fetcher: clone/pull target repo to local `data/` (sparse if large).
  - Commit: `feat(p1): repo fetcher for target repo [P1-T2]`
  - DoD: given config, repo content present locally; idempotent re-run.
- [ ] **P1-T3** — Markdown chunker (split by heading hierarchy, keep section path + source URL).
  - Commit: `feat(p1): markdown chunker by heading [P1-T3]`
  - DoD: README + docs/ chunked; each chunk has title, section path, file path, repo-relative link.
- [ ] **P1-T4** — Code-aware chunker (AST/symbol-based: function/class units with file + line span).
  - Commit: `feat(p1): code-aware chunker (symbol-level) [P1-T4]`
  - DoD: Python source chunked into symbol units with `file_path` + `start_line`/`end_line`.
- [ ] **P1-T5** — Embedding step (Azure OpenAI) for chunks; batched + rate-limit safe.
  - Commit: `feat(p1): embed chunks via azure openai [P1-T5]`
  - DoD: vectors produced for both sources; retries/backoff on 429.
- [ ] **P1-T6** — Define AI Search index schemas (docs index + code index) with hybrid + semantic config.
  - Commit: `feat(p1): ai search index schemas (docs, code) [P1-T6]`
  - DoD: indexes created with vector field, keyword fields, semantic config enabled.
- [ ] **P1-T7** — Uploader: push chunks+vectors to the named indexes; upsert by stable id.
  - Commit: `feat(p1): index uploader with upsert [P1-T7]`
  - DoD: re-running updates rather than duplicates; counts logged.
- [ ] **P1-T8** — `ingest` CLI entrypoint (`uv run repo-expert ingest`) driven by active config.
  - Commit: `feat(p1): ingest cli entrypoint [P1-T8]`
  - DoD: one command ingests docs + code for the active instance end-to-end.

## Exit criteria
- Both indexes populated for the FastAPI target; counts sane.
- Code chunks carry file/line metadata (needed for Phase 3 citations).
- `uv run repo-expert ingest` reproducible from clean state.
- Update master index status; open Phase 2.
