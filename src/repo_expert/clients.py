"""Constructors for Azure SDK clients, wired from settings."""

from __future__ import annotations

from functools import lru_cache

from openai import AzureOpenAI

from repo_expert.config.settings import get_settings


@lru_cache
def get_openai_client() -> AzureOpenAI:
    """Cached Azure OpenAI client."""
    s = get_settings()
    return AzureOpenAI(
        azure_endpoint=s.azure_openai_endpoint,
        api_key=s.azure_openai_api_key,
        api_version=s.azure_openai_api_version,
    )
