"""Groundedness/faithfulness evaluation via an independent LLM judge.

For each question we run the full agent, then independently retrieve the evidence
and ask a judge model whether every claim in the answer is supported by it. We also
record the agent's own self-grounding flag for comparison.
"""

from __future__ import annotations

import logging

from repo_expert.agent.agent import ask
from repo_expert.agent.llm import chat_json
from repo_expert.config.instance import get_instance_config
from repo_expert.eval.dataset import load_qa
from repo_expert.retrieval.registry import get_retrievers

logger = logging.getLogger(__name__)

_JUDGE_SYSTEM = (
    "You are a strict faithfulness judge. Given a QUESTION, an ANSWER, and EVIDENCE, "
    "decide whether every factual claim in the answer is supported by the evidence. "
    "Reply as JSON {\"faithful\": true|false, \"score\": 0.0-1.0, \"reason\": \"...\"}. "
    "If the answer states it doesn't know, treat it as faithful with score 1.0."
)


def _evidence(route: list[str], retrievers: dict, question: str, top: int) -> str:
    chunks = []
    for src in route or ["kb"]:
        retriever = retrievers.get(src)
        if retriever:
            for i, r in enumerate(retriever(question, top=top), start=1):
                chunks.append(f"[{i}] ({r.kind}) {r.content[:700]}")
    return "\n\n".join(chunks)


def run_groundedness(instance: str | None = None, top: int = 5) -> dict:
    """Run the groundedness eval; return aggregate + per-item judgments."""
    cfg = get_instance_config(instance)
    retrievers = get_retrievers(cfg)
    qa = load_qa(cfg.name)

    items = []
    total_score = 0.0
    faithful_count = self_grounded_count = 0
    for item in qa:
        try:
            result = ask(item.question)
            evidence = _evidence(result.route, retrievers, item.question, top)
            verdict = chat_json(
                _JUDGE_SYSTEM,
                f"QUESTION: {item.question}\n\nANSWER: {result.answer}\n\nEVIDENCE:\n{evidence}",
            )
            score = float(verdict.get("score", 0.0))
            faithful = bool(verdict.get("faithful", False))
            total_score += score
            faithful_count += faithful
            self_grounded_count += result.grounded
            items.append(
                {
                    "id": item.id,
                    "faithful": faithful,
                    "score": round(score, 3),
                    "self_grounded": result.grounded,
                    "fallback_used": result.fallback_used,
                }
            )
        except Exception as exc:  # noqa: BLE001 - one transient failure must not abort the run
            logger.warning("Groundedness eval failed for %s: %s", item.id, exc)
            items.append({"id": item.id, "faithful": False, "score": 0.0, "error": str(exc)})

    n = len(qa)
    return {
        "n": n,
        "faithfulness_rate": round(faithful_count / n, 3),
        "mean_faithfulness_score": round(total_score / n, 3),
        "self_grounded_rate": round(self_grounded_count / n, 3),
        "items": items,
    }
