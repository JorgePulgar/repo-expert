"""Markdown chunker: split by heading hierarchy, one chunk per section.

Each chunk keeps its heading title, the ancestor heading path, the repo-relative
file path, and a GitHub blob URL (with heading anchor) for citation.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from repo_expert.config.instance import InstanceConfig, TargetRepo, get_instance_config
from repo_expert.ingestion.discovery import discover_files
from repo_expert.ingestion.models import Chunk, make_chunk_id

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")


def _slugify(text: str) -> str:
    """GitHub-style heading anchor."""
    s = text.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"\s+", "-", s)


def _branch(repo_root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root, check=True, capture_output=True, text=True,
        )
        ref = out.stdout.strip()
        return ref if ref and ref != "HEAD" else "HEAD"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "HEAD"


def _section_anchor(section_path: list[str], title: str, index: int) -> str:
    if title:
        return _slugify(title)
    return f"intro-{index}"




def chunk_markdown_file(
    path: Path, repo_root: Path, repo: TargetRepo, branch: str
) -> list[Chunk]:
    """Chunk one markdown file into one :class:`Chunk` per heading section."""
    rel = path.relative_to(repo_root).as_posix()
    base_url = f"https://github.com/{repo.slug}/blob/{branch}/{rel}"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    chunks: list[Chunk] = []
    stack: list[tuple[int, str]] = []  # (level, title) ancestors
    cur_title = ""
    cur_path: list[str] = []
    body: list[str] = []
    in_fence = False
    idx = 0

    def flush() -> None:
        nonlocal idx
        text = "\n".join(body).strip()
        if not text and not cur_title:
            return
        anchor = _section_anchor(cur_path, cur_title, idx)
        content = (f"{cur_title}\n\n{text}" if cur_title else text).strip()
        chunks.append(
            Chunk(
                id=make_chunk_id(repo.slug, rel, anchor),
                repo_slug=repo.slug,
                source_kind="docs",
                file_path=rel,
                title=cur_title or rel,
                content=content,
                url=f"{base_url}#{anchor}" if cur_title else base_url,
                section_path=list(cur_path),
            )
        )
        idx += 1

    for line in lines:
        if _FENCE.match(line):
            in_fence = not in_fence
            body.append(line)
            continue
        m = None if in_fence else _HEADING.match(line)
        if m:
            flush()
            level = len(m.group(1))
            title = m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            cur_path = [t for _, t in stack]
            stack.append((level, title))
            cur_title = title
            body = []
        else:
            body.append(line)
    flush()
    return [c for c in chunks if c.content]


def chunk_repo_markdown(
    repo_root: Path, repo: TargetRepo, cfg: InstanceConfig | None = None
) -> list[Chunk]:
    """Chunk the markdown files selected by the instance's ``docs_globs``."""
    cfg = cfg or get_instance_config()
    branch = _branch(repo_root)
    files = discover_files(repo_root, cfg.docs_globs, cfg.exclude_globs)
    chunks: list[Chunk] = []
    for f in files:
        chunks.extend(chunk_markdown_file(f, repo_root, repo, branch))
    return chunks
