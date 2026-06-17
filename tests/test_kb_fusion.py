"""Unit test for RRF fusion in the KB retriever (mocked Qdrant, no network)."""

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


def _doc(kind: str, name: str, score: float) -> _Pt:
    return _Pt(
        {"source_kind": kind, "title": name, "url": "http://x", "content": name,
         "file_path": f"{name}.x"},
        score,
    )


def test_rrf_keeps_code_despite_lower_scores(monkeypatch) -> None:
    cfg = get_instance_config("public")  # docs + code collections
    fake = _FakeClient({
        cfg.docs_index: [_doc("docs", f"d{i}", 0.9 - i * 0.01) for i in range(5)],
        cfg.code_index: [_doc("code", f"c{i}", 0.3 - i * 0.01) for i in range(5)],
    })
    monkeypatch.setattr(kb, "get_qdrant_client", lambda: fake)

    results = kb.retrieve_kb("anything", cfg=cfg, top=4)

    kinds = [r.kind for r in results]
    # A global cosine sort would return all docs; RRF interleaves by rank.
    assert "code" in kinds, "code starved by raw-score merge"
    assert results[0].kind == "docs" and results[1].kind == "code"
    # raw cosine score is preserved on the result even though ordering is by RRF
    assert results[1].score == 0.3
