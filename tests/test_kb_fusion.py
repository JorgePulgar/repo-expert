"""Unit tests for fusion in the KB retriever (mocked Qdrant, no network).

Fusion has to satisfy two opposing requirements:

* code chunks score systematically lower than prose for a natural-language query,
  so a plain global sort by cosine starves them;
* plain RRF scores only by rank *within* a collection, which degenerates into a
  fixed quota (docs#1, code#1, career#1, docs#2 …) and hands four of six slots to
  collections that have nothing to say.

The tests below pin both ends: code still survives when it is genuinely relevant,
and a collection that is merely irrelevant no longer takes its share anyway.
"""

import pytest

from repo_expert.config.instance import get_instance_config
from repo_expert.retrieval import kb


class _Pt:
    def __init__(self, payload: dict, score: float) -> None:
        self.payload = payload
        self.score = score


class _Resp:
    def __init__(self, points: list[_Pt]) -> None:
        self.points = points


class _FakeClient:
    def __init__(self, by_collection: dict[str, list[_Pt]]) -> None:
        self._b = by_collection

    def query_points(self, collection_name, query, limit, with_payload):  # noqa: ANN001
        return _Resp(self._b.get(collection_name, []))

    def scroll(self, **kwargs):  # noqa: ANN001, ANN003 - neighbour lookups: none here
        return [], None


def _doc(kind: str, name: str, score: float) -> _Pt:
    return _Pt(
        {"source_kind": kind, "title": name, "url": "http://x", "content": name,
         "file_path": f"{name}.x"},
        score,
    )


@pytest.fixture(autouse=True)
def _no_llm_rewrite(monkeypatch):
    """Retrieval tests measure fusion, not the LLM query rewrite."""
    monkeypatch.setattr(kb, "rewrite_query", lambda q, h=None: q)


def test_code_survives_when_it_is_comparably_relevant(monkeypatch) -> None:
    cfg = get_instance_config("public")  # docs + code collections
    fake = _FakeClient({
        cfg.docs_index: [_doc("docs", f"d{i}", 0.90 - i * 0.01) for i in range(5)],
        # Close behind: code that genuinely answers the question.
        cfg.code_index: [_doc("code", f"c{i}", 0.82 - i * 0.01) for i in range(5)],
    })
    monkeypatch.setattr(kb, "get_qdrant_client", lambda: fake)

    results = kb.retrieve_kb("anything", cfg=cfg, top=4)

    kinds = [r.kind for r in results]
    assert "code" in kinds, "code starved by a raw-score merge"
    assert kinds[0] == "docs"


def test_irrelevant_collection_no_longer_gets_a_quota(monkeypatch) -> None:
    """The bug this replaced: 2 of every 6 slots went to code regardless."""
    cfg = get_instance_config("public")
    fake = _FakeClient({
        cfg.docs_index: [_doc("docs", f"d{i}", 0.90 - i * 0.01) for i in range(6)],
        # Nothing in code comes close to answering this question.
        cfg.code_index: [_doc("code", f"c{i}", 0.20 - i * 0.01) for i in range(6)],
    })
    monkeypatch.setattr(kb, "get_qdrant_client", lambda: fake)

    results = kb.retrieve_kb("anything", cfg=cfg, top=6)

    assert [r.kind for r in results] == ["docs"] * 6


def test_raw_score_is_preserved_on_results(monkeypatch) -> None:
    cfg = get_instance_config("public")
    fake = _FakeClient({
        cfg.docs_index: [_doc("docs", "d0", 0.9)],
        cfg.code_index: [_doc("code", "c0", 0.8)],
    })
    monkeypatch.setattr(kb, "get_qdrant_client", lambda: fake)

    results = kb.retrieve_kb("anything", cfg=cfg, top=2)

    assert {r.score for r in results} == {0.9, 0.8}


def test_empty_index_returns_nothing(monkeypatch) -> None:
    cfg = get_instance_config("public")
    monkeypatch.setattr(kb, "get_qdrant_client", lambda: _FakeClient({}))
    assert kb.retrieve_kb("anything", cfg=cfg, top=5) == []
