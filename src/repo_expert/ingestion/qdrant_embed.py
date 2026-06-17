"""Qdrant Cloud Inference embedding helpers.

Qdrant Cloud embeds text **server-side** at upsert and query time: we hand it a
``models.Document(text=..., model=...)`` wherever a vector is expected and the
managed (free-tier) inference service produces the embedding. No vectors are
computed in our process, so there is no embedding-model download in the deploy
image and no Azure OpenAI embedding call on the Qdrant path.

Model: ``sentence-transformers/all-MiniLM-L6-v2`` (384-dim). The richer
``mxbai-embed-large-v1`` (1024-dim) is **not permitted on the Qdrant free tier**
(verified 2026-06-17, P7-T2 gate), so we use the pre-authorized MiniLM fallback.
MiniLM truncates inputs to ~256 tokens server-side; oversized code/doc chunks lose
their tail, which T6 eval will quantify.

Batching and retry now live where the network call happens: at **upsert** (T3,
batched ``PointStruct`` lists) and **query** (T4), handled by ``qdrant-client``.
"""

from __future__ import annotations

from qdrant_client import models

from repo_expert.config.settings import get_settings
from repo_expert.ingestion.qdrant_collections import get_embedding_dim

__all__ = ["embed_model", "as_document", "get_embedding_dim"]


def embed_model() -> str:
    """The configured Qdrant Cloud Inference embedding model id."""
    return get_settings().qdrant_embed_model


def as_document(text: str) -> models.Document:
    """Wrap text for server-side embedding by Qdrant Cloud Inference.

    Used both as a point ``vector`` at upsert and as a ``query`` at search time.
    """
    return models.Document(text=text, model=embed_model())
