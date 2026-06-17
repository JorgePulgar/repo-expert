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
