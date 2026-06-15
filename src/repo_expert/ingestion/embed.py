"""Embed chunks via Azure OpenAI, batched and rate-limit safe."""

from __future__ import annotations

import logging
import time

from openai import APIError, RateLimitError

from repo_expert.clients import get_openai_client
from repo_expert.config.settings import get_settings
from repo_expert.ingestion.models import Chunk

logger = logging.getLogger(__name__)

_MAX_RETRIES = 6
_BASE_DELAY = 2.0  # seconds; exponential backoff


def embed_texts(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """Return one embedding vector per input text, preserving order."""
    client = get_openai_client()
    deployment = get_settings().azure_openai_embed_deployment
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        vectors.extend(_embed_batch(client, deployment, batch))
    return vectors


def _embed_batch(client, deployment: str, batch: list[str]) -> list[list[float]]:
    for attempt in range(_MAX_RETRIES):
        try:
            resp = client.embeddings.create(model=deployment, input=batch)
            return [d.embedding for d in resp.data]
        except (RateLimitError, APIError) as exc:
            if attempt == _MAX_RETRIES - 1:
                raise
            delay = _BASE_DELAY * (2**attempt)
            logger.warning("Embed retry %d after %.0fs (%s)", attempt + 1, delay, exc)
            time.sleep(delay)
    raise RuntimeError("unreachable")  # pragma: no cover


def embed_chunks(chunks: list[Chunk], batch_size: int = 64) -> list[Chunk]:
    """Attach an embedding vector to each chunk (in place) and return them."""
    vectors = embed_texts([c.content for c in chunks], batch_size=batch_size)
    for chunk, vector in zip(chunks, vectors, strict=True):
        chunk.vector = vector
    logger.info("Embedded %d chunks", len(chunks))
    return chunks
