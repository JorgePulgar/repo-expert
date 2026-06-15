# Phase 4 — FastAPI Backend

**Branch:** `feature/phase-4-api` · **Status:** 🟡 in progress

## Context
Expose the agent over HTTP. Thin FastAPI layer over the Phase 3 `ask()`: request
validation, the agent call, structured response (answer + citations + route taken),
health check, and basic observability. Instance is selected by config/env at startup.

## Why this phase exists
The deliverable must be deployable and testable. A clean API is the boundary for the
Azure deployment (Phase 7) and the optional frontend (Phase 8).

## Prerequisites
- Phase 3 complete (`ask()` works).

## Tasks
- [x] **P4-T1** — FastAPI app factory + settings/instance wired at startup.
  - Commit: `feat(p4): fastapi app factory [P4-T1]`
  - DoD: app boots; active instance logged on startup.
- [x] **P4-T2** — `GET /health` (liveness + which instance/indexes active).
  - Commit: `feat(p4): health endpoint [P4-T2]`
  - DoD: returns 200 with instance name and index status.
- [ ] **P4-T3** — `POST /ask` (validated request → agent → structured answer+citations+route).
  - Commit: `feat(p4): /ask endpoint [P4-T3]`
  - DoD: returns answer, citations, and route taken; validation errors → 422.
- [ ] **P4-T4** — Error handling + request logging/timing middleware.
  - Commit: `feat(p4): error handling and request logging [P4-T4]`
  - DoD: upstream failures → clean 5xx with message; per-request latency logged.
- [ ] **P4-T5** — Optional streaming response for `/ask` (SSE) — defer if time-constrained.
  - Commit: `feat(p4): streaming /ask via sse [P4-T5]`
  - DoD: tokens stream; non-streaming path still works.
- [ ] **P4-T6** — API tests (TestClient) for health + ask (happy path + validation).
  - Commit: `test(p4): api endpoint tests [P4-T6]`
  - DoD: tests cover 200/422/5xx paths.

## Exit criteria
- `uv run uvicorn ...` serves `/health` + `/ask`; OpenAPI docs render.
- Switching instance via env changes behavior without code edit.
- Update master index; open Phase 5.
