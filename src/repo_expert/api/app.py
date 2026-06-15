"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from repo_expert.config.instance import get_instance_config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    cfg = get_instance_config()
    logger.info(
        "Repo Expert API starting | instance=%s | repo=%s | sources: docs=%s code=%s",
        cfg.name, cfg.primary_repo.slug, cfg.docs_index, cfg.code_index,
    )
    yield


def create_app() -> FastAPI:
    """Build the FastAPI app for the active instance."""
    cfg = get_instance_config()
    app = FastAPI(
        title="Repo Expert",
        description=f"Agentic RAG over {cfg.primary_repo.slug} ({cfg.name} instance).",
        version="0.1.0",
        lifespan=_lifespan,
    )
    return app


app = create_app()
