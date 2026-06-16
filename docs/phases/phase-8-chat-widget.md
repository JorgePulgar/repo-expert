# Phase 8 — Frontend (optional)

**Branch:** `feature/phase-8-frontend` · **Status:** ⬜ not started

## Context
Optional "try it live" UI over the Phase 4 API. React + TypeScript. **Node deps via
pnpm only** (never npm/npx — see root CLAUDE.md). Only build if time allows after the
core deliverable ships.

## Why this phase exists
Improves the recruiter demo (portfolio instance) — a chat box beats curl. Strictly a
bonus; the API + docs are the real deliverable.

## Prerequisites
- Phase 4 complete (API). Ideally Phase 6 (portfolio instance) for the demo.

## Tasks
- [ ] **P8-T1** — Scaffold React+TS app (Vite), pnpm-managed.
  - Commit: `chore(p8): scaffold react+ts frontend (pnpm) [P8-T1]`
  - DoD: `pnpm dev` serves a blank app; lint configured.
- [ ] **P8-T2** — API client for `/ask` + `/health` (typed).
  - Commit: `feat(p8): typed api client [P8-T2]`
  - DoD: calls backend; types match API response.
- [ ] **P8-T3** — Chat UI: question input, answer render, citations as links.
  - Commit: `feat(p8): chat ui with citations [P8-T3]`
  - DoD: ask → answer with clickable file/line + doc/url citations.
- [ ] **P8-T4** — Show route taken + (if enabled) streaming tokens.
  - Commit: `feat(p8): route badge and streaming render [P8-T4]`
  - DoD: UI shows which source answered; streams if backend supports SSE.
- [ ] **P8-T5** — Deploy frontend (static host) pointed at deployed API.
  - Commit: `docs(p8): frontend deployment [P8-T5]`
  - DoD: live URL talks to the deployed backend.

## Exit criteria
- Live demo UI for the portfolio instance.
- Update master index; note in README.
