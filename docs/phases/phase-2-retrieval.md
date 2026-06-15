# Phase 2 — Retrieval Layer

**Branch:** `feature/phase-2-retrieval` · **Status:** ⬜ not started

## Context
A clean retrieval API the agent will call. Wraps Azure AI Search **hybrid search**
(keyword + vector) with the **semantic reranker**, exposed per source (docs / code /
issues). Plus the third source for the public instance: **GitHub issues/PRs live via API**
(not indexed — queried at request time so "is this a known bug / still open?" is current).

## Why this phase exists
Isolating retrieval behind a typed interface lets the LangGraph agent (Phase 3) stay
source-agnostic and lets us swap source 3 (issues ↔ career KB) by config in Phase 6.

## Prerequisites
- Phase 1 complete (indexes populated).
- `GITHUB_TOKEN` in `.env` for issues source.

## Tasks
- [ ] **P2-T1** — Retrieval result model (text, score, source kind, citation: file/line or url/section).
  - Commit: `feat(p2): unified retrieval result model [P2-T1]`
  - DoD: one dataclass/pydantic model all retrievers return; carries citation metadata.
- [ ] **P2-T2** — Docs retriever: hybrid + semantic reranker over docs index.
  - Commit: `feat(p2): docs retriever (hybrid + semantic) [P2-T2]`
  - DoD: query returns ranked doc chunks with section citations.
- [ ] **P2-T3** — Code retriever: hybrid + semantic reranker over code index.
  - Commit: `feat(p2): code retriever (hybrid + semantic) [P2-T3]`
  - DoD: query returns ranked code symbols with file/line citations.
- [ ] **P2-T4** — GitHub issues/PRs retriever via API (state filter open/closed, search by terms).
  - Commit: `feat(p2): github issues/prs retriever [P2-T4]`
  - DoD: returns matching issues/PRs with title, state, url; handles rate limits.
- [ ] **P2-T5** — Source registry that resolves "active source 3" from config (issues vs career_kb stub).
  - Commit: `feat(p2): source registry resolves active sources from config [P2-T5]`
  - DoD: agent can ask registry for available retrievers without knowing instance.
- [ ] **P2-T6** — Retrieval tests against live indexes (small, marked integration).
  - Commit: `test(p2): retrieval integration tests [P2-T6]`
  - DoD: known query returns expected top chunk per source.

## Exit criteria
- Three retrievers callable through one interface; citations populated.
- Source registry returns correct set for `public` instance.
- Update master index; open Phase 3.
