"""Shared ingestion data model: one chunk type for docs and code."""

from __future__ import annotations

import hashlib

from pydantic import BaseModel


class Chunk(BaseModel):
    """A retrievable unit with enough metadata to cite it.

    ``source_kind`` is ``"docs"`` or ``"code"``. Docs chunks carry a heading
    ``section_path``; code chunks carry ``start_line``/``end_line``.
    """

    id: str
    repo_slug: str
    source_kind: str
    file_path: str  # repo-relative, posix
    title: str
    content: str
    url: str
    section_path: list[str] = []
    start_line: int | None = None
    end_line: int | None = None


def make_chunk_id(repo_slug: str, file_path: str, anchor: str) -> str:
    """Stable id from repo + file + anchor (for upsert, not duplicate inserts)."""
    raw = f"{repo_slug}:{file_path}:{anchor}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()
