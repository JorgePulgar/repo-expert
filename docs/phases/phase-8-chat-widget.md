# Phase 8 — Chat widget for the Hostinger website

**Branch:** `feature/phase-8-chat-widget` · **Status:** ⬜ not started

## Context

A chat box embedded in Jorge's personal-brand site (hosted on **Hostinger shared
hosting**) that answers questions about Jorge and his projects via the **portfolio
instance**. The widget is pure frontend; it calls the deployed backend's `/ask` (HF
Spaces, from Phase 7) over HTTPS and renders the answer with citations.

**Hosting reality:** Hostinger shared hosting serves only static/PHP — it **cannot** run
the Python backend. So this phase builds an **embeddable widget** (HTML/CSS/JS bundle) that
drops into a Hostinger page and talks to the remote backend. No backend runs on Hostinger.

## Why this phase exists

The recruiter/visitor demo: a chat box beats curl, and it's the actual product feature for
the personal brand. Distinct from a full SPA — it must embed cleanly into an existing site.

## Prerequisites

- Phase 7 complete: backend deployed to a free host with a public `/ask`, **CORS allowing
  the Hostinger domain**, portfolio instance on Qdrant.

## Open decisions (resolve before/within the phase)

1. **Build approach:** single bundled vanilla-JS widget (simplest to drop into Hostinger,
   no framework) vs a small React/Preact widget compiled to a static bundle (richer, **pnpm
   only** per root CLAUDE.md). Recommendation: vanilla or Preact → one `<script>` + `<div>`
   embed.
2. **Embed mechanism:** inline `<script>` + mount `<div>` on a Hostinger page, vs an
   `<iframe>` hosted on the Space. Inline script integrates with site styling; iframe is
   more isolated.
3. **Widget asset hosting:** serve the built JS/CSS from Hostinger itself (upload static
   files) vs from the Space/CDN. Hostinger-served keeps everything on the domain.

## Tasks

- [ ] **P8-T1** — Scaffold the widget (chosen approach), pnpm-managed if Node is used.
  - Commit: `chore(p8): scaffold chat widget [P8-T1]`
  - DoD: `pnpm dev` (or a static `index.html`) renders an empty chat shell; build produces
    an embeddable bundle.
- [ ] **P8-T2** — Typed `/ask` client + config for the backend base URL.
  - Commit: `feat(p8): ask client with configurable backend url [P8-T2]`
  - DoD: posts `{question}` to the deployed `/ask`; backend URL is configurable (not
    hard-coded); handles JSON `AskResponse` (answer, citations, route, grounded).
- [ ] **P8-T3** — Chat UI: input, answer render, citations as clickable links.
  - Commit: `feat(p8): chat ui with citations [P8-T3]`
  - DoD: ask → answer with clickable file/line (GitHub) + doc/url citations; conversation
    scrollback.
- [ ] **P8-T4** — Cold-start + error UX.
  - Commit: `feat(p8): loading, waking-up, and error states [P8-T4]`
  - DoD: shows a "waking up, one moment" state during free-host cold start (~30–60s),
    spinner on normal latency, friendly error on failure/timeout; optional route badge.
- [ ] **P8-T5** — Embed into Hostinger + verify end-to-end.
  - Commit: `docs(p8): hostinger embed guide [P8-T5]`
  - DoD: documented embed snippet; widget live on the Hostinger site talking to the deployed
    backend; CORS confirmed from the real domain; portfolio scope guardrail visibly declines
    off-topic questions.

## Exit criteria

- Working chat widget embedded on the Hostinger site, answering portfolio questions with
  citations against the deployed backend.
- Cold-start and error states handled gracefully.
- Embed instructions documented; master index updated; noted in README.
