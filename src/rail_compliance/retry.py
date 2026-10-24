"""Retry rate limits and transient errors from LLM providers, with exponential backoff."""

from __future__ import annotations

import random
import re
import time
from collections.abc import Callable

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}


class LLMUnavailable(RuntimeError):
    """A provider kept failing after every retry (for example the free-tier quota is spent)."""


def _chain(exc: BaseException):
    """The exception and what it was raised from. LangChain wraps provider errors, so the
    status code usually sits on the cause, not on the exception that reaches us."""
    seen: set[int] = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        yield exc
        exc = exc.__cause__ or exc.__context__


def _status(exc: BaseException) -> int | None:
    for e in _chain(exc):
        for attr in ("status_code", "code"):
            value = getattr(e, attr, None)
            if isinstance(value, int):
                return value
    return None


STATED_DELAY = re.compile(
    r"retry in (\d+(?:\.\d+)?)\s*s|retry[- ]after[^\d]{0,4}(\d+(?:\.\d+)?)", re.I
)


MAX_STATED_DELAY = 100.0  # a provider asking for longer than this is out of quota, not busy


def _retry_after(exc: BaseException) -> float | None:
    """The wait the provider asks for: a Retry-After header, or "Please retry in 11.8s"."""
    for e in _chain(exc):
        headers = getattr(getattr(e, "response", None), "headers", None) or {}
        try:
            return float(headers.get("retry-after"))
        except (TypeError, ValueError):
            pass
        match = STATED_DELAY.search(str(e))
        if match:
            return float(match.group(1) or match.group(2))
    return None


def is_retryable(exc: BaseException) -> bool:
    status = _status(exc)
    if status is not None:
        return status in RETRYABLE_STATUS
    return any(
        type(e).__name__.endswith(("ConnectionError", "TimeoutError", "Timeout", "RateLimitError"))
        for e in _chain(exc)
    )


def with_retries[T](
    fn: Callable[[], T],
    *,
    attempts: int = 6,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    sleep: Callable[[float], None] | None = None,
) -> T:
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:
            if not is_retryable(exc):
                raise
            if attempt == attempts - 1:
                raise LLMUnavailable(f"gave up after {attempts} attempts: {exc}") from exc
            stated = _retry_after(exc)
            if stated:  # never wait less than the provider asked for
                delay = min(stated, MAX_STATED_DELAY) + random.uniform(0.5, 1.5)
            else:
                delay = min(max_delay, base_delay * 2**attempt) * random.uniform(0.9, 1.1)
            (sleep or time.sleep)(delay)
    raise AssertionError("unreachable")
