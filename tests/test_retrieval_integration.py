"""Live retrieval integration tests (run with: uv run pytest -m integration)."""

import pytest

from repo_expert.retrieval.issues import retrieve_issues
from repo_expert.retrieval.kb import retrieve_kb

pytestmark = pytest.mark.integration


def test_kb_returns_code_symbol_for_depends() -> None:
    results = retrieve_kb("What does Depends do in the code?", top=5)
    assert results
    assert any(r.kind == "code" and "Depends" in r.citation.title for r in results)
    # code citations carry file/line
    code = next(r for r in results if r.kind == "code")
    assert code.citation.file_path and code.citation.start_line


def test_kb_returns_docs_for_query_params() -> None:
    results = retrieve_kb("How do I declare query parameters?", top=5)
    assert results
    assert any(r.kind == "docs" and "query" in r.citation.title.lower() for r in results)


def test_issues_returns_results_with_urls() -> None:
    results = retrieve_issues("dependency injection", top=3)
    assert results
    assert all(r.source == "issues" and r.citation.url.startswith("http") for r in results)
