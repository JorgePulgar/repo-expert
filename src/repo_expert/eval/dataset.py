"""Curated evaluation Q/A sets."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

_DATA_DIR = Path(__file__).parent


class QAItem(BaseModel):
    """One evaluation question and its expectations."""

    id: str
    question: str
    expected_sources: list[str]
    expected_kind: str | None = None
    # Lowercased substrings; a retrieval is "relevant" if one appears in a citation.
    must_include: list[str] = []


def load_qa(instance: str = "public") -> list[QAItem]:
    """Load the curated Q/A set for an instance (``qa_<instance>.json``)."""
    path = _DATA_DIR / f"qa_{instance}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return [QAItem(**item) for item in data]
