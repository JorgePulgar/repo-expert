"""Offline unit tests for agent nodes (LLM and config mocked)."""

from types import SimpleNamespace

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


def test_grounding_uses_configured_effort(monkeypatch) -> None:
    seen = {}

    def _judge(*a, **k):
        seen.update(k)
        return {"grounded": True}

    monkeypatch.setattr(graph, "chat_json", _judge)
    monkeypatch.setattr(
        graph, "get_settings", lambda: SimpleNamespace(grounding_reasoning_effort="low")
    )
    grounding_node({"draft": "ans", "results": [_result()]})
    assert seen["reasoning_effort"] == "low"


def test_grounding_empty_effort_means_deployment_default(monkeypatch) -> None:
    seen = {}

    def _judge(*a, **k):
        seen.update(k)
        return {"grounded": True}

    monkeypatch.setattr(graph, "chat_json", _judge)
    monkeypatch.setattr(
        graph, "get_settings", lambda: SimpleNamespace(grounding_reasoning_effort="")
    )
    grounding_node({"draft": "ans", "results": [_result()]})
    assert seen["reasoning_effort"] is None


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


def test_after_grounding_revises_when_route_can_widen(monkeypatch) -> None:
    monkeypatch.setattr(graph, "available_sources", lambda cfg: ["kb", "issues"])
    state = {"grounded": False, "attempts": 0, "route": ["kb"]}
    assert _after_grounding(state) == "revise"
    assert _after_grounding({**state, "attempts": MAX_ATTEMPTS}) == "end"


def test_after_grounding_ends_when_nothing_left_to_widen(monkeypatch) -> None:
    # Single-source instance (portfolio): a revision would only re-roll the draft.
    monkeypatch.setattr(graph, "available_sources", lambda cfg: ["kb"])
    assert _after_grounding({"grounded": False, "attempts": 0, "route": ["kb"]}) == "end"
    monkeypatch.setattr(graph, "available_sources", lambda cfg: ["kb", "issues"])
    state = {"grounded": False, "attempts": 1, "route": ["kb", "issues"]}
    assert _after_grounding(state) == "end"


# --- streaming -----------------------------------------------------------------

def test_stream_ask_emits_draft_deltas_then_done(monkeypatch) -> None:
    from repo_expert.agent import agent

    monkeypatch.setattr(graph, "available_sources", lambda cfg: ["kb"])
    monkeypatch.setattr(
        graph, "get_retrievers", lambda cfg: {"kb": lambda q, top, history: [_result()]}
    )
    monkeypatch.setattr(graph, "get_instance_config", lambda: SimpleNamespace(scope_prompt=None))
    monkeypatch.setattr(
        graph, "get_settings", lambda: SimpleNamespace(grounding_reasoning_effort="low")
    )
    monkeypatch.setattr(graph, "chat_stream", lambda *a, **k: iter(["Use ", "f() [1]"]))
    monkeypatch.setattr(graph, "chat_json", lambda *a, **k: {"grounded": True})

    events = list(agent.stream_ask("how?"))
    names = [e["event"] for e in events]
    assert names[0] == "stage" and names[-1] == "done"
    draft = names.index("draft")
    assert names[draft + 1:draft + 3] == ["delta", "delta"]
    assert "".join(e["text"] for e in events if e["event"] == "delta") == "Use f() [1]"
    assert [e["stage"] for e in events if e["event"] == "stage"] == [
        "retrieve", "generate", "verify"
    ]
    done = events[-1]
    assert done["answer"] == "Use f() [1]" and done["grounded"] is True
    assert done["citations"][0]["url"] == "http://x"
    # /ask runs the same nodes without a stream consumer and must get the same answer.
    assert agent.ask("how?").answer == "Use f() [1]"
