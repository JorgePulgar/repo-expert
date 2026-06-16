# Phases — Master Index & Status

Single source of truth for "where are we". Update the **Status** column when a phase
starts/finishes. Each phase file holds its own context, task list, and exit criteria.

Status legend: `⬜ not started` · `🟡 in progress` · `✅ done`

| #  | Phase                          | Branch                          | Status | File |
|----|--------------------------------|---------------------------------|--------|------|
| 0  | Repo & Foundation              | `feature/phase-0-foundation`    | ✅     | [phase-0-foundation.md](phase-0-foundation.md) |
| 1  | Ingestion & Foundry IQ KB      | `feature/phase-1-ingestion`     | ✅     | [phase-1-ingestion.md](phase-1-ingestion.md) |
| 2  | Retrieval Layer                | `feature/phase-2-retrieval`     | ✅     | [phase-2-retrieval.md](phase-2-retrieval.md) |
| 3  | LangGraph Agent                | `feature/phase-3-agent`         | ✅     | [phase-3-agent.md](phase-3-agent.md) |
| 4  | FastAPI Backend                | `feature/phase-4-api`           | ✅     | [phase-4-api.md](phase-4-api.md) |
| 5  | Evaluation                     | `feature/phase-5-eval`          | ✅     | [phase-5-eval.md](phase-5-eval.md) |
| 6  | Portfolio Instance             | `feature/phase-6-portfolio`     | ✅     | [phase-6-portfolio.md](phase-6-portfolio.md) |
| 7  | Migrate to Qdrant & Deploy     | `feature/phase-7-docs-deploy`   | 🟡     | [phase-7-qdrant-deploy.md](phase-7-qdrant-deploy.md) |
| 8  | Chat Widget (Hostinger)        | `feature/phase-8-chat-widget`   | ⬜     | [phase-8-chat-widget.md](phase-8-chat-widget.md) |

## Conventions (recap — full rules in root `CLAUDE.md`)
- One **branch per phase**, one **commit per task**.
- Commit subject: `type(pN): summary [PN-Tn]`.
- Mark a task `[x]` only when its **DoD** is met.
- Public-repo (FastAPI) instance ships first; portfolio is Phase 6 (config swap).

## Dependency order
0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8. Phase 7 re-scoped (2026-06) from "Docs & Deploy" to the
Qdrant migration + cheap deploy after the pivot to a personal-brand website chat; Phase 8
(chat widget for Hostinger) is now the product feature, no longer optional, and depends on
Phase 7's deployed backend.
