"""Tests for neighbour expansion in the KB retriever (mocked Qdrant, no network).

The markdown chunker splits long sections, so an answer can straddle a boundary:
the matching chunk names the project, the next one says what it does. Neighbours
are merged into the hit's own text rather than appended as extra sources, so the
``[n]`` numbering the model cites stays aligned with the citation list.
"""

import pytest

from repo_expert.config.instance import get_instance_config
from repo_expert.retrieval import kb


class _Pt:
    def __init__(self, payload: dict, score: float = 0.9) -> None:
        self.payload = payload
        self.score = score


class _Resp:
    def __init__(self, points):  # noqa: ANN001
        self.points = points


class _FakeClient:
    def __init__(self, hits, neighbours=None, fail_scroll=False):  # noqa: ANN001
        self._hits = hits
        self._neighbours = neighbours or []
        self._fail = fail_scroll
        self.scroll_calls = 0

    def query_points(self, collection_name, query, limit, with_payload):  # noqa: ANN001
        return _Resp(self._hits.get(collection_name, []))

    def scroll(self, **kwargs):  # noqa: ANN003
        self.scroll_calls += 1
        if self._fail:
            raise RuntimeError("qdrant unavailable")
        return self._neighbours, None


def _payload(kind, name, seq, content, path="career.md"):  # noqa: ANN001
    return {"source_kind": kind, "title": name, "url": "http://x", "content": content,
            "file_path": path, "seq": seq, "repo_slug": "JorgePulgar/repo-expert"}


@pytest.fixture(autouse=True)
def _no_llm_rewrite(monkeypatch):
    monkeypatch.setattr(kb, "rewrite_query", lambda q, h=None: q)


def test_neighbours_are_merged_into_the_hit(monkeypatch) -> None:
    cfg = get_instance_config("portfolio")
    client = _FakeClient(
        hits={cfg.source3_index: [_Pt(_payload("career", "Proyectos", 5, "EL HIT"))]},
        neighbours=[
            _Pt(_payload("career", "Proyectos", 4, "ANTES")),
            _Pt(_payload("career", "Proyectos", 6, "DESPUES")),
        ],
    )
    monkeypatch.setattr(kb, "get_qdrant_client", lambda: client)

    results = kb.retrieve_kb("x", cfg=cfg, top=1)

    assert len(results) == 1, "neighbours must not become extra sources"
    assert results[0].content == "ANTES\n\nEL HIT\n\nDESPUES"
    # The citation still points at the hit itself.
    assert results[0].seq == 5


def test_expansion_can_be_switched_off(monkeypatch) -> None:
    cfg = get_instance_config("portfolio")
    client = _FakeClient(hits={cfg.source3_index: [_Pt(_payload("career", "P", 5, "EL HIT"))]})
    monkeypatch.setattr(kb, "get_qdrant_client", lambda: client)

    results = kb.retrieve_kb("x", cfg=cfg, top=1, neighbours=False)

    assert results[0].content == "EL HIT"
    assert client.scroll_calls == 0


def test_chunks_without_seq_are_skipped(monkeypatch) -> None:
    """Code chunks are whole symbols, not split prose, so they carry no seq."""
    cfg = get_instance_config("portfolio")
    payload = _payload("code", "f", None, "def f(): ...", path="a.py")
    del payload["seq"]
    client = _FakeClient(hits={cfg.code_index: [_Pt(payload)]})
    monkeypatch.setattr(kb, "get_qdrant_client", lambda: client)

    results = kb.retrieve_kb("x", cfg=cfg, top=1)

    assert results[0].content == "def f(): ..."
    assert client.scroll_calls == 0


def test_lookup_failure_leaves_results_intact(monkeypatch) -> None:
    """Extra context is a bonus; losing it must not lose the answer."""
    cfg = get_instance_config("portfolio")
    client = _FakeClient(
        hits={cfg.source3_index: [_Pt(_payload("career", "P", 5, "EL HIT"))]},
        fail_scroll=True,
    )
    monkeypatch.setattr(kb, "get_qdrant_client", lambda: client)

    results = kb.retrieve_kb("x", cfg=cfg, top=1)

    assert results[0].content == "EL HIT"
