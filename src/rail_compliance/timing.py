"""A clock that reports what a run would have taken with no caches and no rate throttle.

Evaluation re-runs hit the disk caches, so wall time says nothing about latency. The caches
store how long each original call took and add it back on a hit; the request throttle's waits
are subtracted because they are our own pacing, not the provider's response time.
"""

from __future__ import annotations

import time
from collections.abc import Callable


class Timing:
    def __init__(self, perf_counter: Callable[[], float] = time.perf_counter):
        self._perf = perf_counter
        self.cached = 0.0  # seconds replayed from cache hits
        self.waited = 0.0  # seconds spent waiting on the request throttle

    def clock(self) -> float:
        return self._perf() + self.cached - self.waited

    def add_cached(self, seconds: float) -> None:
        self.cached += seconds

    def add_throttle(self, seconds: float) -> None:
        self.waited += seconds
