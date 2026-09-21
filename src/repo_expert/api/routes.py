"""API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from repo_expert.agent.agent import ask
from repo_expert.api.rate_limit import enforce_rate_limit
from repo_expert.api.schemas import AskRequest, AskResponse
from repo_expert.clients import get_qdrant_client
from repo_expert.config.instance import get_instance_config

logger = logging.getLogger(__name__)

router = APIRouter()


def _index_count(index_name: str) -> int | None:
    """Point count for a Qdrant collection, or None if it is unreachable."""
    try:
        return get_qdrant_client().count(collection_name=index_name, exact=True).count
    except Exception as exc:  # noqa: BLE001 - health must not raise
        logger.warning("Collection %s unreachable: %s", index_name, exc)
        return None


@router.get("/health")
def health() -> dict:
    """Liveness + which instance/collections are active and populated."""
    cfg = get_instance_config()
    indexes = {
        cfg.docs_index: _index_count(cfg.docs_index),
        cfg.code_index: _index_count(cfg.code_index),
    }
    # The portfolio instance's third source is a Qdrant collection; the public
    # instance queries GitHub issues live, so there is nothing to count.
    if cfg.source3_index:
        indexes[cfg.source3_index] = _index_count(cfg.source3_index)
    healthy = all(c is not None for c in indexes.values())
    return {
        "status": "ok" if healthy else "degraded",
        "instance": cfg.name,
        "repo": cfg.primary_repo.slug,
        "indexes": indexes,
    }


@router.post("/ask", response_model=AskResponse, dependencies=[Depends(enforce_rate_limit)])
def ask_endpoint(request: AskRequest) -> AskResponse:
    """Answer a question about the active instance's repo, with citations.

    Rate-limited per IP; `/health` deliberately is not, so the chat page can send a
    warm-up ping on load without spending part of a visitor's budget.
    """
    result = ask(request.question)
    return AskResponse(**result.model_dump())
