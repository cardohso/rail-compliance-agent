"""HTTP API: POST /check (spec in, report out) and GET /health.

    uv run uvicorn rail_compliance.api:create_app --factory --port 8000

The agent is built once at startup. If it cannot be (no API key, no corpus or index), the process
still starts and /health says why it is not ready; /check then answers 503. A check can use up
to ~30 of the free tier's 500 daily model requests, so /check is rate-limited per client.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse

from rail_compliance import __version__
from rail_compliance.config import Settings, get_settings
from rail_compliance.factory import build_agent
from rail_compliance.llm import ConfigError
from rail_compliance.report import Report, to_markdown
from rail_compliance.retry import LLMUnavailable
from rail_compliance.spec import TrainSpec
from rail_compliance.tools.search import SearchError


class RateLimiter:
    """Per-client sliding windows: at most `per_minute` checks a minute and `per_day` a day.
    A limit of 0 means unlimited. `check` returns None to allow, or seconds to wait."""

    def __init__(self, per_minute: int, per_day: int, clock: Callable[[], float] = time.time):
        self.per_minute, self.per_day, self._clock = per_minute, per_day, clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, client: str) -> float | None:
        with self._lock:
            now = self._clock()
            hits = self._hits[client]
            while hits and now - hits[0] >= 86400:
                hits.popleft()
            recent = [t for t in hits if now - t < 60]
            if self.per_minute and len(recent) >= self.per_minute:
                return max(1.0, recent[0] + 60 - now)
            if self.per_day and len(hits) >= self.per_day:
                return max(1.0, hits[0] + 86400 - now)
            hits.append(now)
            return None


def _client_id(request: Request) -> str:
    # behind a proxy the caller is the first X-Forwarded-For entry
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "?")


def create_app(
    agent=None,
    *,
    agent_factory: Callable = build_agent,
    limiter: RateLimiter | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    limiter = limiter or RateLimiter(settings.api_checks_per_minute, settings.api_checks_per_day)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.agent, app.state.reason = agent, None
        if agent is None:
            try:
                app.state.agent = agent_factory(settings)
            except (ConfigError, SearchError) as exc:
                app.state.reason = str(exc)
        yield

    app = FastAPI(
        title="rail-compliance-agent",
        version=__version__,
        description="Checks a train design spec against the EU PRM TSI. Not legal advice.",
        lifespan=lifespan,
    )

    @app.get("/health")
    def health(request: Request) -> dict:
        ready = request.app.state.agent is not None
        return {
            "status": "ok",  # the process is alive; `ready` says whether /check can run
            "version": __version__,
            "ready": ready,
            "reason": request.app.state.reason,
            "search_backend": settings.search_backend,
            "agent_provider": settings.agent_provider,
        }

    @app.post("/check", response_model=Report)
    def check(
        spec: TrainSpec, request: Request, format: Literal["json", "markdown"] = "json"
    ) -> Response | Report:
        # Sync endpoint: FastAPI runs it in a worker thread, so blocking model calls are fine.
        current = request.app.state.agent
        if current is None:
            raise HTTPException(503, request.app.state.reason or "the agent is not ready")
        wait = limiter.check(_client_id(request))
        if wait is not None:
            raise HTTPException(
                429, "rate limit: each check uses a share of a small model quota",
                headers={"Retry-After": str(int(wait) + 1)},
            )  # fmt: skip
        try:
            report = current.run(spec)
        except LLMUnavailable as exc:
            raise HTTPException(503, f"the language model is unavailable: {exc}") from exc
        except SearchError as exc:
            raise HTTPException(502, f"the regulation search failed: {exc}") from exc
        if format == "markdown":
            return PlainTextResponse(to_markdown(report), media_type="text/markdown")
        return report

    return app
