# Phase 0 — Repo & Foundation

**Branch:** `feature/phase-0-foundation` · **Status:** 🟡 in progress

## Context
Stand up the skeleton everything else builds on: project layout, Python tooling (uv),
config system, secrets handling, and the GitHub remote. No RAG logic yet — just a clean,
runnable, well-structured base. The **config-driven instance switching** requirement
starts here as a typed config model so later phases never hard-code the target repo.

## Why this phase exists
A wrong foundation (no config abstraction, secrets leaking, ad-hoc layout) is expensive
to undo once 8 phases sit on top. Get the seams right first.

## Prerequisites
- Azure subscription access (for later phases; no provisioning required yet).
- GitHub account + ability to create a remote repo.

## Tasks
- [x] **P0-T1** — Create GitHub remote and push initial `main`.
  - Commit: `chore(p0): initialize repo with CLAUDE.md and phase docs [P0-T1]`
  - DoD: remote exists, `main` pushed with CLAUDE.md + `docs/phases/`, branch protection optional.
- [x] **P0-T2** — Initialize uv project (`pyproject.toml`, Python 3.12, `uv.lock`).
  - Commit: `chore(p0): scaffold uv project with python 3.12 [P0-T2]`
  - DoD: `uv run python --version` prints 3.12.x; `uv.lock` committed.
- [x] **P0-T3** — Define package layout under `src/repo_expert/` (`config/`, `ingestion/`, `retrieval/`, `agent/`, `api/`, `eval/`).
  - Commit: `chore(p0): create src/repo_expert package skeleton [P0-T3]`
  - DoD: importable package; empty `__init__.py` per module; `uv run python -c "import repo_expert"` works.
- [x] **P0-T4** — Settings loader (pydantic-settings) reading `.env`; fail-fast on missing required keys.
  - Commit: `feat(p0): env-backed settings loader [P0-T4]`
  - DoD: loads Azure/GitHub keys from `.env`; clear error naming the missing var.
- [x] **P0-T5** — Typed **instance config** model + two configs: `public` (FastAPI target) and `portfolio` (stub).
  - Commit: `feat(p0): instance config model with public/portfolio selection [P0-T5]`
  - DoD: `REPO_EXPERT_INSTANCE` selects config; config carries target repo, index names, and active "source 3" (issues vs career_kb); selectable without code change.
- [x] **P0-T6** — Dev tooling: ruff (lint+format), pytest, pre-commit hook, `make`/`uv` task shortcuts.
  - Commit: `chore(p0): add ruff, pytest, pre-commit [P0-T6]`
  - DoD: `uv run ruff check .` and `uv run pytest` both pass on the skeleton.
- [ ] **P0-T7** — Smoke test + minimal `README` stub describing how to run.
  - Commit: `test(p0): config + settings smoke tests [P0-T7]`
  - DoD: a test asserts each instance config loads and exposes required fields.

## Exit criteria
- Repo pushed to GitHub; `uv run pytest` green; lint clean.
- Switching `REPO_EXPERT_INSTANCE` between `public`/`portfolio` returns different config, no code edit.
- Secrets only in `.env` (gitignored); `.env.example` complete.
- Update `docs/phases/README.md` status → ✅ and open Phase 1.
