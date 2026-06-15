"""Create the Azure AI Search indexes (docs + code) for the active instance.

One shared schema, reused for both indexes. Each index has hybrid-search fields
(keyword + vector) and a semantic configuration, so Foundry IQ can reference it as
an "existing search index" knowledge source. Vector dimension is derived from the
live embedding deployment (no hard-coded 1536/3072).
"""

from __future__ import annotations

import logging

from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)

from repo_expert.clients import get_search_index_client
from repo_expert.config.instance import InstanceConfig, get_instance_config
from repo_expert.ingestion.embed import get_embedding_dim

logger = logging.getLogger(__name__)

_VECTOR_PROFILE = "hnsw-profile"
_HNSW_CONFIG = "hnsw-config"
_SEMANTIC_CONFIG = "semantic-config"


def _build_index(name: str, dim: int) -> SearchIndex:
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SimpleField(name="file_path", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="url", type=SearchFieldDataType.String),
        SimpleField(name="source_kind", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="repo_slug", type=SearchFieldDataType.String, filterable=True),
        SearchField(
            name="section_path",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            searchable=True,
        ),
        SimpleField(name="start_line", type=SearchFieldDataType.Int32, filterable=True),
        SimpleField(name="end_line", type=SearchFieldDataType.Int32, filterable=True),
        SearchField(
            name="vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=dim,
            vector_search_profile_name=_VECTOR_PROFILE,
        ),
    ]
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name=_HNSW_CONFIG)],
        profiles=[
            VectorSearchProfile(
                name=_VECTOR_PROFILE, algorithm_configuration_name=_HNSW_CONFIG
            )
        ],
    )
    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name=_SEMANTIC_CONFIG,
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="title"),
                    content_fields=[SemanticField(field_name="content")],
                ),
            )
        ]
    )
    return SearchIndex(
        name=name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )


def create_indexes(cfg: InstanceConfig | None = None) -> list[str]:
    """Create-or-update the docs and code indexes for the active instance."""
    cfg = cfg or get_instance_config()
    dim = get_embedding_dim()
    client = get_search_index_client()
    names = [cfg.docs_index, cfg.code_index]
    if cfg.source3_index:  # career KB index (portfolio)
        names.append(cfg.source3_index)
    created: list[str] = []
    for name in names:
        client.create_or_update_index(_build_index(name, dim))
        logger.info("Created/updated index %s (dim=%d)", name, dim)
        created.append(name)
    return created
