"""Thin Azure OpenAI chat helper for the agent nodes."""

from __future__ import annotations

import json
from typing import Any

from repo_expert.clients import get_openai_client
from repo_expert.config.settings import get_settings


def chat(
    system: str, user: str, *, json_mode: bool = False, temperature: float | None = None
) -> str:
    """Single-turn chat completion; returns the assistant message text."""
    client = get_openai_client()
    deployment = get_settings().azure_openai_chat_deployment
    kwargs: dict[str, Any] = {
        "model": deployment,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
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
