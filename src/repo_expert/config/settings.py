"""Environment-backed application settings.

Loads secrets and runtime config from the process environment / `.env`.
Fails fast with a clear message naming any missing required variable.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All external configuration for the app.

    Required fields raise a ``ValidationError`` at load time when absent,
    naming the offending environment variable (fail-fast).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Azure OpenAI ---
    azure_openai_endpoint: str = Field(..., alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(..., alias="AZURE_OPENAI_API_KEY")
    azure_openai_api_version: str = Field(
        "2024-10-21", alias="AZURE_OPENAI_API_VERSION"
    )
    azure_openai_chat_deployment: str = Field(
        ..., alias="AZURE_OPENAI_CHAT_DEPLOYMENT"
    )
    azure_openai_embed_deployment: str = Field(
        ..., alias="AZURE_OPENAI_EMBED_DEPLOYMENT"
    )

    # --- Azure AI Search ---
    azure_search_endpoint: str = Field(..., alias="AZURE_SEARCH_ENDPOINT")
    azure_search_api_key: str = Field(..., alias="AZURE_SEARCH_API_KEY")

    # --- GitHub (optional; required only by the issues/PRs retriever) ---
    github_token: str | None = Field(None, alias="GITHUB_TOKEN")

    # --- App ---
    instance: str = Field("public", alias="REPO_EXPERT_INSTANCE")


@lru_cache
def get_settings() -> Settings:
    """Return the cached :class:`Settings`, loaded once per process."""
    return Settings()  # type: ignore[call-arg]
