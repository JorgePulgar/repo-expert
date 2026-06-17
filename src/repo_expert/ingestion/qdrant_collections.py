"""Create the Qdrant collections (docs + code [+ career]) for the active instance.

Qdrant analogue of the Azure AI Search index schema. One collection per source,
named from the instance config (so switching instance = changing config, not code).
Each point stores one chunk vector (cosine distance) plus a payload mirroring the
chunk metadata. Payload indexes are created on the fields used for retrieval-time
filtering, matching the ``filterable=True`` fields of the AI Search schema.

Vector dimension is derived from the chosen Qdrant inference embedding model
(`mxbai-embed-large-v1` = 1024; `all-MiniLM-L6-v2` fallback = 384), not hard-coded.
"""

from __future__ import annotations

import logging

from qdrant_client.models import Distance, PayloadSchemaType, VectorParams

from repo_expert.clients import get_qdrant_client
from repo_expert.config.instance import InstanceConfig, get_instance_config
from repo_expert.config.settings import get_settings

logger = logging.getLogger(__name__)

_DISTANCE = Distance.COSINE

# Vector dimensions per supported Qdrant Cloud inference model (decisions 2026-06-16).
EMBED_DIMS: dict[str, int] = {
    "mixedbread-ai/mxbai-embed-large-v1": 1024,
    "sentence-transformers/all-MiniLM-L6-v2": 384,
}

# Payload fields filtered on at retrieval time (mirror AI Search filterable fields).
_KEYWORD_FIELDS = ("source_kind", "repo_slug", "file_path")
_INTEGER_FIELDS = ("start_line", "end_line")


def get_embedding_dim(model: str | None = None) -> int:
    """Vector dimension for the configured (or given) embedding model."""
    model = model or get_settings().qdrant_embed_model
    try:
        return EMBED_DIMS[model]
    except KeyError:
        valid = ", ".join(sorted(EMBED_DIMS))
        raise ValueError(
            f"Unknown embedding model {model!r}. Known models: {valid}."
        ) from None


def collection_names(cfg: InstanceConfig) -> list[str]:
    """Collection names for an instance (docs, code, and career when present)."""
    names = [cfg.docs_index, cfg.code_index]
    if cfg.source3_index:  # career KB collection (portfolio)
        names.append(cfg.source3_index)
    return names


def create_collections(cfg: InstanceConfig | None = None) -> list[str]:
    """Create-or-update the Qdrant collections for the active instance.

    Idempotent: existing collections are left in place; payload indexes are
    (re)declared so re-running keeps the schema current. Returns the names.
    """
    cfg = cfg or get_instance_config()
    client = get_qdrant_client()
    dim = get_embedding_dim()
    created: list[str] = []
    for name in collection_names(cfg):
        if not client.collection_exists(name):
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dim, distance=_DISTANCE),
            )
            logger.info("Created Qdrant collection %s (dim=%d)", name, dim)
        else:
            logger.info("Qdrant collection %s already exists", name)
        for field in _KEYWORD_FIELDS:
            client.create_payload_index(name, field, PayloadSchemaType.KEYWORD)
        for field in _INTEGER_FIELDS:
            client.create_payload_index(name, field, PayloadSchemaType.INTEGER)
        created.append(name)
    return created
