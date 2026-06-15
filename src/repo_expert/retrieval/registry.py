"""Source registry: resolve the active retrievers from instance config.

The knowledge base retriever is always available. The live GitHub issues retriever
is added only when the instance's third source is ``issues`` (public instance). In
the portfolio instance the career KB is folded into the knowledge base (Phase 6), so
no separate retriever is registered here.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

from repo_expert.config.instance import InstanceConfig, Source3Kind, get_instance_config
from repo_expert.retrieval.issues import retrieve_issues
from repo_expert.retrieval.kb import retrieve_kb
from repo_expert.retrieval.models import RetrievalResult

Retriever = Callable[..., list[RetrievalResult]]


def get_retrievers(cfg: InstanceConfig | None = None) -> dict[str, Retriever]:
    """Return the active retrievers keyed by name, bound to the instance config."""
    cfg = cfg or get_instance_config()
    retrievers: dict[str, Retriever] = {"kb": partial(retrieve_kb, cfg=cfg)}
    if cfg.source3 is Source3Kind.ISSUES:
        retrievers["issues"] = partial(retrieve_issues, cfg=cfg)
    return retrievers


def available_sources(cfg: InstanceConfig | None = None) -> list[str]:
    """Names of the retrievers available for the active instance."""
    return list(get_retrievers(cfg))
