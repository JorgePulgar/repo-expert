"""Live GitHub issues/PRs retriever (outside the knowledge base).

Queries the GitHub Search API at request time so answers about "is this a known
bug / still open?" reflect current state. Not indexed.
"""

from __future__ import annotations

import logging

import httpx

from repo_expert.config.instance import InstanceConfig, get_instance_config
from repo_expert.config.settings import get_settings
from repo_expert.retrieval.models import Citation, RetrievalResult

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://api.github.com/search/issues"
_TIMEOUT = 15.0


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = get_settings().github_token
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def retrieve_issues(
    query: str,
    cfg: InstanceConfig | None = None,
    top: int = 10,
    state: str | None = None,
    item_type: str = "issue",
) -> list[RetrievalResult]:
    """Search issues/PRs of the instance's primary repo.

    ``item_type`` = ``issue`` or ``pull-request`` (GitHub now requires one).
    ``state`` = open|closed|None.
    """
    cfg = cfg or get_instance_config()
    repo = cfg.primary_repo
    q = f"repo:{repo.slug} is:{item_type} {query}"
    if state in ("open", "closed"):
        q += f" state:{state}"

    resp = httpx.get(
        _SEARCH_URL,
        params={"q": q, "per_page": top, "sort": "updated", "order": "desc"},
        headers=_headers(),
        timeout=_TIMEOUT,
    )
    if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
        raise RuntimeError("GitHub API rate limit exceeded (set GITHUB_TOKEN to raise it).")
    resp.raise_for_status()

    results: list[RetrievalResult] = []
    for item in resp.json().get("items", []):
        is_pr = "pull_request" in item
        body = (item.get("body") or "").strip()
        content = (
            f"[{'PR' if is_pr else 'issue'} #{item['number']} · {item['state']}] "
            f"{item['title']}\n\n{body[:1500]}"
        ).strip()
        results.append(
            RetrievalResult(
                source="issues",
                kind="issue",
                content=content,
                score=item.get("score"),
                citation=Citation(title=item["title"], url=item["html_url"]),
            )
        )
    return results
