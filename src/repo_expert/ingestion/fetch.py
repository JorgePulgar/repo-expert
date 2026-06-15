"""Fetch target repositories to local ``data/`` for ingestion.

Idempotent: clones a shallow copy on first run, fast-forward pulls thereafter.
Driven by the active instance config (no hard-coded repo).
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from repo_expert.config.instance import InstanceConfig, TargetRepo, get_instance_config

logger = logging.getLogger(__name__)

# Repo root = .../repo-expert ; data lives there (gitignored).
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_REPOS_DIR = _PROJECT_ROOT / "data" / "repos"


def repo_dir(repo: TargetRepo, base: Path | None = None) -> Path:
    """Local checkout path for ``repo`` (``data/repos/<owner>__<name>``)."""
    return (base or DATA_REPOS_DIR) / f"{repo.owner}__{repo.name}"


def _run_git(args: list[str], cwd: Path | None = None) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def fetch_repo(repo: TargetRepo, base: Path | None = None, depth: int = 1) -> Path:
    """Clone or fast-forward-pull ``repo`` into ``data/``; return its local path."""
    dest = repo_dir(repo, base)
    url = f"https://github.com/{repo.slug}.git"
    if (dest / ".git").is_dir():
        logger.info("Updating %s", repo.slug)
        _run_git(["pull", "--ff-only"], cwd=dest)
    else:
        logger.info("Cloning %s -> %s", repo.slug, dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        _run_git(["clone", "--depth", str(depth), url, str(dest)])
    return dest


def fetch_instance(cfg: InstanceConfig | None = None) -> list[Path]:
    """Fetch every target repo of the active (or given) instance config."""
    cfg = cfg or get_instance_config()
    return [fetch_repo(r) for r in cfg.target_repos]
