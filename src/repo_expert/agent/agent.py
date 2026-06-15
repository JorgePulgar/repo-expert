"""Public agent entrypoint: ``ask`` and graph export."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from repo_expert.agent.graph import build_graph
from repo_expert.retrieval.models import Citation


class AnswerResult(BaseModel):
    """Structured agent answer."""

    answer: str
    citations: list[Citation]
    route: list[str]
    grounded: bool
    fallback_used: bool


@lru_cache
def _graph():
    return build_graph()


def ask(question: str) -> AnswerResult:
    """Answer a question about the active instance's repo, with citations."""
    out = _graph().invoke({"question": question, "attempts": 0})
    return AnswerResult(
        answer=out.get("answer", ""),
        citations=out.get("citations", []),
        route=out.get("route", []),
        grounded=out.get("grounded", False),
        fallback_used=out.get("fallback_used", False),
    )


def export_graph(path: str | Path = "docs/agent-graph.mmd") -> Path:
    """Write the compiled graph as a Mermaid diagram for the docs."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(build_graph().get_graph().draw_mermaid(), encoding="utf-8")
    return dest
