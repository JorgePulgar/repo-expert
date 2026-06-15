"""Upload embedded chunks to an AI Search index (upsert by stable id)."""

from __future__ import annotations

import logging

from repo_expert.clients import get_search_client
from repo_expert.ingestion.models import Chunk

logger = logging.getLogger(__name__)


def chunk_to_doc(chunk: Chunk) -> dict:
    """Map a chunk to an index document, dropping null optional fields."""
    doc = chunk.model_dump(exclude_none=True)
    return doc


def upload_chunks(index_name: str, chunks: list[Chunk], batch_size: int = 1000) -> int:
    """Upsert chunks into the index. Re-runs update (same id) rather than duplicate."""
    if not chunks:
        return 0
    client = get_search_client(index_name)
    uploaded = 0
    for start in range(0, len(chunks), batch_size):
        batch = [chunk_to_doc(c) for c in chunks[start : start + batch_size]]
        results = client.merge_or_upload_documents(documents=batch)
        failed = [r for r in results if not r.succeeded]
        if failed:
            raise RuntimeError(f"{len(failed)} docs failed to upload to {index_name}")
        uploaded += len(batch)
        logger.info("Uploaded %d/%d to %s", uploaded, len(chunks), index_name)
    return uploaded
