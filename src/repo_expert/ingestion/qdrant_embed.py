"""Qdrant Cloud Inference embedding helpers.

Qdrant Cloud embeds text **server-side** at upsert and query time: we hand it a
``models.Document(text=..., model=...)`` wherever a vector is expected and the
managed (free-tier) inference service produces the embedding. No vectors are
computed in our process, so there is no embedding-model download in the deploy
image and no Azure OpenAI embedding call on the Qdrant path.

Model: ``intfloat/multilingual-e5-small`` (384-dim), permitted on the free tier
(probed 2026-09-21).

**Why multilingual.** The previous model, ``all-MiniLM-L6-v2``, is English-only,
and it showed: the career document is written in English while the chat page and
its visitors are Spanish, so a Spanish question could not reach it. Measured on the
same index, same fusion — only the language of the question changed:

    "What projects has Jorge built?"      -> 6/6 career chunks (correct)
    "¿Qué proyectos ha construido Jorge?" -> 6/6 unrelated Spanish prompt templates

e5 keeps the 384 dimensions, so the collections' schema is unchanged; only the
vectors have to be rebuilt.

**Prefixes matter.** The e5 family is trained with asymmetric prefixes: stored text
must be embedded as ``passage: <text>`` and searches as ``query: <text>``. Using the
wrong one, or none, measurably degrades retrieval, so the two cases are separate
functions rather than one shared helper.

Both models truncate long inputs server-side (~512 tokens for e5), which is why the
markdown chunker splits oversized sections instead of relying on the model.
"""

from __future__ import annotations

from qdrant_client import models

from repo_expert.config.settings import get_settings
from repo_expert.ingestion.qdrant_collections import get_embedding_dim

__all__ = ["embed_model", "as_document", "as_query", "get_embedding_dim"]

# Model families that expect "passage:"/"query:" prefixes on their inputs.
_PREFIXED_FAMILIES = ("e5",)


def embed_model() -> str:
    """The configured Qdrant Cloud Inference embedding model id."""
    return get_settings().qdrant_embed_model


def _needs_prefix(model: str) -> bool:
    name = model.rsplit("/", 1)[-1].lower()
    return any(fam in name for fam in _PREFIXED_FAMILIES)


def as_document(text: str) -> models.Document:
    """Wrap stored text for server-side embedding (the ``passage`` side)."""
    model = embed_model()
    body = f"passage: {text}" if _needs_prefix(model) else text
    return models.Document(text=body, model=model)


def as_query(text: str) -> models.Document:
    """Wrap a search string for server-side embedding (the ``query`` side)."""
    model = embed_model()
    body = f"query: {text}" if _needs_prefix(model) else text
    return models.Document(text=body, model=model)
