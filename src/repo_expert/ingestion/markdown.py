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


# The embedding model (MiniLM via Qdrant cloud inference) truncates its input at
# ~256 tokens and says nothing. A section longer than that was being indexed only
# up to the cut, so the tail was unsearchable: before this, 12 of the 22 career
# sections (55%) overflowed, the largest at ~1200 tokens. Sections are therefore
# split into pieces that fit, each carrying the heading so the embedding keeps its
# topic and the citation keeps its context.
_MAX_CHARS = 900          # ~230 tokens of Spanish/English prose, under the cap
_MIN_TAIL_CHARS = 200     # avoid orphan slivers; merge them into the previous piece

# Split on paragraph breaks first, then sentence ends — never mid-sentence.
_PARA_BREAK = re.compile(r"\n\s*\n")
_SENTENCE_END = re.compile(r"(?<=[.!?:;])\s+")


def _split_on_words(text: str, max_chars: int) -> list[str]:
    """Last-resort split of an oversized unit at word boundaries."""
    if len(text) <= max_chars:
        return [text]
    out: list[str] = []
    current = ""
    for word in text.split(" "):
        candidate = f"{current} {word}".strip() if current else word
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            out.append(current)
            current = word
    if current:
        out.append(current)
    return out


def _split_long_text(text: str, max_chars: int = _MAX_CHARS) -> list[str]:
    """Split ``text`` into pieces of at most ``max_chars``, on natural boundaries.

    Paragraphs are kept whole when they fit; oversized paragraphs fall back to
    sentence boundaries, and a single sentence longer than the budget is emitted
    as-is rather than cut mid-word (rare, and better than a broken fragment).
    """
    if len(text) <= max_chars:
        return [text]

    units: list[str] = []
    for para in _PARA_BREAK.split(text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= max_chars:
            units.append(para)
            continue
        sentence = ""
        for part in _SENTENCE_END.split(para):
            # Markdown list items and table rows often carry no sentence punctuation,
            # so a "sentence" can still blow the budget. Fall back to word boundaries
            # rather than let the embedder truncate it silently.
            for part in _split_on_words(part, max_chars):
                candidate = f"{sentence} {part}".strip() if sentence else part
                if len(candidate) <= max_chars:
                    sentence = candidate
                else:
                    if sentence:
                        units.append(sentence)
                    sentence = part
        if sentence:
            units.append(sentence)

    # Pack units back up to the budget so we emit as few pieces as possible.
    pieces: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n\n{unit}" if current else unit
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                pieces.append(current)
            current = unit
    if current:
        merged = f"{pieces[-1]}\n\n{current}" if pieces else ""
        # Absorb an orphan tail into the previous piece, but only when the result
        # still fits — otherwise the merge is what pushes the chunk over the cap.
        if pieces and len(current) < _MIN_TAIL_CHARS and len(merged) <= max_chars:
            pieces[-1] = merged
        else:
            pieces.append(current)
    return pieces or [text]




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
    seen_anchors: dict[str, int] = {}  # de-dup repeated heading slugs per file

    def flush() -> None:
        nonlocal idx
        text = "\n".join(body).strip()
        if not text and not cur_title:
            return
        base = _section_anchor(cur_path, cur_title, idx)
        # GitHub-style disambiguation: first "slug", then "slug-1", "slug-2", ...
        count = seen_anchors.get(base, 0)
        anchor = base if count == 0 else f"{base}-{count}"
        seen_anchors[base] = count + 1
        # A section longer than the embedding window becomes several chunks. Each
        # repeats the heading, so every piece embeds on-topic and cites in context.
        # The heading is prepended afterwards, so it has to come out of the budget.
        heading_cost = len(cur_title) + 2 if cur_title else 0
        pieces = _split_long_text(text, max(_MAX_CHARS - heading_cost, 200))
        for part_no, piece in enumerate(pieces):
            content = (f"{cur_title}\n\n{piece}" if cur_title else piece).strip()
            part_anchor = anchor if part_no == 0 else f"{anchor}--p{part_no}"
            chunks.append(
                Chunk(
                    id=make_chunk_id(repo.slug, rel, part_anchor),
                    repo_slug=repo.slug,
                    source_kind="docs",
                    file_path=rel,
                    title=cur_title or rel,
                    content=content,
                    # The URL keeps the section anchor: every piece of a section
                    # points a reader at that section, not at a synthetic fragment.
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
    kept = [c for c in chunks if c.content]
    # Reading-order ordinal within the file, for neighbour expansion at query time.
    for i, chunk in enumerate(kept):
        chunk.seq = i
    return kept


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
