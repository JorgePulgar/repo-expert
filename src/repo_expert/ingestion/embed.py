"""Embed chunks via Azure OpenAI, token-aware batched and rate-limit safe."""

from __future__ import annotations

import logging
import time
from functools import lru_cache

import tiktoken
from openai import APIError, RateLimitError

from repo_expert.clients import get_openai_client
from repo_expert.config.settings import get_settings
from repo_expert.ingestion.models import Chunk

logger = logging.getLogger(__name__)

_MAX_RETRIES = 6
_BASE_DELAY = 2.0  # seconds; exponential backoff

# ada-002 / 3-* embedding models allow 8192 tokens; keep headroom per request
# (the limit applies to the *sum* of all inputs in one request) and per input.
_MAX_TOKENS_PER_REQUEST = 8000
_MAX_TOKENS_PER_INPUT = 8000
_MAX_INPUTS_PER_REQUEST = 1024

_encoder = tiktoken.get_encoding("cl100k_base")


def _truncate(text: str, max_tokens: int = _MAX_TOKENS_PER_INPUT) -> str:
    """Truncate text to at most ``max_tokens`` tokens (oversized chunks are rare)."""
    tokens = _encoder.encode(text)
    if len(tokens) <= max_tokens:
        return text
    logger.warning("Truncating a %d-token input to %d", len(tokens), max_tokens)
    return _encoder.decode(tokens[:max_tokens])


def _token_batches(texts: list[str]) -> list[list[str]]:
    """Group texts so each request stays under the token and item limits."""
    batches: list[list[str]] = []
    cur: list[str] = []
    cur_tokens = 0
    for text in texts:
        n = len(_encoder.encode(text))
        over_tokens = cur_tokens + n > _MAX_TOKENS_PER_REQUEST
        over_count = len(cur) >= _MAX_INPUTS_PER_REQUEST
        if cur and (over_tokens or over_count):
            batches.append(cur)
            cur, cur_tokens = [], 0
        cur.append(text)
        cur_tokens += n
    if cur:
        batches.append(cur)
    return batches


@lru_cache
def get_embedding_dim() -> int:
    """Probe the embedding deployment once to learn its vector dimension."""
    return len(embed_texts(["dimension probe"])[0])


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return one embedding vector per input text, preserving order."""
    client = get_openai_client()
    deployment = get_settings().azure_openai_embed_deployment
    safe = [_truncate(t) for t in texts]
    vectors: list[list[float]] = []
    for batch in _token_batches(safe):
        vectors.extend(_embed_batch(client, deployment, batch))
    return vectors


def _embed_batch(client, deployment: str, batch: list[str]) -> list[list[float]]:
    for attempt in range(_MAX_RETRIES):
        try:
            resp = client.embeddings.create(model=deployment, input=batch)
            return [d.embedding for d in resp.data]
        except RateLimitError as exc:
            if attempt == _MAX_RETRIES - 1:
                raise
            delay = _BASE_DELAY * (2**attempt)
            logger.warning("Embed retry %d after %.0fs (%s)", attempt + 1, delay, exc)
            time.sleep(delay)
        except APIError:
            raise
    raise RuntimeError("unreachable")  # pragma: no cover


def embed_chunks(chunks: list[Chunk]) -> list[Chunk]:
    """Attach an embedding vector to each chunk (in place) and return them."""
    vectors = embed_texts([c.content for c in chunks])
    for chunk, vector in zip(chunks, vectors, strict=True):
        chunk.vector = vector
    logger.info("Embedded %d chunks", len(chunks))
    return chunks
