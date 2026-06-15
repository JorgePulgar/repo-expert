# Setup & Azure Provisioning

What to provision before running ingestion (Phase 1). All secrets go in `.env`
(gitignored) — see `.env.example` for the variable names.

## 1. Azure AI Search (agentic-retrieval capable)
Foundry IQ knowledge bases require an Azure AI Search service that supports **agentic
retrieval**. Use a tier/region that offers it (Basic or higher; semantic ranker enabled).

- Create the service in the Azure portal.
- Copy the **endpoint** → `AZURE_SEARCH_ENDPOINT`.
- Keys → copy an admin key → `AZURE_SEARCH_API_KEY` (admin needed to create indexes,
  knowledge sources, and the knowledge base).

## 2. Azure OpenAI deployments
Two deployments are needed:
- **Embeddings** (e.g. `text-embedding-3-large`) → `AZURE_OPENAI_EMBED_DEPLOYMENT`.
- **Chat for KB query planning** — must be **gpt-4o / gpt-4.1 / gpt-5 series** (only these
  are supported for Foundry IQ query planning) → `AZURE_OPENAI_CHAT_DEPLOYMENT`.

Copy resource endpoint → `AZURE_OPENAI_ENDPOINT`, key → `AZURE_OPENAI_API_KEY`, and set
`AZURE_OPENAI_API_VERSION`.

## 3. Microsoft Foundry (new) project
- Sign in to Microsoft Foundry, ensure **New Foundry** toggle is on.
- Create (or pick) a project; connect it to the Azure AI Search service above.
- The knowledge base + knowledge sources are created in Phase 1 (portal or programmatically).

## 4. GitHub token (Phase 2 — live issues tool)
Fine-grained PAT, **Public Repositories (read-only)** is enough for `fastapi/fastapi`.
→ `GITHUB_TOKEN`. Bumps API rate limit 60→5000 req/hr. Never commit it.

## 5. App config
- `cp .env.example .env`, fill the values above.
- `REPO_EXPERT_INSTANCE=public` (or `portfolio`).
- Verify: `uv run pytest` (config smoke tests) and the settings loader picks up `.env`.

## Design notes
- KB **retrieval reasoning effort = low** — agentic headline lives in our LangGraph, not
  the managed service (build-vs-buy boundary; see `CLAUDE.md`).
- Index + KB names come from the instance config (`src/repo_expert/config/instance.py`),
  not hard-coded.
