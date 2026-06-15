"""Smoke tests for instance config selection (config-driven switching)."""

import pytest

from repo_expert.config.instance import (
    Source3Kind,
    get_instance_config,
)


@pytest.mark.parametrize("name", ["public", "portfolio"])
def test_instance_loads_with_required_fields(name: str) -> None:
    cfg = get_instance_config(name)
    assert cfg.name == name
    assert cfg.target_repos, "must target at least one repo"
    assert cfg.primary_repo.slug.count("/") == 1
    assert cfg.docs_index and cfg.code_index
    assert isinstance(cfg.source3, Source3Kind)


def test_source3_differs_between_instances() -> None:
    assert get_instance_config("public").source3 is Source3Kind.ISSUES
    assert get_instance_config("portfolio").source3 is Source3Kind.CAREER_KB


def test_career_kb_instance_has_index_issues_instance_does_not() -> None:
    assert get_instance_config("public").source3_index is None
    assert get_instance_config("portfolio").source3_index is not None


def test_unknown_instance_raises_with_valid_options() -> None:
    with pytest.raises(ValueError, match="Valid options"):
        get_instance_config("bogus")
