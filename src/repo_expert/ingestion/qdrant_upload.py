"""Upsert chunks into a Qdrant collection.

The vector is a ``models.Document`` so Qdrant Cloud embeds the chunk text
server-side at upsert time (no client-side embedding). Re-ingest is an upsert,
not a duplicate insert: each chunk's stable id maps deterministically to a Qdrant
point id. Point ids must be an unsigned int or a UUID, but our chunk ids are sha1
hex strings, so we derive a stable UUIDv5 from the chunk id (the original id is
also kept in the payload for citation).
"""

from __future__ import annotations

import logging
import uuid

from qdrant_client import models

from repo_expert.clients import get_qdrant_client
from repo_expert.ingestion.models import Chunk
from repo_expert.ingestion.qdrant_embed import as_document

logger = logging.getLogger(__name__)

# Fixed namespace so chunk_id -> point_id is stable across runs (upsert, not insert).
_POINT_NS = uuid.UUID("6f9619ff-8b86-d011-b42d-00cf4fc964ff")


def point_id(chunk_id: str) -> str:
    """Deterministic Qdrant point id (UUIDv5) for a chunk's stable id."""
    return str(uuid.uuid5(_POINT_NS, chunk_id))


def chunk_to_point(chunk: Chunk) -> models.PointStruct:
    """Map a chunk to a Qdrant point: server-side-embedded vector + metadata payload."""
    payload = chunk.model_dump(exclude_none=True, exclude={"vector"})
    return models.PointStruct(
        id=point_id(chunk.id),
        vector=as_document(chunk.content),
        payload=payload,
    )


def upsert_chunks(collection_name: str, chunks: list[Chunk], batch_size: int = 64) -> int:
    """Upsert chunks into the collection (server-side embedded). Returns the count."""
    if not chunks:
        return 0
    client = get_qdrant_client()
    uploaded = 0
    for start in range(0, len(chunks), batch_size):
        batch = [chunk_to_point(c) for c in chunks[start : start + batch_size]]
        client.upsert(collection_name=collection_name, points=batch)
        uploaded += len(batch)
        logger.info("Upserted %d/%d to %s", uploaded, len(chunks), collection_name)
    return uploaded
