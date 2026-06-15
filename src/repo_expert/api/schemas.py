"""Request/response schemas for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from repo_expert.retrieval.models import Citation


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    route: list[str]
    grounded: bool
    fallback_used: bool
