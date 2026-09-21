"""Rewrite a user question into a better vector-search query.

Two problems this solves, both observed in production:

1. **Short questions and acronyms retrieve badly.** "¿Tiene algún proyecto
   relacionado con ML?" returned "Education" and "Availability", while the same
   question spelled out ("machine learning ... modelo entrenamiento") returned the
   autoencoder and CNN projects from the same index. A 384-dim MiniLM embedding of
   three words carries little signal, and it does not know that "ML" and "machine
   learning" are the same thing.

2. **Follow-ups are not self-contained.** "explícame más del primero" has no
   retrievable content at all; the subject lives in the previous turn.

The live GitHub issues retriever already rewrites queries for the same reason
(``retrieval/issues.py``); this is the equivalent for the vector path, expanding
rather than reducing, because vector search rewards context where keyword search
punishes it.

Best-effort by design: any failure returns the original question, so retrieval
degrades to today's behaviour instead of breaking.
"""

from __future__ import annotations

import logging
import re

from repo_expert.agent.llm import chat

logger = logging.getLogger(__name__)

_MAX_HISTORY_TURNS = 3
_MAX_QUERY_CHARS = 400

# The rewrite must stay a *sentence*. An earlier version asked for synonyms and
# related terms, and the model produced keyword lists — which embed closest to
# tables of contents and indexes, not to prose. "¿Tiene algún proyecto de ML?"
# came back as a list of ML terms and retrieved "Tabla de contenidos" twice.
_SYSTEM = (
    "Reescribes la pregunta de un usuario como UNA sola pregunta en lenguaje "
    "natural, para buscarla en documentos sobre una persona y sus proyectos de "
    "software.\n"
    "Reglas:\n"
    "1. Mantén la forma de pregunta y un estilo natural. NUNCA devuelvas una lista "
    "de palabras clave ni términos separados por comas.\n"
    "2. Expande las siglas dentro de la frase: 'ML' -> 'machine learning', "
    "'RAG' -> 'retrieval augmented generation'. Puedes mencionar ambas formas si "
    "encaja de forma natural.\n"
    "3. Si la pregunta depende de la conversación previa ('el primero', 'ese "
    "proyecto', 'esto último', 'explícame más'), reescríbela nombrando "
    "explícitamente el sujeto para que se entienda por sí sola. Las referencias "
    "apuntan SIEMPRE a lo que dice el texto de la respuesta anterior, nunca a su "
    "lista de fuentes ni a nombres de ficheros o funciones citados al final.\n"
    "4. Máximo 25 palabras. No inventes datos que no estén en la pregunta o el "
    "historial.\n"
    "5. Responde SOLO con la pregunta reescrita, sin comillas ni explicaciones."
)


_REFERENCE_HINTS = (
    "primero", "segundo", "tercero", "anterior", "ese", "esa", "eso", "este",
    "esta", "esto", "más sobre", "mas sobre", "explícame más", "explicame mas",
    "amplía", "amplia", "y de", "the first", "that one", "more about",
)
_ACRONYM = re.compile(r"\b[A-Z]{2,5}\b")
# Acronyms common enough that the embedding already places them near their topic;
# expanding these buys nothing and costs precision.
_WELL_KNOWN_ACRONYMS = frozenset(
    {"PDF", "API", "HTTP", "HTML", "CSS", "SQL", "JSON", "CSV", "CV", "UI", "UX",
     "AWS", "GCP", "CI", "CD", "REST", "IA", "AI", "TFM", "URL", "SDK"}
)
# Below this, a question carries too little signal to embed well on its own.
# "¿Qué proyectos ha construido Jorge?" is five words and retrieves correctly —
# rewriting it made things worse — so the bar sits under it deliberately.
_MIN_WORDS_WITHOUT_HELP = 5


_OLDER_ANSWER_CHARS = 600
_LAST_ANSWER_CHARS = 2000


def _trim_answer(answer: str, is_last: bool) -> str:
    """Trim a past answer for the rewrite prompt, keeping what references need.

    References like "esto último" or "el último que has dicho" point at the *end*
    of the previous answer. Truncating from the front hid exactly that: asked
    "cuéntame más de esto último", the rewriter had only seen the opening of a long
    answer and resolved it against the last entry of the source list instead — so
    the chat explained a demo script nobody had asked about.

    The most recent answer therefore keeps its head *and* its tail; older turns,
    which are only there for context, keep a prefix.
    """
    answer = answer.strip()
    if not is_last:
        return answer[:_OLDER_ANSWER_CHARS]
    if len(answer) <= _LAST_ANSWER_CHARS:
        return answer
    half = _LAST_ANSWER_CHARS // 2
    return f"{answer[:half]}\n[...]\n{answer[-half:]}"


def _subject_hint() -> str:
    """One line telling the rewriter what the knowledge base is about."""
    try:
        from repo_expert.config.instance import get_instance_config

        cfg = get_instance_config()
        repos = ", ".join(r.name for r in cfg.target_repos[:8])
        if cfg.name == "portfolio":
            return (
                "Contexto: la base de conocimiento trata sobre Jorge Pulgar, "
                f"su carrera profesional y sus repositorios ({repos})."
            )
        return f"Contexto: la base de conocimiento cubre los repositorios {repos}."
    except Exception:  # noqa: BLE001 - context is a nicety, not a requirement
        return ""


def needs_rewrite(question: str, history: list[tuple[str, str]] | None = None) -> bool:
    """Whether rewriting is likely to help more than it hurts.

    Rewriting a question that is already specific tends to *lose* precision: the
    expansion reads like a keyword list, and keyword lists match tables of contents
    and indexes rather than prose. Measured on "¿Qué proyectos ha construido
    Jorge?", the rewrite pushed "Profile summary" out in favour of "Índice" and
    "Tabla de contenidos". So rewrite only where it earns its place:

    * a follow-up that refers to earlier turns and cannot be searched as written;
    * a very short question, which carries little signal on its own;
    * a question containing an acronym, which does not embed near its expansion.
    """
    text = (question or "").strip()
    if not text:
        return False
    # Inside a conversation, always rewrite. Trying to detect which follow-ups
    # depend on earlier turns by looking for cue words failed in testing: "¿Y cuál
    # de ellos fue para un cliente?" has no cue from the list, is long enough to
    # look self-contained, and was searched literally — so it missed the client
    # project it was asking about, and the next turn inherited the confusion.
    # A rewrite of an already-self-contained question costs one cheap call and
    # returns it close to unchanged.
    if history:
        return True
    if len(text.split()) < _MIN_WORDS_WITHOUT_HELP:
        return True
    return any(a not in _WELL_KNOWN_ACRONYMS for a in _ACRONYM.findall(text))


def rewrite_query(question: str, history: list[tuple[str, str]] | None = None) -> str:
    """Return an expanded, self-contained search query for ``question``.

    ``history`` is the recent ``(question, answer)`` turns, oldest first; only the
    last few are used, truncated, to keep the prompt small.
    """
    question = (question or "").strip()
    if not question:
        return question
    if not needs_rewrite(question, history):
        return question

    parts: list[str] = []
    # Name the subject: without it the model writes "esa persona", which embeds
    # further from documents that use the actual name.
    subject = _subject_hint()
    if subject:
        parts.append(subject)
    recent = (history or [])[-_MAX_HISTORY_TURNS:]
    for position, (past_q, past_a) in enumerate(recent):
        parts.append(f"Usuario: {past_q}")
        is_last = position == len(recent) - 1
        parts.append(f"Asistente: {_trim_answer(past_a or '', is_last)}")
    parts.append(f"Pregunta actual: {question}")

    try:
        rewritten = chat(_SYSTEM, "\n".join(parts)).strip()
    except Exception as exc:  # noqa: BLE001 - rewriting is best-effort
        logger.warning("Query rewrite failed (%s); using the original question", exc)
        return question

    if not rewritten:
        return question

    # The model often adds a preamble or bullet list despite the instructions, so
    # salvage the query instead of discarding the rewrite: keep the first non-empty
    # line, strip list/quote decoration, and trim to the budget at a word boundary.
    for line in rewritten.splitlines():
        line = line.strip().strip('"').lstrip("-*•").strip()
        if line and not line.lower().startswith(("consulta", "query", "respuesta")):
            rewritten = line
            break
    else:
        return question

    if len(rewritten) > _MAX_QUERY_CHARS:
        rewritten = rewritten[:_MAX_QUERY_CHARS].rsplit(" ", 1)[0]
    if len(rewritten) < len(question) / 2:
        # A rewrite shorter than the question has probably lost its subject.
        return question
    if rewritten != question:
        logger.info("Rewrote query: %r -> %r", question, rewritten)
    return rewritten
