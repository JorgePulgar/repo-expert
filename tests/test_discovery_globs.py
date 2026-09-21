"""Exclusion globs must work at the repository root, not only in subdirectories."""

from pathlib import Path

from repo_expert.ingestion.discovery import discover_files


def _tree(root: Path) -> None:
    for rel in [
        "README.md",
        "docs/guide.md",
        "tasks/phase-1.md",            # at the root — the case that used to leak
        "src/prompts/writer.md",       # nested — this one was excluded correctly
        "src/app/service.md",
    ]:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")


def test_double_star_prefix_also_matches_at_the_root(tmp_path: Path) -> None:
    _tree(tmp_path)

    found = discover_files(tmp_path, ["**/*.md"], ["**/tasks/**", "**/prompts/**"])
    rels = sorted(p.relative_to(tmp_path).as_posix() for p in found)

    assert rels == ["README.md", "docs/guide.md", "src/app/service.md"]


def test_nested_exclusions_still_work(tmp_path: Path) -> None:
    _tree(tmp_path)
    found = discover_files(tmp_path, ["**/*.md"], ["**/prompts/**"])
    rels = {p.relative_to(tmp_path).as_posix() for p in found}
    assert "src/prompts/writer.md" not in rels
    assert "tasks/phase-1.md" in rels


def test_plain_patterns_are_unaffected(tmp_path: Path) -> None:
    _tree(tmp_path)
    found = discover_files(tmp_path, ["**/*.md"], ["docs/*.md"])
    rels = {p.relative_to(tmp_path).as_posix() for p in found}
    assert "docs/guide.md" not in rels
    assert "README.md" in rels
