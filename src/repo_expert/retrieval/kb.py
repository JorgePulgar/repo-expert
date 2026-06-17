"""Knowledge base retriever: vector search over the Qdrant collections.

Queries each of the instance's collections (docs, code, and career when present)
with server-side embedding (``models.Document``) and fuses the per-collection
ranked lists into the unified ``RetrievalResult`` shape. We use Reciprocal Rank
Fusion rather than a raw-score merge: code chunks score systematically lower than
prose for a natural-language query, so a global cosine sort starves code results.
RRF fuses by rank, which is scale-free, so each collection gets fair representation.
Same signature as before, so the registry, agent, and API are unchanged. The live
issues retriever is untouched.
"""

from __future__ import annotations

import logging

from repo_expert.clients import get_qdrant_client
from repo_expert.config.instance import InstanceConfig, get_instance_config
from repo_expert.ingestion.qdrant_collections import collection_names
from repo_expert.ingestion.qdrant_embed import as_document
from repo_expert.retrieval.models import Citation, RetrievalResult

logger = logging.getLogger(__name__)

# Reciprocal Rank Fusion constant (standard default); larger = flatter rank weighting.
_RRF_K = 60


def _to_result(payload: dict, score: float | None) -> RetrievalResult:
    """Build a unified result from a Qdrant point payload + score."""
    return RetrievalResult(
        source="kb",
        kind=payload.get("source_kind", "docs"),
        content=payload.get("content", ""),
        score=score,
        citation=Citation(
            title=payload.get("title", ""),
            url=payload.get("url", ""),
            file_path=payload.get("file_path"),
            section_path=payload.get("section_path") or [],
            start_line=payload.get("start_line"),
            end_line=payload.get("end_line"),
        ),
    )


def retrieve_kb(
    query: str, cfg: InstanceConfig | None = None, top: int = 10
) -> list[RetrievalResult]:
    """Retrieve from the Qdrant collections and return unified results with citations."""
    cfg = cfg or get_instance_config()
    client = get_qdrant_client()
    embedded = as_document(query)
    fused: list[tuple[float, RetrievalResult]] = []
    for name in collection_names(cfg):
        hits = client.query_points(
            collection_name=name, query=embedded, limit=top, with_payload=True
        ).points
        for rank, h in enumerate(hits, start=1):
            rrf = 1.0 / (_RRF_K + rank)
            fused.append((rrf, _to_result(h.payload or {}, h.score)))
    # Stable sort keeps insertion order among ties, so collections interleave by rank.
    fused.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in fused[:top]]
