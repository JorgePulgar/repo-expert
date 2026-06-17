# Phase 7 — Migrate retrieval to Qdrant & deploy cheaply

**Branch:** `feature/phase-7-docs-deploy` · **Status:** 🟡 in progress

## Context — strategic pivot

The project graduates from "class deliverable" to a **production chat on Jorge's personal
brand website** (Hostinger). The class-driven Azure stack is too expensive for a
low-traffic personal site: **Azure AI Search Basic ≈ $75/month flat**, regardless of
traffic. This phase swaps the *retrieval backend* to **Qdrant Cloud free tier** (vector
store + free inference embeddings) and the generation model to a cheap one, then deploys
the backend to a **free host** reachable with the dev machine off.

Target recurring cost: **~$0–1/month** (Qdrant free, free embeddings, cheap LLM, free
host) vs ~$75+/month on Azure.

**What stays (the design payoff):** LangGraph agent (router → retrieve → generate →
grounding → fallback), FastAPI API, instance config, eval harness, the live GitHub issues
tool. Retrieval is already behind `retrieve_kb` + the registry, so the migration is
contained to **ingestion upload + the `kb` retriever**. Both instances (public/FastAPI and
portfolio) keep working; only their KB backend changes from Azure AI Search to Qdrant.

> Earlier P7 tasks (ARCHITECTURE.md, README.md, README.es.md, Dockerfile, deploy guide)
> were written against the Azure stack. They remain valid until the migration lands, then
> are refreshed in **P7-T7**. The Azure deployment path (`docs/deploy.md`) is superseded by
> the HF Spaces path; keep it as an alternative or trim it in P7-T7.

## Why this phase exists

A personal-brand chat must be cheap, always-reachable, and still read as a real,
modern RAG on a CV. Qdrant + LangGraph is a stronger, more recognizable CV story than the
proprietary Azure Foundry IQ KB, at a fraction of the cost.

## Prerequisites

- Phases 1–6 complete (ingestion, retrieval abstraction, agent, API, eval, both instances).
- A Qdrant Cloud free-tier cluster provisioned (0.5 vCPU / 1 GB RAM / 4 GB disk — verified
  ample for the ~3k-chunk corpus).

## Decisions (locked 2026-06-16)

1. **Embedding model:** ~~`mxbai-embed-large-v1` (1024-dim)~~ → **`all-MiniLM-L6-v2`
   (384-dim)**. **Gate result (P7-T2, 2026-06-17):** mxbai is **blocked on the Qdrant free
   tier** (upsert returns `401: "This model: mixedbread-ai/mxbai-embed-large-v1 is not
   allowed in free tier"`). Adopted the pre-authorized MiniLM fallback, served free via
   **server-side cloud inference** (`cloud_inference=True`, `models.Document`). Trade-off:
   lower dim + ~256-token input truncation; T6 eval quantifies the relevance impact.
2. **LLM (generation + routing + grounding):** `gpt-4o-mini` on **Azure OpenAI** — keeps
   the current client, least change. Azure OpenAI is retained for chat; embeddings move to
   Qdrant.
3. **Cold start:** accept the free-host ~30–60s wake-up. The Phase 8 widget shows a
   "waking up" state; no keep-warm cron for now (can add later if it annoys).

## Tasks

- [x] **P7-T1** — Qdrant client + collection schema; provisioning script.
  - Commit: `feat(p7): qdrant client and collection schema [P7-T1]`
  - DoD: a `clients`-level Qdrant client; collections (docs/code/career) created with the
    chosen vector dim + payload fields (mirrors current index fields: `source_kind`,
    `repo_slug`, `file_path`, `url`, `section_path`, `start_line`/`end_line`). Config-driven
    collection names per instance.
- [x] **P7-T2** — Embeddings via Qdrant Cloud Inference (or chosen provider).
  - Commit: `feat(p7): qdrant inference embeddings [P7-T2]`
  - DoD: `embed_chunks`/`embed_texts` path produces vectors from the chosen free model;
    dim derived live; batching + retry preserved. OpenAI/Azure embedding code removed or
    gated behind config.
- [x] **P7-T3** — Ingestion upload → Qdrant (replace `upload_chunks` target).
  - Commit: `feat(p7): upsert chunks into qdrant [P7-T3]`
  - DoD: `repo-expert ingest` populates Qdrant collections for both instances; stable-id
    upsert (no duplicates on re-ingest); pipeline otherwise unchanged.
- [x] **P7-T4** — `kb` retriever against Qdrant (replace Azure AI Search retriever).
  - Commit: `feat(p7): qdrant kb retriever [P7-T4]`
  - DoD: `retrieve_kb` returns `RetrievalResult`s from Qdrant (vector + optional payload
    filtering); same interface, so registry/agent/API need no changes. Issues retriever
    untouched.
- [ ] **P7-T5** — Cheap LLM swap for generation/routing/grounding.
  - Commit: `feat(p7): switch generation to cheap model [P7-T5]`
  - DoD: chat/JSON calls use the chosen cheap model via config; no behavioral regression in
    a smoke `/ask`.
- [ ] **P7-T6** — Re-run eval on the Qdrant stack; refresh results.
  - Commit: `test(p7): eval on qdrant backend [P7-T6]`
  - DoD: `docs/eval-results-*.md/json` regenerated; routing/relevance/groundedness compared
    against the Azure baseline; deltas noted (esp. if the free embed model shifts code
    relevance).
- [ ] **P7-T7** — Docs refresh: Azure → Qdrant/HF across all docs.
  - Commit: `docs(p7): docs reflect qdrant + hf deploy [P7-T7]`
  - DoD: `ARCHITECTURE.md`, `README.md`, `README.es.md`, `CLAUDE.md` architecture/stack
    sections, and `.env.example` describe Qdrant + the cheap LLM + the free host; the
    build-vs-buy paragraph updated (buy = Qdrant managed vector store + free inference;
    build = chunking, LangGraph, issues tool). `docs/setup.md` covers Qdrant provisioning.
- [ ] **P7-T8** — Containerize + deploy backend to Hugging Face Spaces.
  - Commit: `chore(p7): deploy backend to hf spaces [P7-T8]`
  - DoD: backend image builds and runs on HF Spaces (free); `/health` + `/ask` reachable at
    a public URL with the dev machine off; secrets (Qdrant key, LLM key, `GITHUB_TOKEN`)
    set via Space secrets, never in the image; **CORS allows the Hostinger domain**.
    `docs/deploy.md` rewritten for the HF Spaces + Qdrant path (Azure path trimmed or kept
    as an appendix).

## Exit criteria

- Both instances retrieve from Qdrant; eval re-run and documented.
- Public, always-reachable backend endpoint on a free host (PC off), CORS-ready for the
  website, secrets in host config not the image.
- Docs consistent with the Qdrant + HF + cheap-LLM stack.
- Recurring cost demonstrably ~$0–1/month.

_Tasks here are re-scoped from the prior "Docs & Deploy" phase; the Azure-era docs and
Dockerfile are reused and refreshed, not thrown away._
