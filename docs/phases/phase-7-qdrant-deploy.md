# Phase 7 — Docs & Deploy

**Branch:** `feature/phase-7-docs-deploy` · **Status:** ⬜ not started

## Context
Ship it and document it. Produce the bilingual README + ARCHITECTURE, then deploy to
Azure so it's testable in the portal/playground per the class requirement.

## Why this phase exists
The deliverable is graded on documentation and deployability, not just code. This phase
makes the project legible to graders and recruiters and reachable over the internet.

## Prerequisites
- Phases 4–6 complete (API + both instances + eval).

## Tasks
- [ ] **P7-T1** — `ARCHITECTURE.md`: components, data flow, graph diagram, sources, decisions.
  - Commit: `docs(p7): architecture document [P7-T1]`
  - DoD: includes the LangGraph diagram and the 3-source description for both instances.
- [ ] **P7-T2** — `README.md` (EN): what it does / what it's for / what knowledge it has / how to run.
  - Commit: `docs(p7): english readme [P7-T2]`
  - DoD: covers setup, ingest, run, eval results, both instances; satisfies "fully documented".
- [ ] **P7-T3** — `README.es.md` (Spanish translation, kept in sync).
  - Commit: `docs(p7): spanish readme [P7-T3]`
  - DoD: content parity with EN README.
- [ ] **P7-T4** — Containerize (Dockerfile) + local run instructions.
  - Commit: `chore(p7): dockerfile for backend [P7-T4]`
  - DoD: image builds; container serves `/health` + `/ask`.
- [ ] **P7-T5** — Deploy to Azure (App Service / Container Apps); wire env + secrets.
  - Commit: `docs(p7): azure deployment guide and config [P7-T5]`
  - DoD: public/playground-testable endpoint; secrets via Azure config, not in image.
- [ ] **P7-T6** — Final pass: master index all ✅, links checked, eval numbers current.
  - Commit: `docs(p7): finalize phase index and cross-links [P7-T6]`
  - DoD: docs consistent; no dead links; status accurate.

## Exit criteria
- Deployed, reachable endpoint; bilingual docs + ARCHITECTURE complete.
- Class requirements (≥3 sources, documented, deployable) all demonstrably met.
- Update master index → all ✅.
