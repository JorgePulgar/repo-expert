"""Config-driven file discovery for ingestion (include/exclude globs)."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path


def discover_files(
    repo_root: Path, include_globs: list[str], exclude_globs: list[str]
) -> list[Path]:
    """Return files under ``repo_root`` matching include globs, minus excludes.

    Globs are repo-relative (e.g. ``docs/en/docs/**/*.md``). Result is sorted and
    de-duplicated for stable, reproducible ingestion.
    """
    included: set[Path] = set()
    for pattern in include_globs:
        included.update(p for p in repo_root.glob(pattern) if p.is_file())

    def excluded(p: Path) -> bool:
        rel = p.relative_to(repo_root).as_posix()
        return any(fnmatch(rel, pat) for pat in exclude_globs)

    return sorted(p for p in included if not excluded(p))
