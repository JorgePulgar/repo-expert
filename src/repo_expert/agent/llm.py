"""Thin Azure OpenAI chat helper for the agent nodes."""

from __future__ import annotations

import json
from typing import Any

from repo_expert.clients import get_openai_client
from repo_expert.config.settings import get_settings


_MAX_HISTORY_TURNS = 6
_MAX_HISTORY_ANSWER_CHARS = 1200


def chat(
    system: str,
    user: str,
    *,
    json_mode: bool = False,
    temperature: float | None = None,
    history: list[tuple[str, str]] | None = None,
) -> str:
    """Chat completion; returns the assistant message text.

    ``history`` is the prior ``(question, answer)`` turns, oldest first. They are
    replayed as real chat turns between the system prompt and the current message,
    so the model can resolve follow-ups ("explain the first one") instead of
    treating every question as the start of a conversation. Only the last few turns
    are kept, and past answers are trimmed, so a long conversation cannot crowd out
    the retrieved sources.
    """
    client = get_openai_client()
    deployment = get_settings().azure_openai_chat_deployment
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
        "model": deployment,
        "messages": messages,
    }
    # gpt-5-family deployments reject every temperature but the default:
    # "Only the default (1) value is supported". Send it only when a caller
    # explicitly asks, so older deployments can still pin it to 0.
    if temperature is not None:
        kwargs["temperature"] = temperature
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def chat_json(system: str, user: str, temperature: float | None = None) -> dict:
    """Chat completion parsed as JSON; returns {} on parse failure."""
    raw = chat(system, user, json_mode=True, temperature=temperature)
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
