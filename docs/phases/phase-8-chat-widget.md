# Phase 8 — Chat page for the personal site (`/chat.html`)

**Branch:** `feature/phase-8-chat-widget` · **Status:** 🟡 in progress

## Context

A **dedicated chat page** on Jorge's personal-brand site (`https://jorgepulgar.com/chat.html`,
Hostinger shared hosting) that answers questions about Jorge and his projects via the
**portfolio instance**. Not a floating support-bubble: a full page a visitor arrives at
deliberately, with copy explaining what the chat knows, what to ask it, and where it stops.

The page is pure frontend; it calls the deployed backend's `/ask` over HTTPS (Azure
Container Apps, from Phase 7) and renders the answer with citations.

**Hosting reality:** Hostinger shared hosting serves only static files and PHP — it
**cannot** run the Python backend. No backend runs on Hostinger.

## Constraints imposed by `jorge-pulgar-web` (audited 2026-09-20)

These are not preferences; they are facts about the site repo, and they settle three
decisions that were previously open.

1. **No build step.** The site's `CLAUDE.md` states a hard rule: *"pure HTML/CSS/JS — no
   npm, no framework, no build step."* So the client is **vanilla JS**, no Preact, no pnpm,
   no bundler.
2. **CSP `script-src 'self'`** — assets cannot be loaded from Azure or a CDN. `rex-chat.js`
   and `rex-chat.css` must be **served from the site itself**.
3. **CSP `connect-src` currently blocks the backend.** It allows only `'self'` + Google
   Analytics. Until the Azure origin is added to `connect-src` in **both** `.htaccess` (the
   live one on Apache/Hostinger) and `_headers`, every `fetch()` is silently blocked by the
   browser.
4. **Spanish for all UI copy.** English only in code comments.
5. **Style with the site's design system.** The page should inherit `styles.css`, so scope
   class names with a `rex-` prefix rather than isolating in a shadow DOM or an iframe.

## Division of labour

The handoff between the two repos is **two files copied into `jorge-pulgar-web/deploy/`**.

**Rule:** anything that breaks when the `/ask` contract changes lives in `repo-expert`;
anything that breaks when the site's look or SEO changes lives in `jorge-pulgar-web`.

| `repo-expert` (this repo) | `jorge-pulgar-web` |
|---|---|
| `rex-chat.js` — `/ask` client, state, render, cold-start ping, errors | `chat.html` — page shell, nav, footer, Spanish explainer copy |
| `rex-chat.css` — component styles, `rex-` scoped | Wiring the two files in; design-system alignment |
| A standalone demo page for local testing | CSP `connect-src` in `.htaccess` **and** `_headers` |
| `CORS_ORIGINS` on the backend | `sitemap.xml`, `llms.txt`, canonical + OG meta |
| Phase docs, task tracking | Nav links from `portfolio.html` / `portfolio/repo-expert.html` |

> The website repo has its own queue: `.claude/TASKS.md` **Phase 4 — RAG chat embed**
> (A8 gating + endpoint, A9 the embed) and a spec in `.claude/CONTEXT.md`. A8 is answered
> by decision 6 below; A9 moves from `/portfolio.html` to `/chat.html` per the decision
> below, which also needs the architecture block and `sitemap.xml` updated there.

### Known fixes owed in `jorge-pulgar-web` (found during the Phase 7 audit)

- `portfolio/repo-expert.html` meta description says **"Desplegado en Hugging Face Spaces"**
  — false since 2026-09-20; it runs on Azure Container Apps.
- The same page's stats card advertises **94% fidelidad**, which is the **public** instance
  measured on `gpt-4o-mini`. The chat a visitor talks to is the **portfolio** instance:
  routing 1.0, hit@6 0.8, faithfulness 0.7, mean faithfulness 0.9 (2026-09-20, `gpt-5-mini`).
  **Decision: show what the chat actually delivers** — the portfolio numbers — so a visitor
  testing the chat cannot catch the site overstating itself.

## Prerequisites

- ✅ Phase 7 complete: backend live at
  `https://ca-repo-expert.delightfulgrass-0e92a824.swedencentral.azurecontainerapps.io`,
  portfolio instance on Qdrant.
- ✅ Abuse protection live (P8-T0): 10 questions/hour per IP.
- ✅ `CORS_ORIGINS` scoped to `https://jorgepulgar.com`, `https://www.jorgepulgar.com`, and
  `http://localhost:5500` / `http://127.0.0.1:5500` for local development. Verified: an
  allowed origin gets `access-control-allow-origin` echoed back; any other origin gets
  `400`.

## Locked decisions

1. **URL:** `https://jorgepulgar.com/chat.html` (top level, linkable from nav).
2. **Build approach:** vanilla JS, no build step (forced by constraint 1).
3. **Embed mechanism:** inline `<script>` + mount `<div>` on the page. Not an iframe — the
   backend serves no UI, and the page should inherit site styling.
4. **Asset hosting:** served from the site (forced by constraint 2).
5. **Cold start:** fire a `/health` ping on page load so the scale-to-zero container warms
   while the visitor reads the intro and types. No always-on replica — that would burn the
   free grant.
6. **Gating: open + rate-limited.** No email gate — a recruiter who hits a form wall
   leaves. `/ask` is capped at **10 questions per hour per IP**; `/health` is never limited
   so the warm ping stays free. Cloudflare Turnstile only if abuse actually appears.
   (This answers **A8** in `jorge-pulgar-web/.claude/TASKS.md`.)

## Tasks

- [x] **P8-T0** — Abuse protection on the public `/ask` endpoint. **Done 2026-09-21.**
  - Commit: `feat(p8): rate limit the public ask endpoint [P8-T0]`
  - Why: `/ask` is unauthenticated and spends money on every call (three LLM round trips:
    routing, generation, grounding judge). **CORS does not protect it** — CORS is enforced
    by browsers, so a script calling the endpoint directly is unaffected. Before this, the
    endpoint was an open LLM billed to a trial credit.
  - DoD: per-IP sliding window, 10 questions/hour, `429` + `Retry-After` when exceeded,
    rejected *before* any LLM call so a throttled request costs nothing; `/health`
    deliberately exempt; limit configurable via `RATE_LIMIT_PER_HOUR` (0 disables, local
    only). Verified in production: `200, 200, 429` with `Retry-After: 3580` at a temporary
    limit of 2, and `/health` unlimited across 6 pings.
  - Also: Azure budget `repo-expert-guard`, $50/month, alerts at 50% and 80%.
  - Note: the counter is in-process, which is correct at `--max-replicas 1`. If the app is
    ever scaled out, each replica keeps its own counter and the effective limit becomes
    `limit × replicas` — move the state to Redis or the ingress at that point.
- [x] **P8-T1** — `rex-chat.js` + `rex-chat.css` scaffold + standalone demo page.
  **Done 2026-09-21** — `web/rex-chat.{js,css}` + `web/demo.html`. No build step, no
  dependencies, every class `rex-` prefixed, colours via CSS variables the host page can
  override.
- [x] **P8-T2** — `/ask` client + configurable backend URL. **Done 2026-09-21.**
  Base URL comes from `data-api` on the mount div; the file hard-codes nothing. Verified
  against the live endpoint from `http://127.0.0.1:5500`: preflight `200` with
  `access-control-allow-origin` echoed, POST `200`, 6 citations parsed.
  **API is single-turn** — `AskRequest` accepts only `{question}`, so there is no
  conversation history and the UI must not imply follow-ups carry context.
- [x] **P8-T3** — Chat UI: input, answer render, citations as clickable links.
  **Done 2026-09-21.** Inline `[n]` markers become superscript links into `citations[n-1]`;
  a numbered source list shows title + `file_path` + line range; transcript scrollback;
  Spanish copy; `role="log"` + `aria-live` for screen readers.
  **Security:** answers are LLM output, so they are escaped before becoming HTML. Seven
  `node --test` unit tests cover escaping, script-tag injection, a malicious citation URL,
  and unmatched markers (left literal rather than linked somewhere wrong).
- [x] **P8-T4** — Cold-start, error, and discovery UX. **Done 2026-09-21.**
  `/health` warm-ping on load (exempt from the rate limit, so it is free); spinner
  immediately, "despertando el servidor…" after 4s, 120s timeout via `AbortController`;
  distinct messages for network failure, timeout, and **`429`** (reads `Retry-After` and
  tells the visitor when to come back); 3 starter questions, overridable via
  `data-starters`; badges for route, fallback, and an ungrounded answer.
- [x] **P8-T6** — Retrieval quality overhaul. **Done 2026-09-21.**
  - Commit: `feat(p8): multilingual retrieval, weighted fusion and chat memory [P8-T6]`
  - Why: the deployed chat answered badly. "¿Qué proyectos ha construido Jorge?" named
    two projects; "¿Tiene algún proyecto relacionado con ML?" answered with LicitAI (a
    RAG project) rather than the ML ones; follow-ups were impossible.
  - **Root cause: the embedding model was English-only.** `all-MiniLM-L6-v2` cannot
    serve a Spanish question over an English career document. Same index, same fusion,
    only the language changed: the English phrasing returned 6/6 career chunks, the
    Spanish one 6/6 unrelated prompt templates. Now `intfloat/multilingual-e5-small`
    (free-tier permitted, same 384 dims, `query:`/`passage:` prefixes).
  - Also fixed: RRF had degenerated into a fixed 2-per-collection quota (now
    proportional slots weighted by match); 55% of career chunks overflowed the embed
    window (sections now split on sentence boundaries, heading repeated — LicitAI's
    approach); 40% of the docs corpus was task specs and prompt templates (excluded);
    `**/tasks/**` never matched at the repo root because `fnmatch` lets `*` cross `/`.
  - Added conversation memory: `/ask` accepts prior turns, the widget sends the last 5.
  - Eval: routing 1.0, hit@6 0.8 → **1.0** (career 0.6 → **1.0**), faithfulness 0.7 →
    **1.0**. Part of the faithfulness gain is a measurement fix — the judge had been
    retrieving less evidence than the generator used; see the addendum in
    `docs/eval-qdrant-vs-azure.md`.
  - Corpus: 2694 chunks (1691 docs · 947 code · 56 career), `sales-receptivity-cnn` added.
- [x] **P8-T7** — The assistant could not describe itself, and a stale number survived. **Done 2026-09-22.**
  - Why: the first thing a recruiter asks the chat is *"what is this?"*. "¿Qué es Repo
    Expert y qué stack usa?" answered *"no sé — las fuentes no mencionan Repo Expert"*.
  - **Root cause: nothing about repo-expert was indexed.** It was absent from
    `_PORTFOLIO_REPOS` and had no career-doc section. It *looked* indexed because career
    chunks cite the `JorgePulgar/repo-expert` blob URL (the career doc lives in this
    repo), so the citations in other answers pointed at repo-expert while carrying no
    content about it. Fixed by adding the repo to the portfolio instance (excluding
    `docs/phases/**`, `CLAUDE.md`, and the career doc itself, which is already its own
    collection) and adding two career sections plus a "what is this chat" FAQ block.
  - Also fixed: the career doc claimed **4,000** lines for RAG Assistants Platform where
    the site said ~5,000. Counted: 4,973 (3,324 backend + 1,649 frontend), 56 tests.
  - **Ingestion could not remove anything.** Upsert writes the current chunks and leaves
    behind the ones a source stopped producing — and an oversized section's anchors are
    positional (`--p1`, `--p2`), so shortening a section orphans its tail pieces holding
    the superseded text. Added `prune_missing()`: a full ingest is the complete intended
    content, so anything not in the fresh set is deleted. First run removed **118 stale
    docs points and 4 career points** that were still retrievable.
  - Corpus: 2809 chunks (1681 docs · 1062 code · 66 career). Verified in production:
    both questions now answer correctly with citations.
- [ ] **P8-T5** — Page + integration in `jorge-pulgar-web`, verified end to end.
  - Commit: `docs(p8): chat page integration guide [P8-T5]`
  - DoD: `chat.html` live on the site with explainer copy (what it knows, what to ask,
    limits); CSP updated in `.htaccess` **and** `_headers`; `sitemap.xml` + `llms.txt` +
    canonical/OG updated; linked from nav/portfolio; CORS confirmed from the real domain;
    scope guardrail visibly declines off-topic questions; the two stale claims above fixed.

## Explainer copy — what the page must be honest about

The page is a demo of a RAG system, so its own copy is a credibility test. It should state:

- **What it knows:** Jorge's career KB + docs and code from his portfolio repos (3109
  chunks across three Qdrant collections).
- **What it can do:** answer with inline citations pointing at the exact source.
- **Limits, stated plainly:** it only answers about Jorge and his projects (off-topic
  questions are declined by design); answers are grounded in the indexed corpus, so it says
  "no lo sé" rather than inventing; the first request after idle takes a few seconds to
  wake; retrieval on long career entries is imperfect (hit@6 0.8 — the known MiniLM
  256-token truncation).

## Exit criteria

- `https://jorgepulgar.com/chat.html` answers portfolio questions with citations against the
  deployed backend.
- Cold-start and error states handled gracefully; starter questions present.
- Explainer copy states scope and limits honestly.
- CSP, CORS, sitemap, and nav integration all done; master index updated.
