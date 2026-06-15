# Phase 2 — Retrieval Layer

**Branch:** `feature/phase-2-retrieval` · **Status:** 🟡 in progress

## Context
A clean retrieval API the LangGraph agent will call. Two kinds of retriever:
1. **Knowledge base retriever** — wraps the Foundry IQ KB (`knowledge_base_retrieve`)
   built in Phase 1. Covers the indexed sources (docs + code; career KB too, in the
   portfolio instance). The KB does source selection + rerank internally.
2. **Live GitHub issues/PRs retriever** — **outside** the KB (Foundry IQ has no GitHub
   source). Custom GitHub API tool so "is this a known bug / still open?" is current.

The **source registry** resolves what's available from instance config:
- `public`: KB {docs, code} **+** live issues tool.
- `portfolio`: KB {docs, code, career_kb}, **no** live tool (career is indexed into the KB).

## Why this phase exists
Isolating retrieval behind one typed interface keeps the LangGraph agent (Phase 3)
source-agnostic and makes the build-vs-buy seam explicit: managed KB for indexed
content, custom tool for the live source.

## Prerequisites
- Phase 1 complete (KB built + queryable).
- `GITHUB_TOKEN` in `.env` for the issues tool.

## Tasks
- [x] **P2-T1** — Unified retrieval result model (text, score, source kind, citation: file/line or url/section).
  - Commit: `feat(p2): unified retrieval result model [P2-T1]`
  - DoD: one model returned by both retrievers; carries citation metadata.
- [x] **P2-T2** — KB retriever: call `knowledge_base_retrieve`; map KB references → unified results + citations.
  - Commit: `feat(p2): foundry iq knowledge base retriever [P2-T2]`
  - DoD: a query returns ranked KB results with citations; reasoning effort = low (planning stays in LangGraph).
- [x] **P2-T3** — Live GitHub issues/PRs retriever via API (state filter open/closed, search by terms).
  - Commit: `feat(p2): github issues/prs live retriever [P2-T3]`
  - DoD: returns matching issues/PRs (title, state, url); handles rate limits; lives outside the KB.
- [ ] **P2-T4** — Source registry: resolve active retrievers from instance config (KB always; live issues only when source3=issues).
  - Commit: `feat(p2): source registry resolves retrievers from config [P2-T4]`
  - DoD: registry returns {KB, issues} for `public` and {KB} for `portfolio`, no code change.
- [ ] **P2-T5** — Retrieval tests (small, marked integration): KB query + issues query.
  - Commit: `test(p2): retrieval integration tests [P2-T5]`
  - DoD: known query returns expected top result from KB and from the issues tool.

## Exit criteria
- KB retriever + live issues retriever callable through one interface; citations populated.
- Source registry returns the correct set per instance from config alone.
- Update master index; open Phase 3.
