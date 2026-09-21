"""Unit tests for the Qdrant Cloud Inference embedding helpers (no network)."""

from qdrant_client import models

from repo_expert.ingestion.qdrant_collections import get_embedding_dim
from repo_expert.ingestion.qdrant_embed import as_document, as_query, embed_model


def test_default_model_is_multilingual() -> None:
    """English-only MiniLM could not serve Spanish questions over an English corpus."""
    assert embed_model() == "intfloat/multilingual-e5-small"


def test_default_model_dim_is_384() -> None:
    """e5-small keeps MiniLM's dimension, so collection schemas are unchanged."""
    assert get_embedding_dim() == 384


def test_stored_text_gets_the_passage_prefix() -> None:
    doc = as_document("hello world")
    assert isinstance(doc, models.Document)
    assert doc.text == "passage: hello world"
    assert doc.model == embed_model()


def test_searches_get_the_query_prefix() -> None:
    """e5 is trained asymmetrically; the wrong prefix measurably hurts retrieval."""
    assert as_query("hello world").text == "query: hello world"


def test_models_without_prefixes_are_left_alone(monkeypatch) -> None:
    monkeypatch.setenv("QDRANT_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    from repo_expert.config.settings import get_settings

    get_settings.cache_clear()
    try:
        assert as_document("hello").text == "hello"
        assert as_query("hello").text == "hello"
    finally:
        get_settings.cache_clear()
