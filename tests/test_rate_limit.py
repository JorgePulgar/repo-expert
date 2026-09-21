"""Rate-limiting tests for the public /ask endpoint (agent mocked)."""

import pytest
from fastapi.testclient import TestClient

from repo_expert.agent.agent import AnswerResult
from repo_expert.api import routes
from repo_expert.api.app import create_app
from repo_expert.api.rate_limit import client_ip, reset_rate_limit
from repo_expert.config.settings import get_settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("REPO_EXPERT_INSTANCE", "public")
    monkeypatch.setenv("RATE_LIMIT_PER_HOUR", "3")
    get_settings.cache_clear()
    reset_rate_limit()
    monkeypatch.setattr(
        routes,
        "ask",
        lambda q, history=None: AnswerResult(answer="ok", citations=[], route=["kb"], grounded=True, fallback_used=False),
    )
    app = create_app()
    yield TestClient(app, raise_server_exceptions=False)
    get_settings.cache_clear()
    reset_rate_limit()


def _ask(client, ip="203.0.113.7"):
    return client.post(
        "/ask", json={"question": "hola"}, headers={"x-forwarded-for": ip}
    )


def test_requests_under_the_limit_pass(client) -> None:
    for _ in range(3):
        assert _ask(client).status_code == 200


def test_request_over_the_limit_is_rejected(client) -> None:
    for _ in range(3):
        _ask(client)
    resp = _ask(client)
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers
    assert "3 questions per hour" in resp.json()["detail"]


def test_limit_is_per_ip(client) -> None:
    for _ in range(3):
        _ask(client, ip="203.0.113.7")
    assert _ask(client, ip="203.0.113.7").status_code == 429
    # A different caller still has its own budget.
    assert _ask(client, ip="198.51.100.2").status_code == 200


def test_health_is_not_rate_limited(client, monkeypatch) -> None:
    """The chat page pings /health on load to warm the container; that must be free."""
    monkeypatch.setattr(routes, "_index_count", lambda name: 1)
    for _ in range(10):
        assert client.get("/health").status_code == 200


def test_zero_disables_the_limiter(monkeypatch) -> None:
    monkeypatch.setenv("REPO_EXPERT_INSTANCE", "public")
    monkeypatch.setenv("RATE_LIMIT_PER_HOUR", "0")
    get_settings.cache_clear()
    reset_rate_limit()
    monkeypatch.setattr(
        routes,
        "ask",
        lambda q, history=None: AnswerResult(answer="ok", citations=[], route=["kb"], grounded=True, fallback_used=False),
    )
    c = TestClient(create_app(), raise_server_exceptions=False)
    for _ in range(12):
        assert c.post("/ask", json={"question": "hola"}).status_code == 200
    get_settings.cache_clear()
    reset_rate_limit()


class _Req:
    """Minimal stand-in for a Starlette Request."""

    def __init__(self, xff=None, host="10.0.0.1"):
        self.headers = {"x-forwarded-for": xff} if xff else {}
        self.client = type("C", (), {"host": host})()


def test_client_ip_prefers_rightmost_forwarded_entry() -> None:
    """A caller can forge the left of X-Forwarded-For; the ingress appends on the right."""
    assert client_ip(_Req("1.2.3.4, 203.0.113.9")) == "203.0.113.9"
    assert client_ip(_Req("203.0.113.9:41234")) == "203.0.113.9"
    assert client_ip(_Req(None, host="10.0.0.1")) == "10.0.0.1"
