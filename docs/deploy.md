# Deployment

How to build the container and deploy the Repo Expert backend to Azure. Secrets are
injected as environment variables at run time and **never baked into the image** (see
[`Dockerfile`](../Dockerfile) and [`.dockerignore`](../.dockerignore)).

Prerequisites: Azure resources provisioned per [`setup.md`](setup.md) and the indexes/KB
already built (`uv run repo-expert ingest`). Indexes live in Azure AI Search, so the
container is stateless — it only needs the env vars.

---

## 1. Local container run

```bash
docker build -t repo-expert .

# Pass secrets via --env-file (your .env is gitignored and excluded from the image).
docker run --rm -p 8000:8000 --env-file .env repo-expert

# Verify
curl -s localhost:8000/health
curl -s localhost:8000/ask -H 'content-type: application/json' \
  -d '{"question": "How does FastAPI handle dependency injection?"}'
```

`/health` returns `200` with `status: ok` (or `degraded` if an index is unreachable). The
image declares a `HEALTHCHECK` against `/health`.

---

## 2. Azure Container Apps (recommended)

Container Apps gives a public HTTPS endpoint, scale-to-zero, and first-class secret
management. Replace the placeholder values.

```bash
RG=repo-expert-rg
LOC=eastus
ACR=repoexpertacr            # must be globally unique
ENV=repo-expert-env
APP=repo-expert-api

# 0. Resource group + container registry
az group create -n $RG -l $LOC
az acr create -n $ACR -g $RG --sku Basic --admin-enabled true

# 1. Build the image in ACR (no local Docker needed)
az acr build -r $ACR -t repo-expert:latest .

# 2. Container Apps environment
az containerapp env create -n $ENV -g $RG -l $LOC

# 3. Create the app with secrets + env vars
az containerapp create \
  -n $APP -g $RG --environment $ENV \
  --image $ACR.azurecr.io/repo-expert:latest \
  --registry-server $ACR.azurecr.io \
  --target-port 8000 --ingress external \
  --min-replicas 0 --max-replicas 2 \
  --secrets \
    aoai-key=$AZURE_OPENAI_API_KEY \
    search-key=$AZURE_SEARCH_API_KEY \
    gh-token=$GITHUB_TOKEN \
  --env-vars \
    AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT \
    AZURE_OPENAI_API_KEY=secretref:aoai-key \
    AZURE_OPENAI_API_VERSION=2024-10-21 \
    AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o \
    AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-large \
    AZURE_SEARCH_ENDPOINT=$AZURE_SEARCH_ENDPOINT \
    AZURE_SEARCH_API_KEY=secretref:search-key \
    GITHUB_TOKEN=secretref:gh-token \
    REPO_EXPERT_INSTANCE=public
```

The public FQDN is printed on create (and via
`az containerapp show -n $APP -g $RG --query properties.configuration.ingress.fqdn -o tsv`).
Test the playground at `https://<fqdn>/docs`.

**Switch instance** = update one env var, no rebuild:

```bash
az containerapp update -n $APP -g $RG --set-env-vars REPO_EXPERT_INSTANCE=portfolio
```

### Update / redeploy

```bash
az acr build -r $ACR -t repo-expert:latest .
az containerapp update -n $APP -g $RG --image $ACR.azurecr.io/repo-expert:latest
```

---

## 3. Azure App Service (container) — alternative

```bash
az acr build -r $ACR -t repo-expert:latest .
az appservice plan create -n repo-expert-plan -g $RG --is-linux --sku B1
az webapp create -n repo-expert-api -g $RG -p repo-expert-plan \
  --deployment-container-image-name $ACR.azurecr.io/repo-expert:latest
# App settings (secrets) — set each AZURE_*/GITHUB_TOKEN/REPO_EXPERT_INSTANCE key:
az webapp config appsettings set -n repo-expert-api -g $RG --settings \
  WEBSITES_PORT=8000 AZURE_OPENAI_ENDPOINT=... AZURE_OPENAI_API_KEY=... # etc.
```

App Service injects app settings as env vars, so `Settings` picks them up unchanged.

---

## Secret hygiene

- Secrets are **never** in the image: `.env` is in `.dockerignore`; values are supplied at
  run time via Container Apps secrets / App Service app settings.
- The container runs as a non-root user (`appuser`, uid 10001).
- For production, prefer a managed identity + Key Vault references over plain secret values.

> **Note:** the live Azure deployment is a paid, outward-facing resource. Provision and
> deploy only with explicit owner approval (see root `CLAUDE.md`).
