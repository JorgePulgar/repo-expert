"""Unit tests for the Qdrant Cloud Inference embedding helpers (no network)."""

from qdrant_client import models

from repo_expert.ingestion.qdrant_collections import get_embedding_dim
from repo_expert.ingestion.qdrant_embed import as_document, embed_model


def test_default_model_is_minilm_free_tier_fallback() -> None:
    assert embed_model() == "sentence-transformers/all-MiniLM-L6-v2"


def test_default_model_dim_is_384() -> None:
    assert get_embedding_dim() == 384


def test_as_document_wraps_text_with_configured_model() -> None:
    doc = as_document("hello world")
    assert isinstance(doc, models.Document)
    assert doc.text == "hello world"
    assert doc.model == embed_model()
