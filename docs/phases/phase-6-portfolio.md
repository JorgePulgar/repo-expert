# Phase 6 — Portfolio Instance

**Branch:** `feature/phase-6-portfolio` · **Status:** ⬜ not started

## Context
The recruiter demo: **same app, different data**. Prove the config-driven design by
standing up a second instance pointed at my portfolio repos. Sources 1–2 (docs + code)
reuse Phase 1–2 machinery unchanged. **Source 3 swaps** from GitHub issues to a
**Career Knowledge Base**: per-project summaries, my role, tech stack, outcomes.
Routing then handles both kinds of question; guardrails keep it on-topic.

## Why this phase exists
Validates the core requirement (instance switch = config change) and produces the
"try it live" hook. If anything needs a code change to swap instances, that's a bug to
fix here, not a special case to hard-code.

## Prerequisites
- Phases 1–5 complete for the public instance.
- Career KB content authored (project summaries, roles, stacks, outcomes).

## Tasks
- [ ] **P6-T1** — Author Career KB content (per-project: summary, role, stack, outcomes).
  - Commit: `docs(p6): career knowledge base content [P6-T1]`
  - DoD: structured KB data file(s) covering target portfolio projects.
- [ ] **P6-T2** — Career KB ingestion + index (reuse embed/upload; new index name from config).
  - Commit: `feat(p6): career kb ingestion and index [P6-T2]`
  - DoD: KB searchable via AI Search; citations point to project entries.
- [ ] **P6-T3** — Career KB retriever + register as "source 3" for portfolio instance.
  - Commit: `feat(p6): career kb retriever wired into source registry [P6-T3]`
  - DoD: registry returns career_kb (not issues) when instance=portfolio; zero code change elsewhere.
- [ ] **P6-T4** — `portfolio` instance config (target repos, index names, source 3 = career_kb).
  - Commit: `feat(p6): portfolio instance config [P6-T4]`
  - DoD: `REPO_EXPERT_INSTANCE=portfolio` ingests + serves portfolio data.
- [ ] **P6-T5** — Router handles career questions ("which projects use Azure AI Search and Jorge's role?").
  - Commit: `feat(p6): router supports career-kb intent [P6-T5]`
  - DoD: career questions route to KB; code/doc questions still route to code/docs.
- [ ] **P6-T6** — Guardrails: scope strictly to portfolio; decline off-topic cleanly.
  - Commit: `feat(p6): portfolio scope guardrails [P6-T6]`
  - DoD: off-topic questions get a clean refusal; on-topic answered with citations.
- [ ] **P6-T7** — Portfolio eval mini-set (reuse Phase 5 harness).
  - Commit: `test(p6): portfolio eval q/a set [P6-T7]`
  - DoD: eval runs for portfolio instance; results recorded.

## Exit criteria
- Both instances run from the same codebase, selected by config only.
- Career questions answered with citations; off-topic declined.
- Update master index; open Phase 7.
