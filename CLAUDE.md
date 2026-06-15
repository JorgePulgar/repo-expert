# Repo Expert — Agentic RAG for Codebases

> One generalizable agentic RAG that answers questions about any GitHub repo it's
> pointed at. Two instances of the **same** app, differing only in data sources/config:
> 1. **Class deliverable** — pointed at a serious public repo (FastAPI).
> 2. **Recruiter demo** — same app, pointed at my portfolio repos.

This file is the **always-loaded context**: rules + minimal map. Deep context for any
given chunk of work lives in its phase file under `docs/phases/`. Keep this file short.

---

## How development is organized

Work is split into **phases**. Each phase has one file in `docs/phases/phase-N-*.md`
containing: the phase's context (what/why), its task list, and exit criteria.

- **Master index + live status:** `docs/phases/README.md`. Update it when a phase or
  task state changes. It is the single source of truth for "where are we".
- **Tasks** are checkboxes: `[ ]` open, `[x]` done. Mark `[x]` only when the task's
  **Definition of Done (DoD)** is met — not when code is merely written.
- **One commit per task.** Conventional Commits, with the task ID in the subject.
  Example: `feat(p3): router node classifies intent [P3-T2]`
- **One branch per phase:** `feature/phase-N-slug`. Open a PR and merge to `main` at
  phase exit. Never commit secrets.

### Commit rules
- Format: `type(pN): summary [PN-Tn]` — types: `feat`, `fix`, `docs`, `chore`, `test`, `refactor`.
- Subject ≤ ~72 chars. Body only when the "why" isn't obvious.
- Co-author trailer on every commit:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- Do **not** commit or push unless I ask.

---

## Architecture (one-paragraph map) — option C (build-vs-buy)

FastAPI backend exposes a `/ask` endpoint. A **LangGraph** agent orchestrates:
router → retrieve → fallback → corrective/grounding → generate with citations.
Retrieval backend is a **Foundry IQ knowledge base** (built on Azure AI Search agentic
retrieval) over our own custom-chunked indexes; LangGraph wraps it and owns the headline
reasoning (routing, fallback, self-correction). LLM is **Azure OpenAI**. Three
heterogeneous knowledge sources (different *kinds*): (1) docs/markdown and (2) source code
(code-aware chunking) — both indexed into the **KB**; (3) GitHub issues/PRs **live via API
as a tool outside the KB** — swapped for a **Career Knowledge Base** (indexed into the KB)
in the portfolio instance.

**Build-vs-buy boundary:** *buy* = Foundry IQ/AI Search managed retrieval over indexed
content; *build* = custom code-aware chunking + index, LangGraph orchestration + corrective
grounding, and the live GitHub issues tool. Keep KB **reasoning effort low** so the agentic
headline lives in our LangGraph, not the managed service.

## Config-driven targeting (core requirement)
Switching instance = **changing config, not code**. A single config object selects the
target repo, which indexes to use, and which "source 3" is active (issues vs career KB).
Designed in Phase 1, honored everywhere after.

---

## Stack & tooling
- **Python** 3.12, dependency manager **uv** (`uv add`, `uv run`, `uv.lock` committed).
- Retrieval backend: **Foundry IQ knowledge base** on Azure AI Search agentic retrieval
  (hybrid + semantic rerank), over custom-built indexes. KB reasoning effort = low.
- Orchestration: LangGraph (the CV-relevant piece — corrective/agentic RAG wrapping the KB).
- Live source: GitHub issues/PRs tool, outside the KB.
- LLM: Azure OpenAI (embeddings + KB query planning + agent generation; gpt-4o/4.1/5 for KB planning).
- Frontend (optional, Phase 8): React + TS. **Node deps via pnpm only**, never npm/npx.
- Secrets in `.env` (gitignored). `.env.example` documents required keys. Never commit keys.

## Class requirements (must satisfy)
- ≥ 3 heterogeneous knowledge sources.
- Fully documented: what it does, what it's for, what knowledge it has.
- Deployable to Azure / testable in the playground.

## Deliverables
- Bilingual README (`README.md` EN + `README.es.md`), `ARCHITECTURE.md`.
- Curated eval Q/A set + documented retrieval-relevance & groundedness results.
- Config-driven instance switching.

---

## Working agreements for the agent
- Before starting work, read the relevant `docs/phases/phase-N-*.md` for full context.
- Keep `docs/phases/README.md` status current.
- One task → one commit (when I ask to commit). Don't batch unrelated tasks.
- Public-repo (FastAPI) instance is built first; portfolio instance is Phase 6.
- Ask before provisioning paid Azure resources or anything outward-facing/irreversible.
