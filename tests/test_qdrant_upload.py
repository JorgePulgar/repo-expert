"""Unit tests for chunk -> Qdrant point mapping (no network)."""

import uuid

from qdrant_client import models

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
    assert pt.vector.text == "async def f(): ..."
    # payload mirrors chunk metadata; vector field is excluded
    assert pt.payload["file_path"] == "f.py"
    assert pt.payload["source_kind"] == "code"
    assert pt.payload["content"] == "async def f(): ..."
    assert "vector" not in pt.payload
