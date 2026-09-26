"""Thin Azure OpenAI chat helper for the agent nodes."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from repo_expert.clients import get_openai_client
from repo_expert.config.settings import get_settings


_MAX_HISTORY_TURNS = 6
_MAX_HISTORY_ANSWER_CHARS = 1200


def _request(
    system: str,
    user: str,
    *,
    json_mode: bool = False,
    temperature: float | None = None,
    history: list[tuple[str, str]] | None = None,
    reasoning_effort: str | None = None,
) -> dict[str, Any]:
    """Build the chat-completions arguments shared by ``chat`` and ``chat_stream``."""
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for past_question, past_answer in (history or [])[-_MAX_HISTORY_TURNS:]:
        if not past_question:
            continue
        messages.append({"role": "user", "content": past_question})
        messages.append(
            {"role": "assistant", "content": (past_answer or "")[:_MAX_HISTORY_ANSWER_CHARS]}
        )
    messages.append({"role": "user", "content": user})
    kwargs: dict[str, Any] = {
        "model": get_settings().azure_openai_chat_deployment,
        "messages": messages,
    }
    # gpt-5-family deployments reject every temperature but the default:
    # "Only the default (1) value is supported". Send it only when a caller
    # explicitly asks, so older deployments can still pin it to 0.
    if temperature is not None:
        kwargs["temperature"] = temperature
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if reasoning_effort:
        kwargs["reasoning_effort"] = reasoning_effort
    return kwargs


def chat(
    system: str,
    user: str,
    *,
    json_mode: bool = False,
    temperature: float | None = None,
    history: list[tuple[str, str]] | None = None,
    reasoning_effort: str | None = None,
) -> str:
    """Chat completion; returns the assistant message text.

    ``history`` is the prior ``(question, answer)`` turns, oldest first. They are
    replayed as real chat turns between the system prompt and the current message,
    so the model can resolve follow-ups ("explain the first one") instead of
    treating every question as the start of a conversation. Only the last few turns
    are kept, and past answers are trimmed, so a long conversation cannot crowd out
    the retrieved sources.

    ``reasoning_effort`` is passed through to gpt-5-family deployments; None leaves
    the deployment default ("medium"). It is set per call, not globally: the eval
    judge also calls this helper and must keep the effort it was measured at.
    """
    kwargs = _request(
        system, user, json_mode=json_mode, temperature=temperature,
        history=history, reasoning_effort=reasoning_effort,
    )
    resp = get_openai_client().chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def chat_stream(
    system: str,
    user: str,
    *,
    history: list[tuple[str, str]] | None = None,
    reasoning_effort: str | None = None,
) -> Iterator[str]:
    """Like ``chat``, but yield the answer text piece by piece as the model writes it.

    Same request, same tokens: only the delivery changes. gpt-5-family models reason
    before writing, so the first piece arrives after the reasoning, not instantly.
    """
    kwargs = _request(system, user, history=history, reasoning_effort=reasoning_effort)
    stream = get_openai_client().chat.completions.create(**kwargs, stream=True)
    for chunk in stream:
        # Azure sends a first chunk with no choices (content-filter annotations).
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def chat_json(
    system: str,
    user: str,
    temperature: float | None = None,
    reasoning_effort: str | None = None,
) -> dict:
    """Chat completion parsed as JSON; returns {} on parse failure."""
    raw = chat(
        system, user, json_mode=True, temperature=temperature,
        reasoning_effort=reasoning_effort,
    )
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
