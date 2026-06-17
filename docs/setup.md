# Setup & Provisioning

What to provision before running ingestion. All secrets go in `.env` (gitignored) — see
`.env.example` for the variable names.

## 1. Qdrant Cloud (vector store + server-side inference)
Retrieval runs on a **Qdrant Cloud free-tier cluster** (0.5 vCPU / 1 GB RAM / 4 GB disk —
ample for the ~3k-chunk corpus). Embeddings are produced **server-side** by Qdrant Cloud
Inference, so no embedding model runs locally or in the deploy image.

- Create a free cluster at <https://cloud.qdrant.io>.
- Copy the cluster **URL** (REST, port `:6333`) → `QDRANT_URL`.
- Create an API key → `QDRANT_API_KEY`.
- Embedding model → `QDRANT_EMBED_MODEL`. Default `sentence-transformers/all-MiniLM-L6-v2`
  (384-dim). **Note:** `mxbai-embed-large-v1` is *not* allowed on the free tier — confirm
  the "Cost: Free" label in **Console → Inference** before changing the model.
- Collections are created by `uv run repo-expert provision` (config-driven names per
  instance); ids/dims are not hard-coded.

## 2. Azure OpenAI (chat only)
The agent's routing, generation, and grounding use one cheap chat model. (Embeddings no
longer use Azure — they run in Qdrant.)

- Create a **`gpt-4o-mini`** deployment → `AZURE_OPENAI_CHAT_DEPLOYMENT`.
- Resource endpoint → `AZURE_OPENAI_ENDPOINT`, key → `AZURE_OPENAI_API_KEY`, and set
  `AZURE_OPENAI_API_VERSION`.
- `AZURE_OPENAI_EMBED_DEPLOYMENT` is unused on the Qdrant stack; leave it blank.

## 3. GitHub token (live issues tool — public instance)
Fine-grained PAT, **Public Repositories (read-only)** is enough for `fastapi/fastapi`.
→ `GITHUB_TOKEN`. Bumps API rate limit 60→5000 req/hr. Never commit it.

## 4. App config
- `cp .env.example .env`, fill the values above.
- `REPO_EXPERT_INSTANCE=public` (or `portfolio`).
- Provision + verify: `uv run repo-expert provision` then `uv run pytest` (config smoke
  tests); the settings loader picks up `.env`.

## Design notes
- **Managed vector store, built fusion** — Qdrant stores/searches; the agentic headline
  (routing, RRF fusion, fallback, grounding) lives in our LangGraph (build-vs-buy boundary;
  see `CLAUDE.md`).
- Collection names come from the instance config (`src/repo_expert/config/instance.py`),
  not hard-coded.
