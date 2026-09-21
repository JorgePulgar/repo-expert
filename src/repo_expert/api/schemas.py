"""Request/response schemas for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from repo_expert.retrieval.models import Citation


class Turn(BaseModel):
    """One earlier exchange in the same conversation."""

    question: str = Field(min_length=1, max_length=2000)
    answer: str = Field(default="", max_length=8000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    # The service stays stateless: the client sends the conversation back with each
    # request, so nothing is stored server-side and any replica can serve any turn.
    # Capped so a caller cannot use the history as an unbounded prompt channel.
    history: list[Turn] = Field(default_factory=list, max_length=10)


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    route: list[str]
    grounded: bool
    fallback_used: bool
