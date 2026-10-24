"""Retry rate limits and transient errors from LLM providers, with exponential backoff."""

from __future__ import annotations

import random
import time
from collections.abc import Callable

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}


class LLMUnavailable(RuntimeError):
    """A provider kept failing after every retry (for example the free-tier quota is spent)."""


def _status(exc: BaseException) -> int | None:
    for attr in ("status_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    return None


def _retry_after(exc: BaseException) -> float | None:
    headers = getattr(getattr(exc, "response", None), "headers", None) or {}
    try:
        return float(headers.get("retry-after"))
    except (TypeError, ValueError):
        return None


def is_retryable(exc: BaseException) -> bool:
    status = _status(exc)
    if status is not None:
        return status in RETRYABLE_STATUS
    return type(exc).__name__.endswith(("ConnectionError", "TimeoutError", "Timeout"))


def with_retries[T](
    fn: Callable[[], T],
    *,
    attempts: int = 6,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:
            if not is_retryable(exc):
                raise
            if attempt == attempts - 1:
                raise LLMUnavailable(f"gave up after {attempts} attempts: {exc}") from exc
            delay = _retry_after(exc) or min(max_delay, base_delay * 2**attempt)
            sleep(delay * random.uniform(0.9, 1.1))
    raise AssertionError("unreachable")
