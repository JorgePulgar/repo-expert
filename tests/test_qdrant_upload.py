"""Unit tests for chunk -> Qdrant point mapping (no network)."""

import types
import uuid

from qdrant_client import models

from repo_expert.ingestion import qdrant_upload
from repo_expert.ingestion.models import Chunk, make_chunk_id
from repo_expert.ingestion.qdrant_upload import chunk_to_point, point_id


def _chunk() -> Chunk:
    cid = make_chunk_id("o/r", "f.py", "sym")
    return Chunk(
        id=cid, repo_slug="o/r", source_kind="code", file_path="f.py",
        title="f", content="async def f(): ...", url="http://x",
        start_line=1, end_line=9,
    )


def test_point_id_is_stable_uuid() -> None:
    cid = make_chunk_id("o/r", "f.py", "sym")
    pid = point_id(cid)
    assert pid == point_id(cid)  # deterministic -> upsert, not duplicate
    uuid.UUID(pid)  # valid UUID (Qdrant requires int or UUID)


def test_point_id_differs_per_chunk() -> None:
    assert point_id("a") != point_id("b")


def test_chunk_to_point_embeds_server_side_and_carries_payload() -> None:
    pt = chunk_to_point(_chunk())
    assert isinstance(pt, models.PointStruct)
    # vector is a Document (embedded server-side at upsert), not a float list
    assert isinstance(pt.vector, models.Document)
    # e5 embeds stored text on the "passage" side of its asymmetric prefixes.
    assert pt.vector.text == "passage: async def f(): ..."
    # payload mirrors chunk metadata; vector field is excluded
    assert pt.payload["file_path"] == "f.py"
    assert pt.payload["source_kind"] == "code"
    assert pt.payload["content"] == "async def f(): ..."
    assert "vector" not in pt.payload


class _FakeClient:
    """Minimal Qdrant stand-in: one scroll page, records what was deleted."""

    def __init__(self, ids: list[str]) -> None:
        self._ids = ids
        self.deleted: list[str] = []

    def scroll(self, collection_name, limit, offset, with_payload, with_vectors):
        return ([types.SimpleNamespace(id=i) for i in self._ids], None)

    def delete(self, collection_name, points_selector):
        self.deleted.extend(points_selector.points)


def test_prune_missing_deletes_only_orphans(monkeypatch) -> None:
    kept = _chunk()
    orphan = point_id(make_chunk_id("o/r", "f.py", "sym--p1"))
    client = _FakeClient([point_id(kept.id), orphan])
    monkeypatch.setattr(qdrant_upload, "get_qdrant_client", lambda: client)

    removed = qdrant_upload.prune_missing("c", [kept])

    assert removed == 1
    assert client.deleted == [orphan]


def test_prune_missing_skips_empty_chunk_set(monkeypatch) -> None:
    """An empty run means "nothing was chunked", not "the collection is empty"."""
    client = _FakeClient([point_id("anything")])
    monkeypatch.setattr(qdrant_upload, "get_qdrant_client", lambda: client)

    assert qdrant_upload.prune_missing("c", []) == 0
    assert client.deleted == []
