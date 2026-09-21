"""Knowledge base retriever: vector search over the Qdrant collections.

Queries each of the instance's collections (docs, code, and career when present)
with server-side embedding (``models.Document``) and fuses the per-collection
ranked lists into the unified ``RetrievalResult`` shape.

Fusion is rank-based rather than a raw-score merge, because code chunks score
systematically lower than prose for a natural-language query and a global cosine
sort starves them. Plain RRF, however, over-corrected into a fixed quota (see the
comment on ``_WEIGHT_GAMMA``), so ranks are weighted by how well each collection
matches and weak hits are dropped.

The query is expanded before embedding (``rewrite.py``). Same signature plus
optional arguments, so the registry, agent, and API keep working. The live issues
retriever is untouched.
"""

from __future__ import annotations

import logging

from qdrant_client import models

from repo_expert.clients import get_qdrant_client
from repo_expert.config.instance import InstanceConfig, get_instance_config
from repo_expert.ingestion.qdrant_collections import collection_names
from repo_expert.ingestion.qdrant_embed import as_query
from repo_expert.retrieval.models import Citation, RetrievalResult
from repo_expert.retrieval.rewrite import rewrite_query

logger = logging.getLogger(__name__)

# Reciprocal Rank Fusion constant (standard default); larger = flatter rank weighting.
_RRF_K = 60

# Plain RRF scores a hit by its rank *within its own collection*, so every
# collection's #1 ties, every #2 ties, and the merged list is a round-robin:
# docs#1, code#1, career#1, docs#2, ... With top=6 and three collections that is a
# hard quota of 2 per collection, whatever the question. A career question then got
# four slots of repo code and docs it did not ask for.
#
# RRF degenerates this way because it is designed for ranked lists of the *same*
# items; ours are disjoint. Two corrections, both driven by the similarity score
# (comparable across collections here — one embedding model, one metric):
#
#   * weight each collection by how well its best hit matches, so a collection that
#     actually answers the question can take several consecutive slots;
#   * drop hits far below the best match, so a collection with nothing relevant
#     contributes nothing rather than filling its quota.
_WEIGHT_GAMMA = 2.0       # how sharply a weak collection is demoted
_MIN_RELATIVE = 0.05      # drop hits sitting at the bottom of the query's range
_MIN_SPREAD = 0.01        # below this, treat the collections as equally relevant
_SOFTEN = 0.02            # keeps the weakest hit off exactly zero (see relative())

# How many chunks either side of a hit to merge in as extra context. The markdown
# chunker splits long sections, so an answer can straddle a boundary; 1 is enough to
# rejoin it without flooding the prompt.
_NEIGHBOUR_RADIUS = 1


def _to_result(payload: dict, score: float | None) -> RetrievalResult:
    """Build a unified result from a Qdrant point payload + score."""
    return RetrievalResult(
        source="kb",
        kind=payload.get("source_kind", "docs"),
        content=payload.get("content", ""),
        score=score,
        seq=payload.get("seq"),
        repo_slug=payload.get("repo_slug"),
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
    query: str,
    cfg: InstanceConfig | None = None,
    top: int = 10,
    history: list[tuple[str, str]] | None = None,
    expand: bool = True,
    neighbours: bool = True,
) -> list[RetrievalResult]:
    """Retrieve from the Qdrant collections and return unified results with citations.

    ``expand`` rewrites the question into a richer, self-contained search query
    (acronyms spelled out, follow-ups resolved against ``history``). Pass
    ``expand=False`` to search with the literal text, e.g. when measuring raw
    retrieval in tests.
    """
    cfg = cfg or get_instance_config()
    client = get_qdrant_client()
    search_text = rewrite_query(query, history) if expand else query
    embedded = as_query(search_text)

    per_collection: list[list[tuple[int, float, RetrievalResult]]] = []
    for name in collection_names(cfg):
        hits = client.query_points(
            collection_name=name, query=embedded, limit=top, with_payload=True
        ).points
        per_collection.append(
            [
                (rank, float(h.score or 0.0), _to_result(h.payload or {}, h.score))
                for rank, h in enumerate(hits, start=1)
            ]
        )

    all_scores = [score for group in per_collection for _, score, _ in group]
    if not all_scores:
        return []
    best_overall = max(all_scores)
    if best_overall <= 0:
        return []

    # Similarities do not start at zero: with e5, unrelated text still scores ~0.75
    # and everything returned lands in a narrow 0.78-0.88 band, so a ratio of raw
    # scores says almost nothing ("0.784 / 0.824" looks like a tie). Measuring each
    # collection against the *spread actually observed for this query* restores the
    # contrast, and adapts itself to whatever model is configured instead of baking
    # in a per-model constant.
    baseline = min(all_scores)
    spread = best_overall - baseline

    def relative(score: float) -> float:
        """Where a score sits in this query's range: ~0 = worst seen, 1 = best.

        ``_SOFTEN`` keeps the weakest hit from landing on exactly zero. Without it
        the worst result in the pool is always discarded, however close it is —
        with two hits at 0.90 and 0.80 the second scores 0 and disappears, even
        though it is a perfectly good runner-up.
        """
        if spread <= _MIN_SPREAD:
            return 1.0  # every collection matched equally well; share the slots
        return (max(score - baseline, 0.0) + _SOFTEN) / (spread + _SOFTEN)

    # Keep each collection's own ranking, but drop hits far below the best match
    # anywhere: a runner-up in a collection that cannot answer the question is
    # noise, not a second opinion.
    candidates: list[list[tuple[float, RetrievalResult]]] = [
        [(score, result) for _, score, result in group if relative(score) >= _MIN_RELATIVE]
        for group in per_collection
    ]

    # Share the slots out in proportion to how well each collection answers the
    # question, instead of giving every collection the same number. A multiplier on
    # the rank score cannot do this: scaling a whole collection down still leaves
    # its hits ordered behind every hit of the leader, so the leader takes the lot.
    weights = [
        relative(max(score for score, _ in group)) ** _WEIGHT_GAMMA if group else 0.0
        for group in candidates
    ]
    selected = [r for _, r in _take_proportional(candidates, weights, top)]
    return _with_neighbours(client, cfg, selected) if neighbours else selected


def _take_proportional(
    groups: list[list[tuple[float, RetrievalResult]]],
    weights: list[float],
    total: int,
) -> list[tuple[float, RetrievalResult]]:
    """Pick ``total`` items across ``groups``, sharing slots by ``weights``.

    Uses largest-remainder allocation, then hands any slots a short group cannot
    fill back to the others, so a strong collection can take the whole list when
    the rest have nothing relevant. The result is ordered by similarity so the
    strongest evidence is cited first.
    """
    weight_sum = sum(weights)
    if weight_sum <= 0:
        return []

    exact = [total * w / weight_sum for w in weights]
    slots = [min(int(x), len(g)) for x, g in zip(exact, groups)]

    # Largest remainder first, then keep topping up while anything is unfilled.
    for _ in range(total):
        if sum(slots) >= total:
            break
        candidates = [
            i for i, g in enumerate(groups) if slots[i] < len(g) and weights[i] > 0
        ]
        if not candidates:
            break
        best = max(candidates, key=lambda i: (exact[i] - slots[i], weights[i]))
        slots[best] += 1

    picked: list[tuple[float, RetrievalResult]] = []
    for group, take in zip(groups, slots):
        picked.extend(group[:take])
    picked.sort(key=lambda x: x[0], reverse=True)
    return picked[:total]


def _collection_for(cfg: InstanceConfig, kind: str) -> str | None:
    """Which collection a result of this ``kind`` came from."""
    if kind == "code":
        return cfg.code_index
    if kind == "docs":
        return cfg.docs_index
    return cfg.source3_index  # career


def _with_neighbours(
    client, cfg: InstanceConfig, results: list[RetrievalResult]
) -> list[RetrievalResult]:
    """Widen each hit with the chunks either side of it in its source file.

    A section split across chunks can leave the answer straddling a boundary: the
    matching chunk names the project, the next one lists what it does. The
    neighbours are merged into the hit's own text rather than added as extra
    sources, so the ``[n]`` numbering the model cites stays aligned with the
    citation list and no duplicate citations appear.

    Best-effort: any failure returns the results untouched.
    """
    if _NEIGHBOUR_RADIUS < 1:
        return results

    # Group the lookups: collection -> file_path -> wanted seq numbers.
    wanted: dict[str, dict[str, set[int]]] = {}
    for r in results:
        collection = _collection_for(cfg, r.kind)
        path = r.citation.file_path
        # Code chunks carry no seq (they are whole symbols, not split prose).
        if not collection or not path or r.seq is None:
            continue
        for delta in range(1, _NEIGHBOUR_RADIUS + 1):
            for neighbour_seq in (r.seq - delta, r.seq + delta):
                if neighbour_seq >= 0:
                    wanted.setdefault(collection, {}).setdefault(path, set()).add(neighbour_seq)
    if not wanted:
        return results

    found: dict[tuple[str, int], str] = {}
    try:
        for collection, paths in wanted.items():
            for path, seqs in paths.items():
                points, _ = client.scroll(
                    collection_name=collection,
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="file_path", match=models.MatchValue(value=path)
                            ),
                            models.FieldCondition(
                                key="seq", match=models.MatchAny(any=sorted(seqs))
                            ),
                        ]
                    ),
                    limit=len(seqs) * 2,
                    with_payload=True,
                )
                for p in points:
                    payload = p.payload or {}
                    if payload.get("seq") is not None:
                        found[(path, int(payload["seq"]))] = payload.get("content", "")
    except Exception as exc:  # noqa: BLE001 - extra context is a bonus, not a requirement
        logger.warning("Neighbour expansion failed (%s); using the hits as-is", exc)
        return results

    widened: list[RetrievalResult] = []
    for r in results:
        path = r.citation.file_path
        if not path or r.seq is None:
            widened.append(r)
            continue
        before = [found.get((path, r.seq - d), "") for d in range(_NEIGHBOUR_RADIUS, 0, -1)]
        after = [found.get((path, r.seq + d), "") for d in range(1, _NEIGHBOUR_RADIUS + 1)]
        parts = [p for p in (*before, r.content, *after) if p]
        if len(parts) > 1:
            r = r.model_copy(update={"content": "\n\n".join(parts)})
        widened.append(r)
    return widened
