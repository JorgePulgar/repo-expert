"""Public agent entrypoint: ``ask`` and graph export."""

from __future__ import annotations

from collections.abc import Iterator
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


def ask(
    question: str, history: list[tuple[str, str]] | None = None
) -> AnswerResult:
    """Answer a question about the active instance's repo, with citations.

    ``history`` is the prior ``(question, answer)`` turns of the same conversation,
    oldest first. It lets the agent resolve follow-ups that are not self-contained
    and keeps the service stateless: the client owns the conversation.
    """
    out = _graph().invoke(_inputs(question, history))
    return _result(out)


# What the agent does next once a node finishes; the widget shows it as a status line.
_NEXT_STAGE = {"retrieve": "generate", "generate": "verify", "fallback": "widen"}


def stream_ask(
    question: str, history: list[tuple[str, str]] | None = None
) -> Iterator[dict]:
    """Run the same graph as ``ask``, yielding events as it goes.

    Events, in order: ``stage`` (what the agent is doing now), ``draft`` (the
    citations a draft will use, before its text), ``delta`` (answer text as it is
    written), and last ``done`` (the full ``AnswerResult``, which is authoritative:
    the client should render it over whatever it assembled from the deltas). A
    widened retry emits ``stage: widen`` and a second ``draft``, which replaces the
    first; in a single-source instance that never happens.
    """
    state: dict = _inputs(question, history)
    yield {"event": "stage", "stage": "retrieve"}
    for mode, chunk in _graph().stream(state, stream_mode=["custom", "updates"]):
        if mode == "custom":
            yield chunk
            continue
        for node, update in chunk.items():
            state.update(update or {})
            stage = _NEXT_STAGE.get(node)
            if stage:
                yield {"event": "stage", "stage": stage}
    yield {"event": "done", **_result(state).model_dump(mode="json")}


def _inputs(question: str, history: list[tuple[str, str]] | None) -> dict:
    return {"question": question, "history": list(history or []), "attempts": 0}


def _result(out: dict) -> AnswerResult:
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
