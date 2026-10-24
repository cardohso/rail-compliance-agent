import json

import httpx
import pytest

from rail_compliance.models import SearchResult
from rail_compliance.tools.search import (
    CachingBackend,
    LiveBackend,
    LocalBackend,
    ReplayBackend,
    ReplayMiss,
    SearchError,
    search_regulation,
)
from tests.factories import passage

P1 = passage(
    "(1) All exterior passenger doorways shall have a minimum clear useable width of 800 mm."
)
P2 = passage("(2) Another passage.", id_="tsi-prm:Annex §4.2.2.3.2#2")


class Counting:
    name = "fake"

    def __init__(self):
        self.calls = []

    def search(self, question, k):
        self.calls.append((question, k))
        return SearchResult(question=question, passages=[P1, P2][:k], backend="fake")


def test_search_regulation_normalises_whitespace_and_passes_k():
    backend = Counting()
    result = search_regulation("  minimum   door \n width ", backend, k=1)
    assert backend.calls == [("minimum door width", 1)]
    assert [p.id for p in result.passages] == [P1.id]


@pytest.mark.parametrize("question", ["", "  ", "ab", "x" * 501])
def test_search_regulation_rejects_questions_the_live_api_would_reject(question):
    with pytest.raises(ValueError, match="characters"):
        search_regulation(question, Counting())


def test_local_backend_wraps_a_retrieve_function():
    backend = LocalBackend(lambda q, k: [P1, P2][:k])
    result = backend.search("door width", 2)
    assert result.backend == "local"
    assert result.answer is None
    assert [p.id for p in result.passages] == [P1.id, P2.id]


# --- live backend, against httpx's mock transport -------------------------------------------

ASK_OK = {
    "answer": "Exterior doorways need 800 mm [1].",
    "refused": False,
    "refusal_reason": None,
    "trace_id": "abc",
    "citations": [
        {
            "n": 1,
            "passage_id": P1.id,
            "doc_id": "tsi-prm",
            "document": "PRM TSI",
            "section": "Annex §4.2.2.3.2",
            "heading": "4.2.2.3.2. Exterior doors",
            "passage": P1.text,
            "url": "https://eur-lex.europa.eu/x",
            "score": 0.8123,
        }
    ],
}


def live(handler, **kw):
    sleeps = []
    backend = LiveBackend(
        "https://rail.example/",
        httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=sleeps.append,
        **kw,
    )
    return backend, sleeps


def test_live_backend_posts_the_question_and_maps_the_citations():
    seen = []

    def handler(request):
        seen.append((str(request.url), json.loads(request.content)))
        return httpx.Response(200, json=ASK_OK)

    backend, _ = live(handler)
    result = backend.search("door width", 8)
    assert seen == [("https://rail.example/ask", {"question": "door width"})]
    assert result.backend == "live"
    assert result.answer.startswith("Exterior doorways")
    assert result.refused is False
    assert result.passages[0].id == P1.id
    assert result.passages[0].text == P1.text
    assert result.passages[0].score == 0.8123


def test_live_backend_reports_a_refusal_with_no_passages():
    refusal = {**ASK_OK, "refused": True, "refusal_reason": "low_retrieval_score", "citations": []}
    backend, _ = live(lambda r: httpx.Response(200, json=refusal))
    result = backend.search("what is the best pizza", 8)
    assert result.refused is True
    assert result.passages == []


def test_live_backend_retries_a_rate_limit_and_honours_retry_after():
    replies = iter(
        [httpx.Response(429, headers={"retry-after": "7"}), httpx.Response(200, json=ASK_OK)]
    )
    backend, sleeps = live(lambda r: next(replies))
    assert backend.search("door width", 8).passages
    assert len(sleeps) == 1
    assert 6 < sleeps[0] < 8  # retry-after 7 s, with a little jitter


def test_live_backend_backs_off_exponentially_without_retry_after():
    replies = iter([httpx.Response(503), httpx.Response(503), httpx.Response(200, json=ASK_OK)])
    backend, sleeps = live(lambda r: next(replies), base_delay=2.0)
    backend.search("door width", 8)
    assert 1.7 < sleeps[0] < 2.3
    assert 3.5 < sleeps[1] < 4.5


def test_live_backend_gives_up_after_the_attempt_limit():
    backend, sleeps = live(lambda r: httpx.Response(429), attempts=3)
    with pytest.raises(SearchError, match="gave up after 3 attempts"):
        backend.search("door width", 8)
    assert len(sleeps) == 2  # no sleep after the last attempt


def test_live_backend_does_not_retry_a_client_error():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(422, text="bad question")

    backend, sleeps = live(handler)
    with pytest.raises(SearchError, match="422"):
        backend.search("door width", 8)
    assert len(calls) == 1
    assert sleeps == []


def test_live_backend_retries_a_network_error():
    attempts = []

    def handler(request):
        attempts.append(1)
        if len(attempts) == 1:
            raise httpx.ConnectError("boom")
        return httpx.Response(200, json=ASK_OK)

    backend, sleeps = live(handler)
    assert backend.search("door width", 8).passages
    assert len(sleeps) == 1


# --- replay and cache -----------------------------------------------------------------------


def test_replay_backend_serves_recorded_results_and_truncates_to_k(tmp_path):
    recorded = SearchResult(question="q q q", passages=[P1, P2], backend="local")
    path = tmp_path / "rec.json"
    path.write_text(json.dumps({"q q q": recorded.model_dump()}), encoding="utf-8")
    backend = ReplayBackend.from_file(path)
    assert len(backend.search("q q q", 8).passages) == 2
    assert len(backend.search("q q q", 1).passages) == 1


def test_replay_miss_names_the_question():
    with pytest.raises(ReplayMiss, match="unknown question"):
        ReplayBackend({}).search("unknown question", 8)


def test_cache_calls_the_inner_backend_once_per_question_and_k(tmp_path):
    inner = Counting()
    cached = CachingBackend(inner, tmp_path)
    first = cached.search("door width", 2)
    second = cached.search("door width", 2)
    assert first == second
    assert len(inner.calls) == 1
    assert (cached.hits, cached.misses) == (1, 1)
    cached.search("door width", 1)  # a different k is a different entry
    cached.search("step height", 2)
    assert len(inner.calls) == 3


def test_cache_survives_a_new_instance(tmp_path):
    inner = Counting()
    CachingBackend(inner, tmp_path).search("door width", 2)
    CachingBackend(inner, tmp_path).search("door width", 2)
    assert len(inner.calls) == 1


def test_cache_keys_include_the_backend_name(tmp_path):
    a, b = Counting(), Counting()
    b.name = "other"
    CachingBackend(a, tmp_path).search("door width", 2)
    CachingBackend(b, tmp_path).search("door width", 2)
    assert len(a.calls) == len(b.calls) == 1
