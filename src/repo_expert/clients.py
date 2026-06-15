"""Constructors for Azure SDK clients, wired from settings."""

from __future__ import annotations

from functools import lru_cache

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.knowledgebases import KnowledgeBaseRetrievalClient
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


@lru_cache
def get_search_index_client() -> SearchIndexClient:
    """Cached client for creating/managing AI Search indexes."""
    s = get_settings()
    return SearchIndexClient(s.azure_search_endpoint, AzureKeyCredential(s.azure_search_api_key))


def get_search_client(index_name: str) -> SearchClient:
    """Client for upload/query against a specific index."""
    s = get_settings()
    return SearchClient(
        s.azure_search_endpoint, index_name, AzureKeyCredential(s.azure_search_api_key)
    )


@lru_cache
def get_kb_retrieval_client(knowledge_base_name: str) -> KnowledgeBaseRetrievalClient:
    """Cached client for agentic retrieval against a knowledge base."""
    s = get_settings()
    return KnowledgeBaseRetrievalClient(
        s.azure_search_endpoint,
        AzureKeyCredential(s.azure_search_api_key),
        knowledge_base_name=knowledge_base_name,
    )
