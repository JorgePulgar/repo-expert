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
    # Unused on the Qdrant stack (embeddings run server-side in Qdrant); required only
    # by the legacy Azure AI Search embedding path. Optional so the app starts without it.
    azure_openai_embed_deployment: str | None = Field(
        None, alias="AZURE_OPENAI_EMBED_DEPLOYMENT"
    )

    # --- Azure AI Search ---
    azure_search_endpoint: str = Field(..., alias="AZURE_SEARCH_ENDPOINT")
    azure_search_api_key: str = Field(..., alias="AZURE_SEARCH_API_KEY")

    # --- Qdrant (retrieval backend; optional until the migration lands) ---
    qdrant_url: str | None = Field(None, alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(None, alias="QDRANT_API_KEY")
    # mxbai-embed-large-v1 is blocked on the Qdrant free tier (P7-T2 gate, 2026-06-17);
    # MiniLM (384-dim) is the pre-authorized fallback served free via cloud inference.
    qdrant_embed_model: str = Field(
        "sentence-transformers/all-MiniLM-L6-v2", alias="QDRANT_EMBED_MODEL"
    )

    # --- GitHub (optional; required only by the issues/PRs retriever) ---
    github_token: str | None = Field(None, alias="GITHUB_TOKEN")

    # --- App ---
    instance: str = Field("public", alias="REPO_EXPERT_INSTANCE")
    # Comma-separated list of frontend origins allowed to call the API (CORS).
    # "*" allows any origin — the default until the site domain is known; tighten
    # to the Hostinger domain once the widget ships (Phase 8).
    cors_origins: str = Field("*", alias="CORS_ORIGINS")

    @property
    def cors_origin_list(self) -> list[str]:
        """``cors_origins`` split into a clean list for the CORS middleware."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the cached :class:`Settings`, loaded once per process."""
    return Settings()  # type: ignore[call-arg]
