"""Typed instance configuration.

Core requirement: switching instance = changing config, not code. A single
:class:`InstanceConfig` selects the target repo(s), the AI Search index names,
and which "source 3" is active (GitHub issues vs Career Knowledge Base).
Everything downstream (ingestion, retrieval, agent) reads from this object and
stays instance-agnostic.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from repo_expert.config.settings import get_settings


class Source3Kind(StrEnum):
    """The heterogeneous third knowledge source, swapped per instance."""

    ISSUES = "issues"          # GitHub issues/PRs, queried live via API
    CAREER_KB = "career_kb"    # Career Knowledge Base, indexed in AI Search


class TargetRepo(BaseModel):
    """A GitHub repository to ingest/answer about."""

    owner: str
    name: str

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.name}"


class InstanceConfig(BaseModel):
    """All per-instance config. The only thing that differs between deployments."""

    name: str = Field(..., description="Instance id, e.g. 'public' or 'portfolio'.")
    description: str
    target_repos: list[TargetRepo] = Field(..., min_length=1)
    docs_index: str
    code_index: str
    source3: Source3Kind
    # Index name for source 3 when it is indexed (career_kb). None for live issues.
    source3_index: str | None = None

    @property
    def primary_repo(self) -> TargetRepo:
        return self.target_repos[0]


# --- The two instances ---------------------------------------------------------

PUBLIC = InstanceConfig(
    name="public",
    description="Class deliverable pointed at a serious public repo (FastAPI).",
    target_repos=[TargetRepo(owner="fastapi", name="fastapi")],
    docs_index="repo-expert-public-docs",
    code_index="repo-expert-public-code",
    source3=Source3Kind.ISSUES,
    source3_index=None,  # issues are queried live, not indexed
)

PORTFOLIO = InstanceConfig(
    name="portfolio",
    description="Recruiter demo pointed at Jorge's portfolio repos + Career KB.",
    # TODO(Phase 6): replace with the real portfolio repo list.
    target_repos=[TargetRepo(owner="JorgePulgar", name="repo-expert")],
    docs_index="repo-expert-portfolio-docs",
    code_index="repo-expert-portfolio-code",
    source3=Source3Kind.CAREER_KB,
    source3_index="repo-expert-portfolio-career",
)

_INSTANCES: dict[str, InstanceConfig] = {c.name: c for c in (PUBLIC, PORTFOLIO)}


def get_instance_config(name: str | None = None) -> InstanceConfig:
    """Return the active instance config.

    Resolves ``name`` (defaulting to ``REPO_EXPERT_INSTANCE`` from settings).
    Raises ``ValueError`` naming valid options when the instance is unknown.
    """
    resolved = (name or get_settings().instance).lower()
    try:
        return _INSTANCES[resolved]
    except KeyError:
        valid = ", ".join(sorted(_INSTANCES))
        raise ValueError(
            f"Unknown instance {resolved!r}. Valid options: {valid}."
        ) from None
