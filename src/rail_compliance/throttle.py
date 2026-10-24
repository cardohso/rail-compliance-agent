"""Client-side rate limit: stay under a provider's requests-per-minute quota instead of hitting
it and backing off. Gemini's free tier allows 15 requests a minute; one spec needs 15-30."""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable


class Throttle:
    """Sliding window: at most `per_minute` calls in any 60 s. 0 means unlimited."""

    def __init__(
        self,
        per_minute: int,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        on_wait: Callable[[float], None] | None = None,
    ):
        self.per_minute, self._clock, self._sleep = per_minute, clock, sleep
        self._on_wait = on_wait  # told how long each wait was, so latency can exclude it
        self._stamps: deque[float] = deque()
        self._lock = threading.Lock()

    def wait(self) -> None:
        if self.per_minute <= 0:
            return
        with self._lock:
            now = self._clock()
            while self._stamps and now - self._stamps[0] >= 60:
                self._stamps.popleft()
            if len(self._stamps) >= self.per_minute:
                wait = self._stamps[0] + 60 - now
                self._sleep(wait)
                if self._on_wait:
                    self._on_wait(wait)
                now = self._clock()
                while self._stamps and now - self._stamps[0] >= 60:
                    self._stamps.popleft()
            self._stamps.append(now)
