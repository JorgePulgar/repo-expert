# Phase 5 — Evaluation

**Branch:** `feature/phase-5-eval` · **Status:** 🟡 in progress

## Context
Prove it works. Build a small curated Q/A set for the public instance and measure
**retrieval relevance** and **answer groundedness (faithfulness)**. Document results in
the README. Curate questions opportunistically during earlier phases; finalize here.

## Why this phase exists
A class deliverable claiming "agentic/corrective RAG" needs numbers. Eval also guards
against regressions when tuning chunking/routing.

## Prerequisites
- Phase 4 complete (API/agent callable).

## Tasks
- [x] **P5-T1** — Curated Q/A set for FastAPI instance (mix: code, docs, issues, multi-hop).
  - Commit: `test(p5): curated eval q/a set (public instance) [P5-T1]`
  - DoD: ≥ ~15 questions with expected sources/answers, stored as data file.
- [x] **P5-T2** — Retrieval-relevance metric (hit@k / expected-source match) harness.
  - Commit: `feat(p5): retrieval relevance eval harness [P5-T2]`
  - DoD: runs over Q/A set, reports per-source relevance scores.
- [x] **P5-T3** — Groundedness/faithfulness metric (LLM-as-judge against retrieved evidence).
  - Commit: `feat(p5): groundedness eval harness [P5-T3]`
  - DoD: scores each answer for support by cited evidence; aggregate reported.
- [x] **P5-T4** — Eval runner CLI (`uv run repo-expert eval`) + results report (markdown/json).
  - Commit: `feat(p5): eval runner cli with report output [P5-T4]`
  - DoD: one command produces a results report committed under `docs/`.
- [ ] **P5-T5** — Record baseline results + brief analysis in README/ARCHITECTURE.
  - Commit: `docs(p5): document eval methodology and baseline results [P5-T5]`
  - DoD: numbers + method written up; limitations noted.

## Exit criteria
- Reproducible eval with documented relevance + groundedness numbers.
- Results referenced in README.
- Update master index; open Phase 6.
