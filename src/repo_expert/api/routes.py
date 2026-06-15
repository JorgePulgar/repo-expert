"""API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from repo_expert.agent.agent import ask
from repo_expert.api.schemas import AskRequest, AskResponse
from repo_expert.clients import get_search_client
from repo_expert.config.instance import get_instance_config

logger = logging.getLogger(__name__)

router = APIRouter()


def _index_count(index_name: str) -> int | None:
    try:
        return get_search_client(index_name).get_document_count()
    except Exception as exc:  # noqa: BLE001 - health must not raise
        logger.warning("Index %s unreachable: %s", index_name, exc)
        return None


@router.get("/health")
def health() -> dict:
    """Liveness + which instance/indexes are active and populated."""
    cfg = get_instance_config()
    indexes = {
        cfg.docs_index: _index_count(cfg.docs_index),
        cfg.code_index: _index_count(cfg.code_index),
    }
    healthy = all(c is not None for c in indexes.values())
    return {
        "status": "ok" if healthy else "degraded",
        "instance": cfg.name,
        "repo": cfg.primary_repo.slug,
        "indexes": indexes,
    }


@router.post("/ask", response_model=AskResponse)
def ask_endpoint(request: AskRequest) -> AskResponse:
    """Answer a question about the active instance's repo, with citations."""
    result = ask(request.question)
    return AskResponse(**result.model_dump())
