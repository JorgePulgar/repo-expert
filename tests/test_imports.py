"""Sanity: the package and its submodules import."""

import importlib

import pytest

MODULES = [
    "repo_expert",
    "repo_expert.config",
    "repo_expert.config.settings",
    "repo_expert.config.instance",
    "repo_expert.ingestion",
    "repo_expert.retrieval",
    "repo_expert.agent",
    "repo_expert.api",
    "repo_expert.eval",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_imports(module: str) -> None:
    assert importlib.import_module(module) is not None
