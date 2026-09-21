"""Tests for the query rewrite that feeds vector search."""

import pytest

from repo_expert.retrieval import rewrite
from repo_expert.retrieval.rewrite import needs_rewrite, rewrite_query


@pytest.fixture(autouse=True)
def _no_subject_lookup(monkeypatch):
    monkeypatch.setattr(rewrite, "_subject_hint", lambda: "Contexto: pruebas.")


# --- when to rewrite at all -----------------------------------------------------

def test_specific_questions_are_left_alone() -> None:
    """Rewriting these lost precision: the expansion matched tables of contents."""
    assert not needs_rewrite("Que proyectos ha construido Jorge?")
    assert not needs_rewrite("Que experiencia tiene Jorge con bases de datos vectoriales?")


def test_short_questions_are_rewritten() -> None:
    assert needs_rewrite("Que es RAG?")


def test_unfamiliar_acronyms_trigger_a_rewrite() -> None:
    assert needs_rewrite("Tiene algun proyecto relacionado con ML?")


def test_well_known_acronyms_do_not() -> None:
    """PDF already embeds near its topic; expanding it only adds noise."""
    assert not needs_rewrite("Como funciona el parser de PDF del proyecto de licitaciones?")


def test_every_question_in_a_conversation_is_rewritten() -> None:
    """Cue-word detection missed real follow-ups, so history alone is the trigger."""
    assert needs_rewrite("explicame mas del primero", [("q", "a")])
    # No cue word, long enough to look self-contained - and yet it depends
    # entirely on the previous turn. This one returned "no lo sé" in testing.
    assert needs_rewrite("¿Y cuál de ellos fue para un cliente?", [("q", "a")])
    # Even a self-contained question is rewritten inside a conversation; the cost
    # is one cheap call and the rewrite comes back close to unchanged.
    assert needs_rewrite("Que experiencia tiene Jorge con bases de datos?", [("q", "a")])


# --- how the rewrite is handled -------------------------------------------------

def test_preamble_is_stripped(monkeypatch) -> None:
    monkeypatch.setattr(
        rewrite, "chat",
        lambda *a, **k: '"¿Qué experiencia tiene Jorge con machine learning?"',
    )
    out = rewrite_query("Tiene proyectos de ML?")
    assert out == "¿Qué experiencia tiene Jorge con machine learning?"


def test_multiline_answer_keeps_the_first_usable_line(monkeypatch) -> None:
    monkeypatch.setattr(
        rewrite, "chat",
        lambda *a, **k: "- ¿Qué proyectos de machine learning tiene Jorge?\n- otra cosa",
    )
    assert rewrite_query("proyectos de ML?") == "¿Qué proyectos de machine learning tiene Jorge?"


def test_overlong_rewrite_is_trimmed_not_discarded(monkeypatch) -> None:
    monkeypatch.setattr(rewrite, "chat", lambda *a, **k: "palabra " * 200)
    out = rewrite_query("Que es RAG?")
    assert 0 < len(out) <= rewrite._MAX_QUERY_CHARS
    assert not out.endswith(" ")


def test_llm_failure_falls_back_to_the_question(monkeypatch) -> None:
    def _boom(*a, **k):
        raise RuntimeError("upstream down")

    monkeypatch.setattr(rewrite, "chat", _boom)
    assert rewrite_query("Que es RAG?") == "Que es RAG?"


def test_truncated_rewrite_falls_back(monkeypatch) -> None:
    """A rewrite far shorter than the question has probably lost the subject."""
    monkeypatch.setattr(rewrite, "chat", lambda *a, **k: "RAG")
    question = "Que experiencia con RAG tiene?"
    assert rewrite_query(question) == question


def test_empty_question_is_returned_unchanged() -> None:
    assert rewrite_query("") == ""
