"""Retrieval-relevance evaluation: routing accuracy + hit@k.

For each question we measure two things independently:
- routing accuracy: does the router pick (at least one of) the expected source(s)?
- retrieval relevance: does a top-k result from the expected source match the
  expected citation (``must_include`` substring) and kind?
"""

from __future__ import annotations

from repo_expert.agent.graph import router_node
from repo_expert.config.instance import get_instance_config
from repo_expert.eval.dataset import QAItem, load_qa
from repo_expert.retrieval.models import RetrievalResult
from repo_expert.retrieval.registry import get_retrievers


def _citation_text(r: RetrievalResult) -> str:
    c = r.citation
    return " ".join(filter(None, [c.title, c.url, c.file_path, *c.section_path])).lower()


def _is_relevant(item: QAItem, results: list[RetrievalResult]) -> bool:
    for r in results:
        if item.expected_kind and r.kind != item.expected_kind:
            continue
        text = _citation_text(r)
        if not item.must_include or any(tok.lower() in text for tok in item.must_include):
            return True
    return False


def run_relevance(instance: str | None = None, top: int = 6) -> dict:
    """Run the relevance eval; return aggregate + per-item results."""
    cfg = get_instance_config(instance)
    retrievers = get_retrievers(cfg)
    qa = load_qa(cfg.name)

    items = []
    routing_hits = relevance_hits = 0
    for item in qa:
        predicted = router_node({"question": item.question}).get("route", [])
        routed_ok = bool(set(predicted) & set(item.expected_sources))

        results: list[RetrievalResult] = []
        for src in item.expected_sources:
            retriever = retrievers.get(src)
            if retriever:
                results.extend(retriever(item.question, top=top))
        relevant = _is_relevant(item, results)

        routing_hits += routed_ok
        relevance_hits += relevant
        items.append(
            {
                "id": item.id,
                "expected_sources": item.expected_sources,
                "predicted_route": predicted,
                "routing_ok": routed_ok,
                "relevant": relevant,
            }
        )

    n = len(qa)
    by_kind: dict[str, dict[str, int]] = {}
    for item, rec in zip(qa, items, strict=True):
        k = item.expected_kind or "mixed"
        bucket = by_kind.setdefault(k, {"hits": 0, "total": 0})
        bucket["total"] += 1
        bucket["hits"] += int(rec["relevant"])
    per_kind = {
        k: round(v["hits"] / v["total"], 3) for k, v in sorted(by_kind.items())
    }
    return {
        "n": n,
        "routing_accuracy": round(routing_hits / n, 3),
        "relevance_hit_at_k": round(relevance_hits / n, 3),
        "relevance_by_kind": per_kind,
        "top_k": top,
        "items": items,
    }
