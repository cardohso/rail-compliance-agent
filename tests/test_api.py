import json

import pytest
from fastapi.testclient import TestClient

from rail_compliance import __version__
from rail_compliance.api import RateLimiter, create_app
from rail_compliance.config import Settings
from rail_compliance.llm import ConfigError
from rail_compliance.retry import LLMUnavailable
from rail_compliance.tools.search import SearchError
from tests.eval_helpers import report_for

SPEC = {"name": "t", "unit_length_m": 30.0, "wheelchair_spaces": 1}


class FakeAgent:
    """Returns a canned report (or raises) so the HTTP layer is tested without any model."""

    def __init__(self, raises=None):
        self.raises, self.specs = raises, []

    def run(self, spec):
        self.specs.append(spec)
        if self.raises:
            raise self.raises
        return report_for("g04")


def client(agent=None, limiter=None, **kw):
    app = create_app(
        agent, limiter=limiter or RateLimiter(100, 1000), settings=Settings(_env_file=None), **kw
    )
    return TestClient(app)


def test_health_reports_version_and_readiness_without_secrets():
    with client(FakeAgent()) as c:
        body = c.get("/health").json()
    assert body["status"] == "ok" and body["version"] == __version__
    assert body["ready"] is True and body["reason"] is None
    assert {"search_backend", "agent_provider"} <= set(body)
    assert "key" not in json.dumps(body).lower()


def test_health_still_answers_when_the_agent_could_not_be_built():
    def broken(settings, **kw):
        raise ConfigError("no API key for 'gemini': set GEMINI_API_KEY")

    with client(None, agent_factory=broken) as c:
        health = c.get("/health")
        assert health.status_code == 200  # alive, just not ready
        assert health.json()["ready"] is False
        assert "GEMINI_API_KEY" in health.json()["reason"]
        denied = c.post("/check", json=SPEC)
    assert denied.status_code == 503 and "GEMINI_API_KEY" in denied.json()["detail"]


def test_check_returns_the_report_as_json_and_passes_the_validated_spec_on():
    agent = FakeAgent()
    with client(agent) as c:
        response = c.post("/check", json=SPEC)
    assert response.status_code == 200
    body = response.json()
    assert {"spec_name", "results", "trace", "stats", "disclaimer"} <= set(body)
    assert "Not legal advice" in body["disclaimer"]
    assert agent.specs[0].unit_length_m == 30.0


def test_check_can_return_markdown():
    with client(FakeAgent()) as c:
        response = c.post("/check?format=markdown", json=SPEC)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.text.startswith("# Compliance report")


def test_an_unknown_format_is_rejected():
    with client(FakeAgent()) as c:
        assert c.post("/check?format=pdf", json=SPEC).status_code == 422


@pytest.mark.parametrize(
    "bad",
    [
        {"name": "t"},  # unit length missing
        {"name": "t", "unit_length_m": -1},
        {"name": "t", "unit_length_m": 30, "wheelchair_space": 1},  # typo'd field
        {"name": "t", "unit_length_m": 30, "toilets": {"fitted": 1, "universal": 2}},
    ],
)
def test_an_invalid_spec_is_a_422_that_names_the_problem_and_never_reaches_the_agent(bad):
    agent = FakeAgent()
    with client(agent) as c:
        response = c.post("/check", json=bad)
    assert response.status_code == 422 and response.json()["detail"]
    assert agent.specs == []


@pytest.mark.parametrize(
    ("error", "status"),
    [(LLMUnavailable("quota spent"), 503), (SearchError("rail assistant down"), 502)],
)
def test_provider_failures_are_not_500s(error, status):
    with client(FakeAgent(raises=error)) as c:
        response = c.post("/check", json=SPEC)
    assert response.status_code == status
    assert str(error) in response.json()["detail"]


def test_a_client_over_its_limit_gets_429_with_retry_after_and_others_are_unaffected():
    limiter = RateLimiter(per_minute=1, per_day=100)
    with client(FakeAgent(), limiter=limiter) as c:
        assert (
            c.post("/check", json=SPEC, headers={"x-forwarded-for": "1.1.1.1"}).status_code == 200
        )
        blocked = c.post("/check", json=SPEC, headers={"x-forwarded-for": "1.1.1.1, 9.9.9.9"})
        other = c.post("/check", json=SPEC, headers={"x-forwarded-for": "2.2.2.2"})
    assert blocked.status_code == 429 and int(blocked.headers["retry-after"]) > 0
    assert other.status_code == 200


def test_health_is_not_rate_limited():
    limiter = RateLimiter(per_minute=1, per_day=1)
    with client(FakeAgent(), limiter=limiter) as c:
        assert all(c.get("/health").status_code == 200 for _ in range(5))


# --- the limiter on its own ---------------------------------------------------------------------


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_limiter_allows_up_to_the_minute_limit_then_blocks_until_the_window_slides():
    clock = Clock()
    limiter = RateLimiter(per_minute=2, per_day=100, clock=clock)
    assert limiter.check("a") is None and limiter.check("a") is None
    wait = limiter.check("a")
    assert wait is not None and 0 < wait <= 60
    clock.now += 61
    assert limiter.check("a") is None


def test_limiter_enforces_a_daily_cap():
    clock = Clock()
    limiter = RateLimiter(per_minute=100, per_day=3, clock=clock)
    for _ in range(3):
        assert limiter.check("a") is None
        clock.now += 61
    assert limiter.check("a") is not None
    clock.now += 86400
    assert limiter.check("a") is None


def test_limiter_with_zero_limits_is_unlimited():
    limiter = RateLimiter(per_minute=0, per_day=0)
    assert all(limiter.check("a") is None for _ in range(500))
