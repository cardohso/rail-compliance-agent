"""Scores the agent's reports against the golden set.

A scored item is one (case, parameter) the case expects a verdict for. Everything here is
deterministic: no model judges anything. Rates carry their numerator and denominator because the
golden set is small, and a Wilson interval so a reader sees how much a single case moves them.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field

from rail_compliance.explanations import explanation_problems
from rail_compliance.golden import Expected, GoldenCase
from rail_compliance.report import Report
from rail_compliance.spec import spec_values

RATE_METRICS = (
    "verdict_accuracy",
    "unsafe_pass_rate",
    "needs_human_recall",
    "needs_human_precision",
    "tool_selection_accuracy",
    "argument_correctness",
    "citation_hit_rate",
)
HIGHER_IS_BETTER = {m: m != "unsafe_pass_rate" for m in RATE_METRICS}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ItemScore(_Strict):
    case: str
    parameter: str
    tags: list[str]
    expected: str
    verdict: str | None  # None: the run for this case crashed
    correct: bool
    unsafe_pass: bool
    tool_selection_ok: bool
    agent_calls: int
    check_calls: int
    correct_check_calls: int
    cited: list[str] = Field(default_factory=list)
    citation_hit: bool | None = None  # None: nothing was cited, so nothing to judge
    citation_precision: float | None = None


class Rate(_Strict):
    value: float | None
    k: int
    n: int
    low: float | None = None
    high: float | None = None


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k successes in n trials."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def rate(k: int, n: int) -> Rate:
    if n == 0:
        return Rate(value=None, k=0, n=0)
    low, high = wilson(k, n)
    return Rate(value=k / n, k=k, n=n, low=round(low, 4), high=round(high, 4))


def is_subsequence(wanted: Sequence[str], seen: Sequence[str]) -> bool:
    it = iter(seen)
    return all(any(name == w for name in it) for w in wanted)


def _score_item(case: GoldenCase, parameter: str, expected: Expected, report: Report | None):
    values = spec_values(case.spec)
    base = {
        "case": case.id,
        "parameter": parameter,
        "tags": case.tags,
        "expected": expected.verdict,
    }
    if report is None:  # the run crashed: counts against every metric, not as missing data
        return ItemScore(
            **base, verdict=None, correct=False, unsafe_pass=False, tool_selection_ok=False,
            agent_calls=0, check_calls=0, correct_check_calls=0,
        )  # fmt: skip
    result = report.result_for(parameter)
    calls = [t for t in report.trace if t.parameter == parameter and t.source == "agent"]
    names = [t.name for t in calls]
    acceptable = [expected.expected_tools, *expected.alt_tools]
    checks = [t for t in calls if t.name == "check"]
    right = [
        t
        for t in checks
        if t.args.get("parameter") == parameter
        and isinstance(t.args.get("spec_value"), int | float)
        and abs(float(t.args["spec_value"]) - values[parameter]) < 1e-9
    ]
    cited = [c.passage_id for c in result.citations]
    hit = precision = None
    if cited:
        gold = set(expected.gold_passages)
        hit = any(c in gold for c in cited)
        precision = sum(c in gold for c in cited) / len(cited)
    return ItemScore(
        **base,
        verdict=result.verdict,
        correct=result.verdict == expected.verdict,
        unsafe_pass=result.verdict == "pass" and expected.verdict in ("fail", "needs_human"),
        tool_selection_ok=any(is_subsequence(seq, names) for seq in acceptable),
        agent_calls=len(calls),
        check_calls=len(checks),
        correct_check_calls=len(right),
        cited=cited,
        citation_hit=hit,
        citation_precision=precision,
    )


def score_items(
    cases: Sequence[GoldenCase], reports: Mapping[str, Report | None]
) -> list[ItemScore]:
    items = []
    for case in cases:
        report = reports.get(case.id)
        for parameter, expected in case.expected.items():
            items.append(_score_item(case, parameter, expected, report))
    return items


def rates(items: Sequence[ItemScore]) -> dict[str, Rate]:
    escalated = [i for i in items if i.verdict == "needs_human"]
    expected_esc = [i for i in items if i.expected == "needs_human"]
    both = [i for i in items if i.expected == "needs_human" and i.verdict == "needs_human"]
    cited = [i for i in items if i.citation_hit is not None]
    return {
        "verdict_accuracy": rate(sum(i.correct for i in items), len(items)),
        "unsafe_pass_rate": rate(sum(i.unsafe_pass for i in items), len(items)),
        "needs_human_recall": rate(len(both), len(expected_esc)),
        "needs_human_precision": rate(len(both), len(escalated)),
        "tool_selection_accuracy": rate(sum(i.tool_selection_ok for i in items), len(items)),
        "argument_correctness": rate(
            sum(i.correct_check_calls for i in items), sum(i.check_calls for i in items)
        ),
        "citation_hit_rate": rate(sum(bool(i.citation_hit) for i in cited), len(cited)),
    }


def percentile(values: Sequence[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def explanation_quality(reports: Iterable[Report]) -> Rate:
    """Clean reasons / reasons the agent recorded. A rejected call was rewritten, and runtime
    reasons are written by code, so neither is the agent's explanation."""
    reasons = [
        str(t.args.get("reason", ""))
        for r in reports
        for t in r.trace
        if t.name == "needs_human" and t.ok and t.source == "agent"
    ]
    return rate(sum(1 for text in reasons if not explanation_problems(text)), len(reasons))


class Metrics(_Strict):
    n_cases: int
    n_items: int
    errors: int
    rates: dict[str, Rate]
    tool_calls_per_parameter: float | None
    by_tag: dict[str, dict[str, Rate]]
    confusion: dict[str, dict[str, int]]  # expected verdict -> actual verdict -> count
    per_spec: dict[str, float | None]  # tool calls, model calls, seconds (mean) and p50/p95 seconds
    # Report only, never gated: share of the agent's recorded escalation reasons with no problem
    # (see explanations.py). Added after the thresholds were set, so it has none.
    explanation_quality: Rate | None = None


def compute_metrics(
    cases: Sequence[GoldenCase],
    reports: Mapping[str, Report | None],
    items: Sequence[ItemScore] | None = None,
) -> Metrics:
    items = list(items) if items is not None else score_items(cases, reports)
    by_tag: dict[str, list[ItemScore]] = defaultdict(list)
    for item in items:
        for tag in item.tags:
            by_tag[tag].append(item)
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for item in items:
        confusion[item.expected][item.verdict or "error"] += 1
    done = [r for r in reports.values() if r is not None]
    seconds = [r.stats.seconds for r in done]
    n = len(done)
    return Metrics(
        n_cases=len(cases),
        n_items=len(items),
        errors=sum(1 for c in cases if reports.get(c.id) is None),
        rates=rates(items),
        tool_calls_per_parameter=(sum(i.agent_calls for i in items) / len(items))
        if items
        else None,
        by_tag={t: rates(group) for t, group in sorted(by_tag.items())},
        confusion={e: dict(v) for e, v in sorted(confusion.items())},
        per_spec={
            "tool_calls_mean": sum(r.stats.tool_calls for r in done) / n if n else None,
            "model_calls_mean": sum(r.stats.llm_calls for r in done) / n if n else None,
            "seconds_mean": sum(seconds) / n if n else None,
            "seconds_p50": percentile(seconds, 0.5),
            "seconds_p95": percentile(seconds, 0.95),
        },
        explanation_quality=explanation_quality(done),
    )
