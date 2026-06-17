# Deployment

How to build the container and deploy the Repo Expert backend to **Hugging Face Spaces**
(free, always-reachable). Secrets are injected as Space secrets at run time and **never
baked into the image** (see [`Dockerfile`](../Dockerfile) and
[`.dockerignore`](../.dockerignore)).

Prerequisites: a Qdrant Cloud cluster provisioned per [`setup.md`](setup.md) and the
collections already built (`uv run repo-expert ingest`). The vectors live in Qdrant Cloud,
so the container is **stateless** — it only needs the env vars below.

> The legacy Azure (Container Apps / App Service) path is kept as an appendix at the bottom.

---

## 1. Local container run

```bash
docker build -t repo-expert .

# Pass secrets via --env-file (your .env is gitignored and excluded from the image).
# HF Spaces serves on 7860; map it locally.
docker run --rm -p 7860:7860 --env-file .env repo-expert

# Verify
curl -s localhost:7860/health
curl -s localhost:7860/ask -H 'content-type: application/json' \
  -d '{"question": "How does FastAPI handle dependency injection?"}'
```

`/health` returns `200` with `status: ok` (or `degraded` if a collection is unreachable).
The image declares a `HEALTHCHECK` against `/health` and honors `$PORT` (default `7860`).

---

## 2. Hugging Face Spaces (Docker SDK) — recommended

HF Spaces gives a free, public HTTPS endpoint reachable with the dev machine off. The free
CPU tier sleeps when idle, so expect a **~30–60s cold start** on the first request after a
nap (the Phase 8 widget shows a "waking up" state).

### 2.1 Create the Space

1. New Space → **SDK: Docker** → **Blank** template → CPU basic (free).
2. The Space is its own git repo. It needs a `Dockerfile` (this one) plus a `README.md`
   whose YAML frontmatter declares the SDK and port:

   ```yaml
   ---
   title: Repo Expert API
   emoji: 🤖
   colorFrom: indigo
   colorTo: blue
   sdk: docker
   app_port: 7860
   pinned: false
   ---
   ```

### 2.2 Push the code

Either point the Space at this GitHub repo (Settings → "Link to a GitHub repository"), or
push directly:

```bash
git remote add space https://huggingface.co/spaces/<user>/repo-expert
git push space main
```

HF builds the image from the `Dockerfile` and starts the container automatically.

### 2.3 Set secrets (never in the image)

Space → **Settings → Variables and secrets**. Add as **secrets**:

| Key                            | Notes                                              |
|--------------------------------|----------------------------------------------------|
| `AZURE_OPENAI_ENDPOINT`        | Chat LLM endpoint                                  |
| `AZURE_OPENAI_API_KEY`         | Chat LLM key                                       |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | `gpt-4o-mini`                                      |
| `QDRANT_URL`                   | Qdrant Cloud cluster URL (`...:6333`)              |
| `QDRANT_API_KEY`               | Qdrant Cloud key                                   |
| `GITHUB_TOKEN`                 | for the live issues/PRs tool (public instance)     |

And as **public variables** (non-secret):

| Key                    | Value                                                       |
|------------------------|-------------------------------------------------------------|
| `REPO_EXPERT_INSTANCE` | `public` or `portfolio`                                     |
| `QDRANT_EMBED_MODEL`   | `sentence-transformers/all-MiniLM-L6-v2`                    |
| `CORS_ORIGINS`         | the Hostinger site origin once known (e.g. `https://…`); `*` until then |

> `AZURE_SEARCH_ENDPOINT` / `AZURE_SEARCH_API_KEY` are required by `Settings` only for the
> legacy Azure-Search path. On the Qdrant stack set them to any non-empty placeholder so
> startup doesn't fail, or leave the legacy retriever unconfigured.

### 2.4 Verify (PC off)

```bash
curl -s https://<user>-repo-expert.hf.space/health
curl -s https://<user>-repo-expert.hf.space/ask \
  -H 'content-type: application/json' \
  -d '{"question": "How does FastAPI handle dependency injection?"}'
```

Playground: `https://<user>-repo-expert.hf.space/docs`.

**Switch instance** = change one Space variable (`REPO_EXPERT_INSTANCE`) and restart — no
rebuild.

---

## Secret hygiene

- Secrets are **never** in the image: `.env` is in `.dockerignore`; values are supplied at
  run time via HF Space secrets.
- The container runs as a non-root user (`appuser`, uid 10001).
- CORS is config-driven (`CORS_ORIGINS`); tighten from `*` to the site origin once the
  widget ships.

---

## Appendix — Azure (legacy, superseded by HF Spaces)

The project ran on Azure Container Apps before the Phase 7 cost migration. Kept for
reference; **not the current deploy path** and a paid, outward-facing resource — provision
only with explicit owner approval.

```bash
RG=repo-expert-rg; LOC=eastus; ACR=repoexpertacr; ENV=repo-expert-env; APP=repo-expert-api
az group create -n $RG -l $LOC
az acr create -n $ACR -g $RG --sku Basic --admin-enabled true
az acr build -r $ACR -t repo-expert:latest .
az containerapp env create -n $ENV -g $RG -l $LOC
az containerapp create \
  -n $APP -g $RG --environment $ENV \
  --image $ACR.azurecr.io/repo-expert:latest \
  --registry-server $ACR.azurecr.io \
  --target-port 7860 --ingress external \
  --min-replicas 0 --max-replicas 2 \
  --secrets aoai-key=$AZURE_OPENAI_API_KEY qdrant-key=$QDRANT_API_KEY gh-token=$GITHUB_TOKEN \
  --env-vars \
    AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT \
    AZURE_OPENAI_API_KEY=secretref:aoai-key \
    AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini \
    QDRANT_URL=$QDRANT_URL QDRANT_API_KEY=secretref:qdrant-key \
    GITHUB_TOKEN=secretref:gh-token REPO_EXPERT_INSTANCE=public
```
