"""Knowledge base retriever: wraps Foundry IQ agentic retrieval.

The KB ``retrieve`` returns reranked references (title + docKey + score) but, in
the GA API, no inline ``sourceData``. We resolve each ``docKey`` back to its stored
document in the docs/code indexes to build full content + citations.
"""

from __future__ import annotations

import logging

from azure.core.exceptions import ResourceNotFoundError
from azure.search.documents.knowledgebases.models import (
    KnowledgeBaseRetrievalRequest,
    KnowledgeRetrievalSemanticIntent,
)

from repo_expert.clients import get_kb_retrieval_client, get_search_client
from repo_expert.config.instance import InstanceConfig, get_instance_config
from repo_expert.ingestion.knowledge import kb_name
from repo_expert.retrieval.models import Citation, RetrievalResult

logger = logging.getLogger(__name__)

_SELECT = [
    "id", "content", "title", "file_path", "url",
    "source_kind", "section_path", "start_line", "end_line",
]


def _resolve_docs(cfg: InstanceConfig, keys: list[str]) -> dict[str, dict]:
    """Look up stored documents by id across the docs and code indexes.

    The key field isn't filterable, so resolve each key with ``get_document``,
    trying the docs index then the code index.
    """
    index_names = [cfg.docs_index, cfg.code_index]
    if cfg.source3_index:  # career KB index (portfolio)
        index_names.append(cfg.source3_index)
    clients = [get_search_client(i) for i in index_names]
    docs: dict[str, dict] = {}
    for key in dict.fromkeys(keys):  # de-dup, preserve order
        for client in clients:
            try:
                docs[key] = client.get_document(key=key, selected_fields=_SELECT)
                break
            except ResourceNotFoundError:
                continue
    return docs


def retrieve_kb(
    query: str, cfg: InstanceConfig | None = None, top: int = 10
) -> list[RetrievalResult]:
    """Retrieve from the knowledge base and return unified results with citations."""
    cfg = cfg or get_instance_config()
    client = get_kb_retrieval_client(kb_name(cfg))
    request = KnowledgeBaseRetrievalRequest(
        intents=[KnowledgeRetrievalSemanticIntent(search=query)]
    )
    response = dict(client.retrieve(request))
    references = [dict(r) for r in (response.get("references") or [])]

    keys = [r["docKey"] for r in references if r.get("docKey")]
    docs = _resolve_docs(cfg, keys)

    results: list[RetrievalResult] = []
    for ref in references:
        doc = docs.get(ref.get("docKey"))
        if not doc:
            continue
        results.append(
            RetrievalResult(
                source="kb",
                kind=doc.get("source_kind", "docs"),
                content=doc.get("content", ""),
                score=ref.get("rerankerScore"),
                citation=Citation(
                    title=doc.get("title") or ref.get("title") or "",
                    url=doc.get("url", ""),
                    file_path=doc.get("file_path"),
                    section_path=doc.get("section_path") or [],
                    start_line=doc.get("start_line"),
                    end_line=doc.get("end_line"),
                ),
            )
        )
    results.sort(key=lambda r: r.score or 0.0, reverse=True)
    return results[:top]
