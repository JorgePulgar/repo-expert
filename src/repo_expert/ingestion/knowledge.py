"""Create Foundry IQ knowledge sources + a knowledge base over our indexes.

Each AI Search index (docs, code) is registered as a ``SearchIndexKnowledgeSource``
("existing search index" type). A basic GA knowledge base references both. No LLM is
attached to the KB: it does multi-source retrieval/merge while our LangGraph layer
(Phase 3) owns query planning, routing, correction, and generation — the build-vs-buy
boundary. (LLM query planning and reasoning-effort tuning are preview-only in the GA
SDK; revisit if we move to a preview API version.)
"""

from __future__ import annotations

import logging

from azure.search.documents.indexes.models import (
    KnowledgeBase,
    KnowledgeSourceReference,
    SearchIndexFieldReference,
    SearchIndexKnowledgeSource,
    SearchIndexKnowledgeSourceParameters,
)

from repo_expert.clients import get_search_index_client
from repo_expert.config.instance import InstanceConfig, get_instance_config

logger = logging.getLogger(__name__)

_SEMANTIC_CONFIG = "semantic-config"

# Fields returned with each retrieved result (for citations downstream).
_CITATION_FIELDS = [
    "id",
    "content",
    "title",
    "file_path",
    "url",
    "source_kind",
    "section_path",
    "start_line",
    "end_line",
]

_DOCS_KS_DESC = (
    "Documentation and guides (README + markdown). Use for conceptual, how-to, "
    "and usage questions about the project."
)
_CODE_KS_DESC = (
    "Source code symbols (functions and classes with file/line spans). Use for "
    "'how is X implemented?' and code-behavior questions."
)


def _ks_name(index_name: str) -> str:
    return f"{index_name}-ks"


def _make_knowledge_source(index_name: str, description: str) -> SearchIndexKnowledgeSource:
    return SearchIndexKnowledgeSource(
        name=_ks_name(index_name),
        description=description,
        search_index_parameters=SearchIndexKnowledgeSourceParameters(
            search_index_name=index_name,
            semantic_configuration_name=_SEMANTIC_CONFIG,
            source_data_fields=[SearchIndexFieldReference(name=f) for f in _CITATION_FIELDS],
        ),
    )


def kb_name(cfg: InstanceConfig) -> str:
    return f"repo-expert-{cfg.name}-kb"


def create_knowledge_sources(cfg: InstanceConfig | None = None) -> list[str]:
    """Create-or-update the docs + code knowledge sources for the active instance."""
    cfg = cfg or get_instance_config()
    client = get_search_index_client()
    sources = [
        _make_knowledge_source(cfg.docs_index, _DOCS_KS_DESC),
        _make_knowledge_source(cfg.code_index, _CODE_KS_DESC),
    ]
    for ks in sources:
        client.create_or_update_knowledge_source(ks)
        logger.info("Created/updated knowledge source %s", ks.name)
    return [ks.name for ks in sources]


def create_knowledge_base(cfg: InstanceConfig | None = None) -> str:
    """Create-or-update the knowledge base referencing both knowledge sources."""
    cfg = cfg or get_instance_config()
    client = get_search_index_client()
    name = kb_name(cfg)
    kb = KnowledgeBase(
        name=name,
        description=f"Repo Expert knowledge base for the {cfg.name} instance.",
        knowledge_sources=[
            KnowledgeSourceReference(name=_ks_name(cfg.docs_index)),
            KnowledgeSourceReference(name=_ks_name(cfg.code_index)),
        ],
    )
    client.create_or_update_knowledge_base(kb)
    logger.info("Created/updated knowledge base %s", name)
    return name
