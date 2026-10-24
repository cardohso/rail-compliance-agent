"""The quality gate: compare metrics with eval/thresholds.yaml.

    metrics:
      verdict_accuracy: {min: 0.80}
      tool_calls_per_parameter: {max: 6}
    tags:
      exact-limit: {verdict_accuracy: {min: 0.85}}

A metric with no value (nothing to measure it on) fails its check: silence is not a pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from rail_compliance.evaluation.metrics import RATE_METRICS, Metrics, Rate

KNOWN = (*RATE_METRICS, "tool_calls_per_parameter", "errors")


class ThresholdError(ValueError):
    pass


@dataclass(frozen=True)
class Check:
    scope: str  # "all" or "tag:<name>"
    metric: str
    value: float | None
    n: int | None
    low: float | None
    high: float | None
    minimum: float | None
    maximum: float | None
    ok: bool
    message: str


def load_thresholds(path: Path) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    for key in data:
        if key not in ("metrics", "tags"):
            raise ThresholdError(f"{path}: unknown key '{key}' (expected 'metrics' and 'tags')")
    return data


def _validate(
    name: str, rule: object, where: str, allowed: tuple[str, ...]
) -> tuple[float | None, float | None]:
    if name not in allowed:
        raise ThresholdError(f"{where}: unknown metric '{name}'. Known: {', '.join(allowed)}")
    if not isinstance(rule, dict) or not set(rule) <= {"min", "max"} or not rule:
        raise ThresholdError(f"{where}.{name}: expected {{min: x}} and/or {{max: x}}")
    return rule.get("min"), rule.get("max")


def _check(scope, metric, value, n, low, high, minimum, maximum) -> Check:
    problems = []
    if value is None:
        problems.append("no value: nothing could be measured")
    else:
        if minimum is not None and value < minimum:
            problems.append(f"{value:.3f} < {minimum:g}")
        if maximum is not None and value > maximum:
            problems.append(f"{value:.3f} > {maximum:g}")
    return Check(scope, metric, value, n, low, high, minimum, maximum, not problems,
                 "ok" if not problems else "; ".join(problems))  # fmt: skip


def _from_rate(scope: str, metric: str, r: Rate, minimum, maximum) -> Check:
    return _check(scope, metric, r.value, r.n, r.low, r.high, minimum, maximum)


def check_thresholds(metrics: Metrics, thresholds: dict) -> list[Check]:
    checks: list[Check] = []
    for name, rule in (thresholds.get("metrics") or {}).items():
        minimum, maximum = _validate(name, rule, "metrics", KNOWN)
        if name in RATE_METRICS:
            checks.append(_from_rate("all", name, metrics.rates[name], minimum, maximum))
        elif name == "errors":
            checks.append(_check("all", name, float(metrics.errors), metrics.n_cases, None, None,
                                 minimum, maximum))  # fmt: skip
        else:
            checks.append(_check("all", name, metrics.tool_calls_per_parameter, metrics.n_items,
                                 None, None, minimum, maximum))  # fmt: skip
    for tag, rules in (thresholds.get("tags") or {}).items():
        group = metrics.by_tag.get(tag)
        for name, rule in (rules or {}).items():
            minimum, maximum = _validate(name, rule, f"tags.{tag}", RATE_METRICS)
            r = group[name] if group else Rate(value=None, k=0, n=0)
            checks.append(_from_rate(f"tag:{tag}", name, r, minimum, maximum))
    return checks


def passed(checks: list[Check]) -> bool:
    return all(c.ok for c in checks)


def gate_markdown(checks: list[Check]) -> str:
    def fmt(c: Check) -> str:
        if c.value is None:
            return "n/a"
        text = f"{c.value:.3f}"
        return text + (f" ({c.low:.2f}-{c.high:.2f})" if c.low is not None else "")

    def limit(c: Check) -> str:
        parts = ([f"≥ {c.minimum:g}"] if c.minimum is not None else []) + (
            [f"≤ {c.maximum:g}"] if c.maximum is not None else []
        )
        return " and ".join(parts)

    verdict = "PASSED" if passed(checks) else "FAILED"
    lines = [
        f"### Quality gate: {verdict}",
        "",
        "| Scope | Metric | Value (95% CI) | n | Required | |",
        "|---|---|---|---|---|---|",
    ]
    for c in checks:
        lines.append(
            f"| {c.scope} | `{c.metric}` | {fmt(c)} | {c.n if c.n is not None else ''} | "
            f"{limit(c)} | {'ok' if c.ok else '**' + c.message + '**'} |"
        )
    return "\n".join(lines) + "\n"
