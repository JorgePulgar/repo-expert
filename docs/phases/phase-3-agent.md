# Phase 3 — LangGraph Agent

**Branch:** `feature/phase-3-agent` · **Status:** 🟡 in progress

## Context
The CV-relevant core and the **build** half of build-vs-buy. A **LangGraph** agent
orchestrates corrective/agentic RAG **on top of** the Foundry IQ KB and the live issues
tool. The KB handles managed retrieval; LangGraph owns the headline reasoning the KB
doesn't: routing between KB and the live tool, fallback, and a **corrective/grounding
node** that verifies the draft against retrieved evidence.

Graph flow: **router** (KB / live-issues / both) → **retrieve** (via registry) →
**fallback** → **corrective/grounding** → **generate** with citations.

## Why this phase exists
This is what makes the project read as engineering, not portal configuration. Owning the
orchestration + self-correction lets the CV claim BOTH "built corrective RAG in LangGraph"
AND "integrated Foundry IQ agentic retrieval" AND "made the build-vs-buy call".

## Build-vs-buy boundary (keep explicit)
- **KB (buy):** managed retrieval over indexed docs/code (+career), source selection, rerank.
- **LangGraph (build):** routing KB↔live-tool, fallback, corrective grounding, generation, citations.
- KB reasoning effort stays **low** so the agentic headline is demonstrably ours.

## Prerequisites
- Phase 2 complete (KB retriever + live issues retriever + source registry).
- Azure OpenAI chat deployment for the agent's generation/grounding.

## Tasks
- [x] **P3-T1** — Graph state + skeleton (nodes/edges wired, no logic).
  - Commit: `feat(p3): langgraph state and skeleton graph [P3-T1]`
  - DoD: graph compiles; state carries query, route, retrieved results, draft, citations.
- [x] **P3-T2** — Router node: classify intent → KB / live-issues / both.
  - Commit: `feat(p3): router node (kb vs live issues) [P3-T2]`
  - DoD: "how is X implemented?" → KB; "is this a known bug / still open?" → issues; ambiguous → both.
- [x] **P3-T3** — Retrieve node: call selected retriever(s) via the registry.
  - Commit: `feat(p3): retrieve node via source registry [P3-T3]`
  - DoD: populates state with results + citations from KB and/or the live tool.
- [x] **P3-T4** — Fallback logic: weak/empty KB → try issues (and vice versa); "is this broken?" → issues, then code if unresolved.
  - Commit: `feat(p3): fallback routing on weak/empty retrieval [P3-T4]`
  - DoD: low-confidence/empty retrieval triggers the secondary source; logged.
- [x] **P3-T5** — Corrective/grounding node: verify draft against retrieved evidence; re-retrieve or revise if unsupported.
  - Commit: `feat(p3): corrective grounding node [P3-T5]`
  - DoD: claims unsupported by retrieved text trigger revision/re-retrieval before responding.
- [x] **P3-T6** — Generate node: grounded answer with inline citations (file/line or doc section/url/issue).
  - Commit: `feat(p3): grounded generation with citations [P3-T6]`
  - DoD: every answer cites sources; no evidence → honest "I don't know".
- [ ] **P3-T7** — Agent entrypoint `ask(question) -> answer+citations+route` + graph diagram export.
  - Commit: `feat(p3): agent ask() entrypoint and graph export [P3-T7]`
  - DoD: callable function returns structured answer; mermaid/png of graph saved for docs.
- [ ] **P3-T8** — Unit tests for router + grounding with fixtures.
  - Commit: `test(p3): router and grounding unit tests [P3-T8]`
  - DoD: routing (KB vs issues) and grounding behavior asserted on representative questions.

## Exit criteria
- End-to-end `ask()` answers code/docs questions (via KB) and "known bug?" questions
  (via live issues) with citations.
- Corrective loop demonstrably catches an ungrounded draft (test or logged example).
- KB reasoning effort low; agentic headline lives in LangGraph.
- Update master index; open Phase 4.
