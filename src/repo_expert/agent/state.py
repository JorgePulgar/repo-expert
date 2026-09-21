"""LangGraph agent state."""

from __future__ import annotations

from typing import TypedDict

from repo_expert.retrieval.models import Citation, RetrievalResult


class AgentState(TypedDict, total=False):
    """Shared state threaded through the graph.

    ``route`` is the list of source names to query (e.g. ["kb"], ["issues"],
    ["kb", "issues"]). ``attempts`` counts corrective loops. ``grounded`` records
    whether the latest draft passed the grounding check. ``history`` carries the
    earlier turns so follow-ups ("explícame más del primero") can be resolved.
    """

    question: str
    # Prior (question, answer) turns, oldest first. The API is otherwise
    # stateless: the client sends the conversation back with each request.
    history: list[tuple[str, str]]
    route: list[str]
    results: list[RetrievalResult]
    draft: str
    grounded: bool
    attempts: int
    fallback_used: bool
    answer: str
    citations: list[Citation]
