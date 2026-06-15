"""Offline unit tests for the source registry."""

from repo_expert.config.instance import get_instance_config
from repo_expert.retrieval.registry import available_sources


def test_public_has_kb_and_issues() -> None:
    assert available_sources(get_instance_config("public")) == ["kb", "issues"]


def test_portfolio_has_only_kb() -> None:
    assert available_sources(get_instance_config("portfolio")) == ["kb"]
