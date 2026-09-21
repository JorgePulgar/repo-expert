# Deployment

How to build the container and deploy the Repo Expert backend to **Azure Container Apps**,
with scale-to-zero so an idle app costs nothing. Secrets are injected at run time as
Container App secrets and **never baked into the image** (see [`Dockerfile`](../Dockerfile)
and [`.dockerignore`](../.dockerignore)).

Prerequisites: a Qdrant Cloud cluster provisioned per [`setup.md`](setup.md) with the
collections already built (`uv run repo-expert ingest`), and an Azure OpenAI / Foundry
resource with a chat deployment. The vectors live in Qdrant Cloud, so the container is
**stateless** — it only needs the env vars below.

> **Why not Hugging Face Spaces?** It was the original Phase 7 target, but HF now gates
> Docker Spaces behind a PRO subscription: repo creation returns `402 Payment Required` —
> *"Static Spaces are free for everyone, but hosting Gradio and Docker Spaces on free
> cpu-basic requires a PRO subscription."* Static Spaces stay free but cannot run Python.
> The HF path is kept as an appendix in case that changes.

---

## 1. Local container run

```bash
docker build -t repo-expert .

# Pass secrets via --env-file (your .env is gitignored and excluded from the image).
docker run --rm -p 7860:7860 --env-file .env repo-expert

# Verify
curl -s localhost:7860/health
curl -s localhost:7860/ask -H 'content-type: application/json' \
  -d '{"question": "What projects has Jorge worked on?"}'
```

`/health` returns `200` with `status: ok` (or `degraded` if a collection is unreachable).
The image honors `$PORT` (default `7860`) and runs as non-root `appuser` (uid 10001).

---

## 2. Azure Container Apps — current deploy path

Scale-to-zero plus the monthly free grant means a low-traffic personal-site backend costs
effectively nothing, and stays reachable with the dev machine off.

### 2.1 Push the image to a registry

Container Apps pulls from any registry it can reach. This project uses Docker Hub:

```bash
docker build -t <dockerhub-user>/repo-expert:<tag> .
docker push <dockerhub-user>/repo-expert:<tag>
```

> **Use an immutable tag** (`p7t8-2`, a date, a git SHA) — not `:latest`. Container Apps
> caches by tag: redeploying the same `:latest` after a rebuild silently keeps serving the
> old image, even in a brand-new revision. This cost time during P7-T8.

> **Do not** create an Azure Container Registry for this. ACR Basic is ~$5/month **flat** —
> the same fixed-fee trap Phase 7 removed when it dropped Azure AI Search. Docker Hub and
> ghcr.io are free. (GHCR needs a **classic** PAT with `write:packages`; fine-grained PATs
> are rejected with `denied`.)

### 2.2 Create the environment

```bash
az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights

az containerapp env create \
  --name cae-repo-expert --resource-group rg-repo-expert \
  --location swedencentral --logs-destination none
```

`--logs-destination none` is deliberate: the default attaches a Log Analytics workspace,
which bills separately. Add it back if you want queryable logs.

### 2.3 Create the app

```bash
az containerapp create \
  --name ca-repo-expert --resource-group rg-repo-expert \
  --environment cae-repo-expert \
  --image docker.io/<dockerhub-user>/repo-expert:<tag> \
  --target-port 7860 --ingress external \
  --min-replicas 0 --max-replicas 1 \
  --cpu 0.5 --memory 1.0Gi \
  --secrets azure-openai-api-key=... qdrant-url=... qdrant-api-key=... \
  --env-vars AZURE_OPENAI_API_KEY=secretref:azure-openai-api-key ...
```

`--min-replicas 0` is what makes idle free; the trade-off is a cold start on the first
request after a nap (the Phase 8 widget shows a "waking up" state).

### 2.4 Configuration

As **secrets** (`--secrets`, referenced via `secretref:`):

| Key                     | Secret name             | Notes                                     |
|-------------------------|-------------------------|-------------------------------------------|
| `AZURE_OPENAI_API_KEY`  | `azure-openai-api-key`  | Chat LLM key                              |
| `AZURE_SEARCH_ENDPOINT` | `azure-search-endpoint` | Unused on Qdrant, but `Settings` requires it non-empty |
| `AZURE_SEARCH_API_KEY`  | `azure-search-api-key`  | Same — a placeholder is fine              |
| `QDRANT_URL`            | `qdrant-url`            | Qdrant Cloud cluster URL (`...:6333`)     |
| `QDRANT_API_KEY`        | `qdrant-api-key`        | Qdrant Cloud key                          |
| `GITHUB_TOKEN`          | `github-token`          | Live issues/PRs tool (public instance only) |

As plain **env vars**:

| Key                            | Value                                          |
|--------------------------------|------------------------------------------------|
| `AZURE_OPENAI_ENDPOINT`        | `https://<resource>.services.ai.azure.com`      |
| `AZURE_OPENAI_API_VERSION`     | `2024-10-21`                                    |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | `gpt-5-mini`                                    |
| `QDRANT_EMBED_MODEL`           | `intfloat/multilingual-e5-small`                |
| `REPO_EXPERT_INSTANCE`         | `public` or `portfolio`                         |
| `CORS_ORIGINS`                 | the site origin(s) allowed to call the API      |
| `RATE_LIMIT_PER_HOUR`          | per-IP budget for `/ask` (default `10`, `0` disables) |

**Switch instance** = change `REPO_EXPERT_INSTANCE` and roll a revision — no rebuild.

### 2.5 Redeploy after a code change

```bash
docker build -t <user>/repo-expert:<new-tag> . && docker push <user>/repo-expert:<new-tag>
az containerapp update --name ca-repo-expert --resource-group rg-repo-expert \
  --image docker.io/<user>/repo-expert:<new-tag> --revision-suffix <suffix>
```

### 2.6 Verify (PC off)

```bash
URL=https://ca-repo-expert.<env-suffix>.swedencentral.azurecontainerapps.io
curl -s $URL/health
curl -s $URL/ask -H 'content-type: application/json' \
  -d '{"question": "What is Jorge'\''s experience with RAG systems?"}'
```

Playground: `$URL/docs`. A healthy response names every active collection with its point
count, e.g. `docs: 2146 · code: 941 · career: 22`.

> Connections are kept alive through the ingress, so right after a new revision you may
> still receive a cached response from the previous one. Add a cache-buster
> (`/health?cb=$RANDOM`) to confirm what is actually live.

---

## 3. Cost

| Item | Cost |
|---|---|
| Container Apps, scale-to-zero, low traffic | covered by the monthly free grant |
| Qdrant Cloud free tier | $0 |
| Embeddings (Qdrant server-side inference) | $0 |
| `gpt-5-mini` | $0.25/1M in, $2.00/1M out — ~$0.60/month at 200 questions |

> **Subscription expiry.** This deployment runs on an Azure **free trial**: $200 credit,
> 30 days from **2026-09-20**. When it lapses the subscription and every resource in it go
> with it — which is exactly how the previous Foundry resource vanished and broke the stack.
> Convert to pay-as-you-go, or move to the `Azure for Students` subscription, before then.

---

## Abuse protection

`/ask` is unauthenticated and spends money on every call, so it is rate-limited to
`RATE_LIMIT_PER_HOUR` questions per IP (default 10), returning `429` with `Retry-After`
once exceeded. Throttled requests are rejected **before** any LLM call, so they cost
nothing. `/health` is deliberately exempt: the chat page pings it on load to warm the
scale-to-zero container.

> **CORS is not a security control here.** It is enforced by browsers only — a script or
> `curl` calling the endpoint directly ignores it entirely. The rate limit, not
> `CORS_ORIGINS`, is what protects the credit.

The counter is in-process, which is correct at `--max-replicas 1`. Scaling out would give
each replica its own counter (effective limit `limit × replicas`); move the state to Redis
or the ingress if that day comes.

Second line of defence: an Azure budget (`repo-expert-guard`, $50/month) alerts the
subscription owner at 50% and 80% of spend.

---

## Secret hygiene

- Secrets are **never** in the image: `.env` is in `.dockerignore`; values are supplied at
  run time as Container App secrets.
- The container runs as a non-root user (`appuser`, uid 10001).
- CORS is config-driven (`CORS_ORIGINS`); tighten from `*` to the site origin once the
  widget ships (P8-T5).

---

## Appendix — Hugging Face Spaces (requires PRO)

The original Phase 7 target. Still works **with a PRO subscription** ($9/month). The Space
needs a `README.md` whose YAML frontmatter declares the SDK and port:

```yaml
---
title: Repo Expert API
emoji: 🤖
sdk: docker
app_port: 7860
---
```

Push the repo to the Space's git remote and set the same keys as Space secrets. The free
CPU tier sleeps when idle (~30–60s cold start).
