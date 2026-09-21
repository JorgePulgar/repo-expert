"""Per-IP rate limiting for the public ``/ask`` endpoint.

``/ask`` is an unauthenticated endpoint that spends money on every call (one LLM
round trip for routing, one for generation, one for the grounding judge), so it is
the one surface worth protecting. CORS does **not** protect it: CORS is enforced by
browsers, and a script calling the endpoint directly never asks a browser's
permission.

The window is a simple in-memory sliding log, which is correct for this deployment
because the app runs at most one replica (``--max-replicas 1``). If it is ever
scaled out, each replica would keep its own counter and the effective limit becomes
``limit * replicas`` — move the state to Redis or the ingress at that point.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from repo_expert.config.settings import get_settings

logger = logging.getLogger(__name__)

_WINDOW_SECONDS = 3600

# client ip -> timestamps of its accepted requests inside the window
_hits: defaultdict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def client_ip(request: Request) -> str:
    """Best-effort client IP behind the Container Apps ingress.

    The ingress appends the peer address to ``X-Forwarded-For``, so the **rightmost**
    entry is the one it observed and the only one a caller cannot forge by sending
    its own header. Falls back to the socket address when the header is absent
    (local runs, tests).
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    parts = [p.strip() for p in forwarded.split(",") if p.strip()]
    if parts:
        # Strip the :port the ingress may attach (IPv4 only; IPv6 is bracketed).
        candidate = parts[-1]
        if candidate.count(":") == 1:
            candidate = candidate.split(":")[0]
        return candidate
    return request.client.host if request.client else "unknown"


def _prune(bucket: deque[float], now: float) -> None:
    while bucket and now - bucket[0] >= _WINDOW_SECONDS:
        bucket.popleft()


def enforce_rate_limit(request: Request) -> None:
    """FastAPI dependency: raise ``429`` when the caller is over its hourly budget.

    Rejects *before* any LLM call, so a throttled request costs nothing.
    """
    limit = get_settings().rate_limit_per_hour
    if limit <= 0:  # 0 disables the limiter (local development)
        return

    ip = client_ip(request)
    now = time.monotonic()

    with _lock:
        bucket = _hits[ip]
        _prune(bucket, now)
        if len(bucket) >= limit:
            retry_after = int(_WINDOW_SECONDS - (now - bucket[0])) + 1
            logger.warning("Rate limit hit by %s (%d/%d)", ip, len(bucket), limit)
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded: {limit} questions per hour. "
                    f"Try again in {retry_after // 60 + 1} minute(s)."
                ),
                headers={"Retry-After": str(retry_after)},
            )
        bucket.append(now)


def reset_rate_limit() -> None:
    """Clear all buckets. Test helper."""
    with _lock:
        _hits.clear()
