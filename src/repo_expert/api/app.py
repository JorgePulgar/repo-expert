"""FastAPI application factory."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from repo_expert.api.routes import router
from repo_expert.config.instance import get_instance_config
from repo_expert.config.settings import get_settings

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
    app.include_router(router)

    # Allow the chat widget's origin(s) to call /ask from the browser. Config-driven
    # via CORS_ORIGINS; defaults to "*" until the Hostinger domain is set (Phase 8).
    origins = get_settings().cors_origin_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %d (%.0f ms)",
            request.method, request.url.path, response.status_code, elapsed_ms,
        )
        return response

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal error processing the request."},
        )

    return app


app = create_app()
