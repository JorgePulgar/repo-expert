"""Code-aware chunker: one chunk per top-level function/class (Python AST).

Each chunk spans the symbol's full source (including decorators) and records
``start_line``/``end_line`` plus a GitHub line-anchored URL for citation. Symbol
granularity keeps "how is X implemented?" answers coherent.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

from repo_expert.config.instance import InstanceConfig, TargetRepo, get_instance_config
from repo_expert.ingestion.discovery import discover_files
from repo_expert.ingestion.markdown import _branch
from repo_expert.ingestion.models import Chunk, make_chunk_id

logger = logging.getLogger(__name__)

_DEF_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _symbol_span(node: ast.AST) -> tuple[int, int]:
    """1-based start (incl. decorators) and end line of a def/class node."""
    start = node.lineno  # type: ignore[attr-defined]
    decorators = getattr(node, "decorator_list", [])
    if decorators:
        start = min(start, min(d.lineno for d in decorators))
    end = getattr(node, "end_lineno", start) or start
    return start, end


def chunk_code_file(
    path: Path, repo_root: Path, repo: TargetRepo, branch: str
) -> list[Chunk]:
    """Chunk one Python file into one :class:`Chunk` per top-level symbol."""
    rel = path.relative_to(repo_root).as_posix()
    source = path.read_text(encoding="utf-8", errors="replace")
    lines = source.splitlines()
    try:
        tree = ast.parse(source, filename=rel)
    except SyntaxError:
        logger.warning("Skipping unparseable file %s", rel)
        return []

    base_url = f"https://github.com/{repo.slug}/blob/{branch}/{rel}"
    chunks: list[Chunk] = []
    for node in tree.body:
        if not isinstance(node, _DEF_TYPES):
            continue
        start, end = _symbol_span(node)
        content = "\n".join(lines[start - 1 : end]).strip()
        if not content:
            continue
        kind = "class" if isinstance(node, ast.ClassDef) else "function"
        anchor = f"L{start}-L{end}"
        chunks.append(
            Chunk(
                id=make_chunk_id(repo.slug, rel, anchor),
                repo_slug=repo.slug,
                source_kind="code",
                file_path=rel,
                title=f"{kind} {node.name}",
                content=content,
                url=f"{base_url}#{anchor}",
                section_path=[rel],
                start_line=start,
                end_line=end,
            )
        )
    return chunks


def chunk_repo_code(
    repo_root: Path, repo: TargetRepo, cfg: InstanceConfig | None = None
) -> list[Chunk]:
    """Chunk the Python files selected by the instance's ``code_globs``."""
    cfg = cfg or get_instance_config()
    branch = _branch(repo_root)
    files = discover_files(repo_root, cfg.code_globs, cfg.exclude_globs)
    chunks: list[Chunk] = []
    for f in files:
        chunks.extend(chunk_code_file(f, repo_root, repo, branch))
    return chunks
