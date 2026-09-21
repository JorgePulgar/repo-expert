"""Tests for splitting oversized markdown sections.

The embedding model truncates at ~256 tokens without warning, so a section longer
than the budget used to be indexed only up to the cut. These tests pin the
invariants that keep the tail searchable.
"""

from pathlib import Path

from repo_expert.config.instance import TargetRepo
from repo_expert.ingestion.markdown import _MAX_CHARS, _split_long_text, chunk_markdown_file

REPO = TargetRepo(owner="JorgePulgar", name="repo-expert")


def test_short_text_is_not_split() -> None:
    assert _split_long_text("una frase corta") == ["una frase corta"]


def test_every_piece_respects_the_budget() -> None:
    para = ("Frase de relleno con longitud razonable. " * 60).strip()
    pieces = _split_long_text(para)
    assert len(pieces) > 1
    assert all(len(p) <= _MAX_CHARS for p in pieces)


def test_split_does_not_cut_mid_sentence() -> None:
    para = ("Alfa uno dos tres. " * 80).strip()
    for piece in _split_long_text(para):
        assert not piece.endswith("Alfa uno dos"), "piece ends mid-sentence"


def test_oversized_unit_without_punctuation_still_fits() -> None:
    """List items and table rows often carry no sentence punctuation."""
    row = "palabra " * 500
    assert all(len(p) <= _MAX_CHARS for p in _split_long_text(row))


def test_no_content_is_lost() -> None:
    para = ("Contenido importante que no debe perderse. " * 40).strip()
    joined = " ".join(_split_long_text(para)).replace("\n\n", " ")
    assert "Contenido importante" in joined
    assert len(joined.split()) == len(para.split())


def test_long_section_becomes_several_chunks_each_keeping_the_heading(tmp_path: Path) -> None:
    doc = tmp_path / "career.md"
    body = "Detalle del proyecto con suficiente texto. " * 80
    doc.write_text(f"# Proyectos\n\n{body}\n", encoding="utf-8")

    chunks = chunk_markdown_file(doc, tmp_path, REPO, "main")

    assert len(chunks) > 1, "an oversized section must split"
    assert all(c.content.startswith("Proyectos") for c in chunks)
    assert all(len(c.content) <= _MAX_CHARS for c in chunks)
    # Every piece cites the same section anchor, so a reader lands on the section.
    assert len({c.url for c in chunks}) == 1
    # Ids stay unique so the upsert does not collapse the pieces into one point.
    assert len({c.id for c in chunks}) == len(chunks)
    # Reading order is recorded for neighbour expansion.
    assert [c.seq for c in chunks] == list(range(len(chunks)))
