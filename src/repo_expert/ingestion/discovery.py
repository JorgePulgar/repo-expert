"""Config-driven file discovery for ingestion (include/exclude globs)."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path


def _matches(rel_path: str, pattern: str) -> bool:
    """Glob match with ``**/`` also matching at the repository root.

    ``fnmatch`` treats ``*`` as matching ``/`` as well, so ``**/tasks/**`` compiles
    to a pattern that *requires* a slash before ``tasks``: it excluded
    ``src/prompts/x.md`` but silently kept ``tasks/x.md`` at the root. That left
    1003 of 2885 doc chunks in the index that the config said to drop. Any
    ``**/``-prefixed pattern is therefore also tried without the prefix, which is
    what people mean by "anywhere, including here".
    """
    if fnmatch(rel_path, pattern):
        return True
    if pattern.startswith("**/"):
        return fnmatch(rel_path, pattern[3:])
    return False


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
        return any(_matches(rel, pat) for pat in exclude_globs)

    return sorted(p for p in included if not excluded(p))
