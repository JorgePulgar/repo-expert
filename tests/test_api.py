"""Offline API tests (agent and index lookups mocked)."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import BadRequestError, RateLimitError

from repo_expert.agent.agent import AnswerResult
from repo_expert.api import routes
from repo_expert.api.app import create_app
from repo_expert.config.settings import get_settings
from repo_expert.retrieval.models import Citation


@pytest.fixture
def client(monkeypatch):
    # Force the public instance regardless of the developer's local .env, and reset
    # the settings cache so the override is read (get_settings is lru_cached).
    monkeypatch.setenv("REPO_EXPERT_INSTANCE", "public")
    get_settings.cache_clear()
    app = create_app()
    yield TestClient(app, raise_server_exceptions=False)
    get_settings.cache_clear()


def test_health_ok(client, monkeypatch) -> None:
    monkeypatch.setattr(routes, "_index_count", lambda name: 100)
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["instance"] == "public"
    assert all(v == 100 for v in body["indexes"].values())


def test_health_degraded_when_index_unreachable(client, monkeypatch) -> None:
    monkeypatch.setattr(routes, "_index_count", lambda name: None)
    assert client.get("/health").json()["status"] == "degraded"


def test_ask_happy_path(client, monkeypatch) -> None:
    fake = AnswerResult(
        answer="Use Query().",
        citations=[Citation(title="Query Parameters", url="http://x")],
        route=["kb"],
        grounded=True,
        fallback_used=False,
    )
    monkeypatch.setattr(routes, "ask", lambda q, history=None: fake)
    body = client.post("/ask", json={"question": "How do I query?"}).json()
    assert body["answer"] == "Use Query()."
    assert body["route"] == ["kb"] and body["grounded"] is True
    assert body["citations"][0]["url"] == "http://x"


def test_ask_validation_rejects_empty(client) -> None:
    assert client.post("/ask", json={"question": ""}).status_code == 422


def test_ask_upstream_error_returns_500(client, monkeypatch) -> None:
    def _boom(q, history=None):
        raise RuntimeError("agent down")

    monkeypatch.setattr(routes, "ask", _boom)
    resp = client.post("/ask", json={"question": "x"})
    assert resp.status_code == 500 and "detail" in resp.json()


def _sse_events(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_ask_stream_relays_events(client, monkeypatch) -> None:
    def _fake(q, history=None):
        yield {"event": "draft", "citations": [{"title": "t", "url": "http://x"}]}
        yield {"event": "delta", "text": "Hola "}
        yield {"event": "delta", "text": "[1]"}
        yield {"event": "done", "answer": "Hola [1]", "grounded": True}

    monkeypatch.setattr(routes, "stream_ask", _fake)
    resp = client.post("/ask/stream", json={"question": "hola"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = _sse_events(resp.text)
    assert [name for name, _ in events] == ["draft", "delta", "delta", "done"]
    assert events[-1][1]["answer"] == "Hola [1]"


def test_ask_stream_failure_becomes_error_event(client, monkeypatch) -> None:
    def _fake(q, history=None):
        yield {"event": "delta", "text": "Ho"}
        raise RuntimeError("model went away")

    monkeypatch.setattr(routes, "stream_ask", _fake)
    events = _sse_events(client.post("/ask/stream", json={"question": "x"}).text)
    assert events[-1] == ("error", {"kind": "internal"})


def test_error_kind_classifies_quota_and_filter() -> None:
    request = httpx.Request("POST", "http://x")
    quota = RateLimitError("quota", response=httpx.Response(429, request=request), body=None)
    filtered = BadRequestError(
        "filtered", response=httpx.Response(400, request=request),
        body={"code": "content_filter"},
    )
    assert routes._error_kind(quota) == "busy"
    assert routes._error_kind(filtered) == "content_filter"
    assert routes._error_kind(RuntimeError()) == "internal"


def test_ask_stream_validation_rejects_empty(client) -> None:
    assert client.post("/ask/stream", json={"question": ""}).status_code == 422
