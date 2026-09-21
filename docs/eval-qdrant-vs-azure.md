# Eval: Qdrant stack vs. Azure baseline (P7-T6)

Same curated Q/A sets, same agent (LangGraph router → retrieve → generate →
grounding). Only the retrieval backend and models changed:

| | Azure baseline (2026-06-15) | Qdrant stack (2026-06-17) |
| --- | --- | --- |
| Vector store | Azure AI Search (Foundry IQ agentic retrieval) | Qdrant Cloud (vector + RRF fusion) |
| Embeddings | text-embedding-3-large (3072-dim) | all-MiniLM-L6-v2 (384-dim), server-side |
| Chat LLM | gpt-4o | gpt-4o-mini |
| Recurring cost | ~$75+/mo | ~$0–1/mo |

## Public (fastapi/fastapi, n=16)

| Metric | Azure | Qdrant | Δ |
| --- | --- | --- | --- |
| Routing accuracy | 1.0 | 1.0 | — |
| Relevance hit@6 | 0.875 | **1.0** | ▲ +0.125 |
| ↳ code | 0.6 | **1.0** | ▲ +0.4 |
| ↳ docs / issue / mixed | 1.0 / 1.0 / 1.0 | 1.0 / 1.0 / 1.0 | — |
| Faithfulness rate (judge) | 0.75 | **0.938** | ▲ +0.188 |
| Mean faithfulness | 0.887 | **0.938** | ▲ +0.051 |
| Agent self-grounded rate | 0.875 | **1.0** | ▲ +0.125 |

**Read:** public improved across the board despite the cheaper embed model. The big
move is **code relevance 0.6 → 1.0**: replacing the managed reranker's single global
ranking with **Reciprocal Rank Fusion across the docs/code collections** stops prose
from starving code hits (code chunks score lower than NL queries on cosine). Cheaper
gpt-4o-mini did not regress groundedness here.

## Portfolio (Jorge's repos + Career KB, n=10)

| Metric | Azure | Qdrant | Δ |
| --- | --- | --- | --- |
| Routing accuracy | 1.0 | 1.0 | — |
| Relevance hit@6 | 1.0 | **0.8** | ▼ −0.2 |
| ↳ career | 1.0 | **0.6** | ▼ −0.4 |
| ↳ mixed | 1.0 | 1.0 | — |
| Faithfulness rate (judge) | 1.0 | 1.0 | — |
| Mean faithfulness | 1.0 | 1.0 | — |
| Agent self-grounded rate | 0.0 | **0.9** | ▲ +0.9 |

**Read:** the only real regression is **career retrieval 1.0 → 0.6** (2 of ~5 career
questions miss). This is the expected cost of the T2 gate fallback: MiniLM's lower
capacity (384-dim) plus its **~256-token input window** truncates the longer career
entries, so some answers fall outside hit@6. Groundedness is unaffected (1.0). The
jump in self-grounded rate (0.0 → 0.9) reflects gpt-4o-mini emitting a usable grounding
verdict where the Azure run had not.

## Conclusion

The migration is a net win for the headline (public) instance and cuts cost ~75×. The
portfolio career regression is contained (groundedness intact, only recall on long
career entries). **Mitigations if it matters later:** chunk the career doc smaller to
fit MiniLM's 256-token window; raise `top` for the career collection; or adopt a larger
free embed model if Qdrant enables one on the free tier (the original mxbai choice).

---

## Addendum — 2026-09-20: model change gpt-4o-mini → gpt-5-mini (P7-T8)

The Azure subscription behind the original runs lapsed and its Foundry resource was
deleted, so the chat stack was rebuilt on a new subscription. `gpt-4o-mini` can no longer
be deployed at all — Azure rejects it with *"has been deprecated since 03/31/2026"* — so
routing, generation, and the grounding judge now run on **`gpt-5-mini`**.

Portfolio instance, same 10-question set, same Qdrant collections (re-ingested: 2146 docs
+ 941 code + 22 career chunks):

| Metric | gpt-4o-mini (2026-06-17) | gpt-5-mini (2026-09-20) | Δ |
| --- | --- | --- | --- |
| Routing accuracy | 1.0 | 1.0 | — |
| Relevance hit@6 | 0.8 | 0.8 | — |
| ↳ career | 0.6 | 0.6 | — |
| ↳ mixed | 1.0 | 1.0 | — |
| Faithfulness rate (judge) | 1.0 | **0.7** | ▼ −0.3 |
| Mean faithfulness | 1.0 | **0.9** | ▼ −0.1 |
| Agent self-grounded rate | 0.9 | **1.0** | ▲ +0.1 |

**Read:** retrieval is untouched, as expected — embeddings, chunking, and collections did
not change, only the chat model. The groundedness drop is mostly **judge strictness, not
worse answers**: the judge is itself `gpt-5-mini`, and two of the three "unfaithful"
verdicts carry scores of **0.85** (`career-datarmony`) and **0.8**
(`repo-invoice-analyzer`) — high scores paired with `faithful: false`, which `gpt-4o-mini`
did not do. Only `repo-clarity-bank` (**0.35**) is a genuine failure, and it is the same
long-career-entry weakness already documented above: MiniLM's 256-token window truncates
that content, so the answer outruns its evidence.

**Caveat:** generator and judge changed together, so this comparison cannot fully separate
"stricter judge" from "less faithful generator". Pinning the judge to a fixed model while
varying the generator would separate them; not done here because `gpt-4o-mini` is no longer
deployable, so there is no way to reproduce the old baseline.

**Note on determinism:** `gpt-5-mini` rejects any `temperature` but its default
(`"Only the default (1) value is supported"`), so the previous `temperature=0.0` pinning is
gone from `agent/llm.py` and `retrieval/issues.py`. Run-to-run variance is therefore higher
than in the gpt-4o-mini runs.

---

## Addendum — 2026-09-21: retrieval overhaul (multilingual embeddings, fusion, memory)

Prompted by the chat answering badly in production: "¿Qué proyectos ha construido
Jorge?" named two projects, "¿Tiene algún proyecto relacionado con ML?" answered
with LicitAI (a RAG project) instead of the ML ones, and follow-ups were impossible.

Portfolio instance, same 10-question set:

| Metric | 2026-09-20 | 2026-09-21 | Δ |
| --- | --- | --- | --- |
| Routing accuracy | 1.0 | 1.0 | — |
| Relevance hit@6 | 0.8 | **1.0** | ▲ +0.2 |
| ↳ career | 0.6 | **1.0** | ▲ +0.4 |
| Faithfulness rate (judge) | 0.7 | **1.0** | ▲ +0.3 |
| Mean faithfulness | 0.9 | **1.0** | ▲ +0.1 |

### What changed, and which change did the work

1. **The embedding model was English-only.** `all-MiniLM-L6-v2` cannot serve a
   Spanish question over an English career document. Measured on the same index,
   same fusion — only the language of the question changed:

   * `"What projects has Jorge built?"` → 6/6 career chunks (correct)
   * `"¿Qué proyectos ha construido Jorge?"` → 6/6 unrelated Spanish prompt templates

   Replaced with `intfloat/multilingual-e5-small`: multilingual, free-tier
   permitted, same 384 dimensions, `query:`/`passage:` prefixes. **This was the
   root cause**; the career regression documented above (1.0 → 0.6) was never
   really about MiniLM's token window — it was about its language.

2. **Fusion was a quota, not a ranking.** Plain RRF scores by rank *within* a
   collection, so every collection's #1 tied and the merged list was a round-robin:
   with `top=6` and three collections, exactly 2 from each, whatever was asked.
   Four of six slots went to repo code and docs on career questions. Replaced with
   proportional slot allocation weighted by how well each collection matches,
   measured against the spread observed for that query.

3. **Long sections were truncated at embed time.** 12 of 22 career chunks (55%)
   exceeded the model's input window, the largest at ~1200 tokens, so their tails
   were unsearchable. The markdown chunker now splits sections on sentence
   boundaries, repeating the heading on each piece (the approach used in LicitAI).
   Career: 22 → 56 chunks, longest 4952 → 899 chars, none over the cap.

4. **40% of the docs corpus was internal noise.** 1003 task-spec chunks and 161
   prompt-template chunks, which is where "Firma", "Voz (innegociable)" and a
   *fictional* job posting ("Machine Learning Engineer — NeuralForge") were coming
   from. Now excluded; docs 2885 → 1691, total corpus 2694.

5. **Query rewrite, then gated.** Expanding every question made things worse — the
   expansion read like a keyword list and matched tables of contents. It now fires
   only for follow-ups, very short questions and unfamiliar acronyms, and must
   return prose.

6. **Conversation memory.** `/ask` accepts prior turns, replayed as chat turns.
   "Explícame más sobre el primero" now resolves against the previous answer.

### Caveat on the faithfulness number

Part of that 0.7 → 1.0 is a **measurement fix, not a model improvement**. The judge
retrieves its own evidence; it was doing so at `top=5` with each chunk cropped to
700 characters, while the generator had been raised to 12 chunks of 2400. Answers
were being marked unsupported because the text supporting them had been cropped out
of the judge's view — an intermediate run read **0.1** for exactly this reason. The
judge now sees the same breadth the generator did.

The retrieval numbers (routing, hit@6) are unaffected by that and improved on their
own. Read the faithfulness figure as "no longer measured unfairly" rather than as a
threefold quality gain.
