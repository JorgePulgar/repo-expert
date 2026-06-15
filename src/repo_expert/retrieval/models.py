"""Unified retrieval result returned by every retriever (KB + live tools)."""

from __future__ import annotations

from pydantic import BaseModel


class Citation(BaseModel):
    """Where a result came from, for grounding the final answer."""

    title: str
    url: str
    file_path: str | None = None
    section_path: list[str] = []
    start_line: int | None = None
    end_line: int | None = None


class RetrievalResult(BaseModel):
    """One retrieved item from any source.

    ``source`` is the retriever ("kb" or "issues"); ``kind`` is the content type
    ("docs", "code", or "issue"). ``score`` is comparable only within a source.
    """

    source: str
    kind: str
    content: str
    citation: Citation
    score: float | None = None
