"""Chunk the Career Knowledge Base markdown into retrievable chunks.

The career doc is a local markdown file (not in a target repo). It is authored as
self-contained sections, so we reuse the heading-based markdown chunker and tag the
chunks as the ``career`` source kind.
"""

from __future__ import annotations

from repo_expert.config.instance import InstanceConfig, TargetRepo, get_instance_config
from repo_expert.ingestion.fetch import _PROJECT_ROOT
from repo_expert.ingestion.markdown import chunk_markdown_file
from repo_expert.ingestion.models import Chunk

# The career doc lives in this repo; cite it on the repo-expert blob.
_CAREER_REPO = TargetRepo(owner="JorgePulgar", name="repo-expert")


def chunk_career_doc(cfg: InstanceConfig | None = None) -> list[Chunk]:
    """Chunk the instance's career markdown; returns [] if none configured."""
    cfg = cfg or get_instance_config()
    if not cfg.career_doc:
        return []
    path = (_PROJECT_ROOT / cfg.career_doc).resolve()
    chunks = chunk_markdown_file(path, _PROJECT_ROOT, _CAREER_REPO, "main")
    for c in chunks:
        c.source_kind = "career"
    return chunks
