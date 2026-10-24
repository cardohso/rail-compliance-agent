import json

from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from rail_compliance.llm import CachedAgentLLM, CachedStructuredLLM
from rail_compliance.models import SearchResult
from rail_compliance.throttle import Throttle
from rail_compliance.timing import Timing
from rail_compliance.tools.search import CachingBackend
from tests.factories import passage


class FakeClock:
    """A stand-in for time.perf_counter that only moves when told to."""

    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class Answer(BaseModel):
    value: float


def test_timing_clock_adds_cached_seconds_and_removes_throttle_waits():
    base = FakeClock()
    timing = Timing(perf_counter=base)
    assert timing.clock() == 100.0
    timing.add_cached(5.0)
    timing.add_throttle(2.0)
    assert timing.clock() == 103.0


def test_throttle_reports_how_long_it_waited():
    base = FakeClock()
    timing = Timing(perf_counter=base)
    slept = []

    def sleep(seconds):
        slept.append(seconds)
        base.now += seconds

    throttle = Throttle(1, clock=base, sleep=sleep, on_wait=timing.add_throttle)
    throttle.wait()
    throttle.wait()  # must wait the rest of the minute
    assert round(timing.waited, 3) == round(sum(slept), 3) > 0


class SlowAgent:
    name = "slow"

    def __init__(self, base, timing, seconds=3.0, wait=1.0):
        self.base, self.timing, self.seconds, self.wait = base, timing, seconds, wait
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        self.base.now += self.seconds  # the call takes 3 s, 1 s of which was the throttle
        self.timing.add_throttle(self.wait)
        return AIMessage("ok")


def test_a_cache_miss_records_model_time_without_the_throttle_wait(tmp_path):
    base = FakeClock()
    timing = Timing(perf_counter=base)
    cached = CachedAgentLLM(SlowAgent(base, timing), tmp_path, timing=timing)
    cached.invoke([HumanMessage("h")])
    entry = json.loads(next(tmp_path.glob("agent-*.json")).read_text("utf-8"))
    assert entry["seconds"] == 2.0  # 3 s elapsed minus 1 s spent waiting on the throttle


def test_a_cache_hit_advances_the_clock_by_the_original_latency(tmp_path):
    base = FakeClock()
    timing = Timing(perf_counter=base)
    inner = SlowAgent(base, timing)
    cached = CachedAgentLLM(inner, tmp_path, timing=timing)
    cached.invoke([HumanMessage("h")])
    before = timing.clock()
    cached.invoke([HumanMessage("h")])  # hit: no real time passes
    assert inner.calls == 1
    assert timing.clock() - before == 2.0


def test_old_cache_entries_without_a_latency_still_load(tmp_path):
    from langchain_core.messages import messages_to_dict

    inner = SlowAgent(FakeClock(), Timing())
    cached = CachedAgentLLM(inner, tmp_path)
    cached.invoke([HumanMessage("h")])
    path = next(tmp_path.glob("agent-*.json"))
    path.write_text(json.dumps(messages_to_dict([AIMessage("legacy")])[0]), "utf-8")  # old format
    assert CachedAgentLLM(inner, tmp_path).invoke([HumanMessage("h")]).content == "legacy"


def test_structured_and_search_caches_record_and_replay_latency(tmp_path):
    base = FakeClock()
    timing = Timing(perf_counter=base)

    class Inner:
        name = "m"

        def extract(self, system, user, schema):
            base.now += 4.0
            return schema(value=1)

    s = CachedStructuredLLM(Inner(), tmp_path, timing=timing)
    s.extract("a", "b", Answer)
    before = timing.clock()
    s.extract("a", "b", Answer)
    assert timing.clock() - before == 4.0

    class Search:
        name = "fake"

        def search(self, question, k):
            base.now += 1.5
            return SearchResult(question=question, passages=[passage("text")], backend="fake")

    c = CachingBackend(Search(), tmp_path / "search", timing=timing)
    c.search("door width", 8)
    before = timing.clock()
    c.search("door width", 8)
    assert timing.clock() - before == 1.5
