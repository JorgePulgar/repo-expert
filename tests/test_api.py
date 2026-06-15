"""Offline API tests (agent and index lookups mocked)."""

import pytest
from fastapi.testclient import TestClient

from repo_expert.agent.agent import AnswerResult
from repo_expert.api import routes
from repo_expert.api.app import create_app
from repo_expert.retrieval.models import Citation


@pytest.fixture
def client():
    return TestClient(create_app(), raise_server_exceptions=False)


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
    monkeypatch.setattr(routes, "ask", lambda q: fake)
    body = client.post("/ask", json={"question": "How do I query?"}).json()
    assert body["answer"] == "Use Query()."
    assert body["route"] == ["kb"] and body["grounded"] is True
    assert body["citations"][0]["url"] == "http://x"


def test_ask_validation_rejects_empty(client) -> None:
    assert client.post("/ask", json={"question": ""}).status_code == 422


def test_ask_upstream_error_returns_500(client, monkeypatch) -> None:
    def _boom(q):
        raise RuntimeError("agent down")

    monkeypatch.setattr(routes, "ask", _boom)
    resp = client.post("/ask", json={"question": "x"})
    assert resp.status_code == 500 and "detail" in resp.json()
