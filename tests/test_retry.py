import pytest

from rail_compliance.retry import LLMUnavailable, with_retries


class Boom(Exception):
    def __init__(self, status=None, retry_after=None):
        super().__init__(f"boom {status}")
        self.status_code = status
        if retry_after is not None:
            self.response = type("R", (), {"headers": {"retry-after": str(retry_after)}})()


class ReadTimeout(Exception):
    pass


def flaky(failures, result="ok"):
    errors = list(failures)

    def fn():
        if errors:
            raise errors.pop(0)
        return result

    return fn


def test_success_needs_no_sleep():
    sleeps = []
    assert with_retries(flaky([]), sleep=sleeps.append) == "ok"
    assert sleeps == []


def test_retries_rate_limits_with_exponential_backoff():
    sleeps = []
    assert with_retries(flaky([Boom(429), Boom(503)]), base_delay=2.0, sleep=sleeps.append) == "ok"
    assert 1.7 < sleeps[0] < 2.3
    assert 3.5 < sleeps[1] < 4.5


def test_honours_retry_after():
    sleeps = []
    with_retries(flaky([Boom(429, retry_after=7)]), sleep=sleeps.append)
    assert 6 < sleeps[0] < 8


def test_does_not_retry_a_client_error():
    sleeps = []
    with pytest.raises(Boom):
        with_retries(flaky([Boom(400)]), sleep=sleeps.append)
    assert sleeps == []


def test_retries_timeouts_without_a_status_code():
    assert with_retries(flaky([ReadTimeout()]), sleep=lambda s: None) == "ok"


def test_gives_up_with_llm_unavailable():
    sleeps = []
    with pytest.raises(LLMUnavailable, match="gave up after 3 attempts"):
        with_retries(flaky([Boom(429)] * 5), attempts=3, sleep=sleeps.append)
    assert len(sleeps) == 2


def test_delay_is_capped():
    sleeps = []
    with_retries(
        flaky([Boom(503)] * 4), attempts=6, base_delay=10, max_delay=15, sleep=sleeps.append
    )
    assert max(sleeps) <= 15 * 1.1
