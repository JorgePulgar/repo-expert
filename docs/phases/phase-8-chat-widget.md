# Phase 8 — Chat page for the personal site (`/chat.html`)

**Branch:** `feature/phase-8-chat-widget` · **Status:** ⬜ not started

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

## Tasks

- [ ] **P8-T1** — `rex-chat.js` + `rex-chat.css` scaffold + standalone demo page.
  - Commit: `chore(p8): scaffold vanilla chat client [P8-T1]`
  - DoD: opening the demo page renders an empty chat shell (messages area, input, send);
    no build step; all classes `rex-` prefixed.
- [ ] **P8-T2** — `/ask` client + configurable backend URL.
  - Commit: `feat(p8): ask client with configurable backend url [P8-T2]`
  - DoD: posts `{question}` to `/ask`; base URL configurable via a data attribute on the
    mount div (never hard-coded); parses `AskResponse` (answer, citations, route, grounded).
- [ ] **P8-T3** — Chat UI: input, answer render, citations as clickable links.
  - Commit: `feat(p8): chat ui with citations [P8-T3]`
  - DoD: ask → answer with clickable file/line (GitHub) and doc/url citations; conversation
    scrollback; Spanish UI copy.
- [ ] **P8-T4** — Cold-start, error, and discovery UX.
  - Commit: `feat(p8): loading, waking-up, and error states [P8-T4]`
  - DoD: `/health` warm-ping on load; "despertando el servidor…" state on cold start;
    spinner on normal latency; friendly error on failure/timeout; **3 suggested starter
    questions** so visitors know what the chat knows; optional route badge.
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
