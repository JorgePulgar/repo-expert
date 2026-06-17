"""End-to-end ingestion: fetch -> chunk -> upsert into Qdrant.

Embedding is server-side at upsert time (Qdrant Cloud Inference), so there is no
separate embed step. Collections are provisioned up front; chunks are upserted by
stable id, so re-ingest updates in place rather than duplicating.
"""

from __future__ import annotations

import logging

from repo_expert.config.instance import InstanceConfig, get_instance_config
from repo_expert.ingestion.career import chunk_career_doc
from repo_expert.ingestion.code import chunk_repo_code
from repo_expert.ingestion.fetch import fetch_repo
from repo_expert.ingestion.markdown import chunk_repo_markdown
from repo_expert.ingestion.models import Chunk
from repo_expert.ingestion.qdrant_collections import create_collections
from repo_expert.ingestion.qdrant_upload import upsert_chunks

logger = logging.getLogger(__name__)


def ingest(cfg: InstanceConfig | None = None) -> dict[str, int]:
    """Run the full ingestion pipeline for the active instance.

    Returns a summary of chunk counts per collection.
    """
    cfg = cfg or get_instance_config()
    logger.info("Ingesting instance %s", cfg.name)

    create_collections(cfg)

    docs: list[Chunk] = []
    code: list[Chunk] = []
    for repo in cfg.target_repos:
        root = fetch_repo(repo)
        docs.extend(chunk_repo_markdown(root, repo, cfg))
        code.extend(chunk_repo_code(root, repo, cfg))
    logger.info("Chunked %d docs, %d code symbols", len(docs), len(code))

    n_docs = upsert_chunks(cfg.docs_index, docs)
    n_code = upsert_chunks(cfg.code_index, code)
    summary = {cfg.docs_index: n_docs, cfg.code_index: n_code}

    # Career KB source (portfolio): a local markdown file upserted into source3_index.
    career = chunk_career_doc(cfg)
    if career and cfg.source3_index:
        summary[cfg.source3_index] = upsert_chunks(cfg.source3_index, career)
        logger.info("Chunked %d career entries", len(career))

    logger.info("Ingestion complete: %s", summary)
    return summary
