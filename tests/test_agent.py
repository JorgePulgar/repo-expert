"""Offline unit tests for agent nodes (LLM and config mocked)."""

from repo_expert.agent import graph
from repo_expert.agent.graph import (
    MAX_ATTEMPTS,
    _after_grounding,
    fallback_node,
    generate_node,
    grounding_node,
    router_node,
)
from repo_expert.retrieval.models import Citation, RetrievalResult


def _result(kind: str = "code") -> RetrievalResult:
    return RetrievalResult(
        source="kb",
        kind=kind,
        content="def f(): ...",
        citation=Citation(title="function f", url="http://x", file_path="a.py", start_line=1),
    )


# --- router --------------------------------------------------------------------

def test_router_single_source_skips_llm(monkeypatch) -> None:
    monkeypatch.setattr(graph, "available_sources", lambda cfg: ["kb"])
    called = False

    def _fail(*a, **k):
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(graph, "chat_json", _fail)
    assert router_node({"question": "anything"}) == {"route": ["kb"]}
    assert not called


def test_router_filters_invalid_route(monkeypatch) -> None:
    monkeypatch.setattr(graph, "available_sources", lambda cfg: ["kb", "issues"])
    monkeypatch.setattr(graph, "chat_json", lambda *a, **k: {"route": ["issues", "bogus"]})
    assert router_node({"question": "is this a known bug?"}) == {"route": ["issues"]}


def test_router_defaults_to_kb_when_empty(monkeypatch) -> None:
    monkeypatch.setattr(graph, "available_sources", lambda cfg: ["kb", "issues"])
    monkeypatch.setattr(graph, "chat_json", lambda *a, **k: {"route": []})
    assert router_node({"question": "?"}) == {"route": ["kb"]}


# --- grounding -----------------------------------------------------------------

def test_grounding_empty_results_is_false() -> None:
    assert grounding_node({"draft": "x", "results": []}) == {"grounded": False}


def test_grounding_passes_through_llm_verdict(monkeypatch) -> None:
    monkeypatch.setattr(graph, "chat_json", lambda *a, **k: {"grounded": True})
    assert grounding_node({"draft": "ans", "results": [_result()]}) == {"grounded": True}


def test_grounding_flags_unsupported(monkeypatch) -> None:
    monkeypatch.setattr(graph, "chat_json", lambda *a, **k: {"grounded": False})
    assert grounding_node({"draft": "wrong", "results": [_result()]}) == {"grounded": False}


# --- generate / fallback / edges ----------------------------------------------

def test_generate_no_results_says_dont_know() -> None:
    out = generate_node({"question": "q", "results": []})
    assert out["citations"] == [] and "don't know" in out["answer"].lower()


def test_fallback_widens_route(monkeypatch) -> None:
    monkeypatch.setattr(graph, "available_sources", lambda cfg: ["kb", "issues"])
    out = fallback_node({"route": ["kb"], "attempts": 0})
    assert out["route"] == ["kb", "issues"] and out["attempts"] == 1 and out["fallback_used"]


def test_after_grounding_ends_when_grounded() -> None:
    assert _after_grounding({"grounded": True, "attempts": 0}) == "end"


def test_after_grounding_revises_then_stops_at_max() -> None:
    assert _after_grounding({"grounded": False, "attempts": 0}) == "revise"
    assert _after_grounding({"grounded": False, "attempts": MAX_ATTEMPTS}) == "end"
