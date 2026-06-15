# Phase 3 — LangGraph Agent

**Branch:** `feature/phase-3-agent` · **Status:** ⬜ not started

## Context
The CV-relevant core: a **LangGraph** agent implementing corrective/agentic RAG.
Graph flow: **router** (classify intent → docs / code / issues|career) → **retrieve**
from selected source(s) → **fallback** logic → **corrective/grounding** check →
**generate** grounded answer with citations.

## Why this phase exists
This is what distinguishes the project from naive RAG: routing to heterogeneous sources,
self-correction against retrieved evidence, and graceful fallback. It's the headline of
the README and the resume.

## Prerequisites
- Phase 2 complete (retrievers + source registry).
- Azure OpenAI chat deployment available.

## Tasks
- [ ] **P3-T1** — Define graph state + skeleton (nodes/edges wired, no logic).
  - Commit: `feat(p3): langgraph state and skeleton graph [P3-T1]`
  - DoD: graph compiles; state carries query, route, retrieved docs, draft, citations.
- [ ] **P3-T2** — Router node: classify intent → source(s).
  - Commit: `feat(p3): router node classifies intent [P3-T2]`
  - DoD: "how is X implemented?" → code; "is this a known bug?" → issues; doc questions → docs.
- [ ] **P3-T3** — Retrieve node: call selected retriever(s) via registry.
  - Commit: `feat(p3): retrieve node via source registry [P3-T3]`
  - DoD: populates state with results + citations for the routed source.
- [ ] **P3-T4** — Fallback logic: e.g. "is this broken?" → issues; if unresolved → read code/docs.
  - Commit: `feat(p3): fallback routing on weak/empty retrieval [P3-T4]`
  - DoD: low-confidence or empty retrieval triggers secondary source; logged.
- [ ] **P3-T5** — Corrective/grounding node: verify draft answer against retrieved evidence; re-retrieve or revise if unsupported.
  - Commit: `feat(p3): corrective grounding node [P3-T5]`
  - DoD: answer claims unsupported by retrieved text trigger revision/re-retrieval before responding.
- [ ] **P3-T6** — Generate node: grounded answer with inline citations (file/line or doc section/url).
  - Commit: `feat(p3): grounded generation with citations [P3-T6]`
  - DoD: every answer cites its sources; no-evidence → honest "I don't know".
- [ ] **P3-T7** — Agent entrypoint `ask(question) -> answer+citations` + graph diagram export.
  - Commit: `feat(p3): agent ask() entrypoint and graph export [P3-T7]`
  - DoD: callable function returns structured answer; mermaid/png of graph saved for docs.
- [ ] **P3-T8** — Unit tests for router + grounding with fixtures.
  - Commit: `test(p3): router and grounding unit tests [P3-T8]`
  - DoD: routing and grounding behavior asserted on representative questions.

## Exit criteria
- End-to-end `ask()` answers code/docs/issues questions with citations.
- Corrective loop demonstrably catches an ungrounded draft (test or logged example).
- Update master index; open Phase 4.
