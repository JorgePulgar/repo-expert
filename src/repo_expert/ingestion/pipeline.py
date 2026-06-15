"""End-to-end ingestion: fetch -> chunk -> embed -> upload -> (re)build KB."""

from __future__ import annotations

import logging

from repo_expert.config.instance import InstanceConfig, get_instance_config
from repo_expert.ingestion.career import chunk_career_doc
from repo_expert.ingestion.code import chunk_repo_code
from repo_expert.ingestion.embed import embed_chunks
from repo_expert.ingestion.fetch import fetch_repo
from repo_expert.ingestion.index import create_indexes
from repo_expert.ingestion.knowledge import create_knowledge_base, create_knowledge_sources
from repo_expert.ingestion.markdown import chunk_repo_markdown
from repo_expert.ingestion.models import Chunk
from repo_expert.ingestion.upload import upload_chunks

logger = logging.getLogger(__name__)


def ingest(cfg: InstanceConfig | None = None) -> dict[str, int]:
    """Run the full ingestion pipeline for the active instance.

    Returns a summary of chunk counts per index.
    """
    cfg = cfg or get_instance_config()
    logger.info("Ingesting instance %s", cfg.name)

    create_indexes(cfg)

    docs: list[Chunk] = []
    code: list[Chunk] = []
    for repo in cfg.target_repos:
        root = fetch_repo(repo)
        docs.extend(chunk_repo_markdown(root, repo, cfg))
        code.extend(chunk_repo_code(root, repo, cfg))
    logger.info("Chunked %d docs, %d code symbols", len(docs), len(code))

    embed_chunks(docs)
    embed_chunks(code)
    n_docs = upload_chunks(cfg.docs_index, docs)
    n_code = upload_chunks(cfg.code_index, code)
    summary = {cfg.docs_index: n_docs, cfg.code_index: n_code}

    # Career KB source (portfolio): a local markdown file indexed into source3_index.
    career = chunk_career_doc(cfg)
    if career and cfg.source3_index:
        embed_chunks(career)
        summary[cfg.source3_index] = upload_chunks(cfg.source3_index, career)
        logger.info("Chunked %d career entries", len(career))

    create_knowledge_sources(cfg)
    create_knowledge_base(cfg)

    logger.info("Ingestion complete: %s", summary)
    return summary
