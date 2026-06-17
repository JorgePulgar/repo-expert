"""Unit tests for Qdrant collection schema helpers (no live cluster needed)."""

import pytest

from repo_expert.config.instance import get_instance_config
from repo_expert.ingestion.qdrant_collections import (
    EMBED_DIMS,
    collection_names,
    get_embedding_dim,
)


def test_default_model_dim_is_mxbai_1024() -> None:
    assert get_embedding_dim("mixedbread-ai/mxbai-embed-large-v1") == 1024


def test_minilm_fallback_dim() -> None:
    assert get_embedding_dim("sentence-transformers/all-MiniLM-L6-v2") == 384


def test_unknown_model_raises_with_known_options() -> None:
    with pytest.raises(ValueError, match="Known models"):
        get_embedding_dim("bogus/model")


def test_default_model_is_known() -> None:
    # The configured default must have a dimension entry.
    assert get_embedding_dim() in EMBED_DIMS.values()


def test_public_has_two_collections_no_career() -> None:
    cfg = get_instance_config("public")
    names = collection_names(cfg)
    assert names == [cfg.docs_index, cfg.code_index]


def test_portfolio_has_career_collection() -> None:
    cfg = get_instance_config("portfolio")
    names = collection_names(cfg)
    assert names == [cfg.docs_index, cfg.code_index, cfg.source3_index]
    assert len(names) == 3
