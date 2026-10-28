"""Run the agent over the golden set, score it, and write the results."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from rail_compliance.evaluation.gate import Check, check_thresholds, gate_markdown
from rail_compliance.evaluation.metrics import ItemScore, Metrics, compute_metrics, score_items
from rail_compliance.golden import GoldenCase
from rail_compliance.report import Report, to_markdown
from rail_compliance.retry import LLMUnavailable


@dataclass
class RunResult:
    reports: dict[str, Report | None] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)


def run_cases(
    cases: Sequence[GoldenCase],
    agent,
    progress: Callable[[str], None] = lambda message: None,
) -> RunResult:
    """One report per case. A crash in one case is recorded and the rest still run; a provider
    outage (`LLMUnavailable`) stops the run, because the remaining numbers would be junk."""
    run = RunResult()
    for number, case in enumerate(cases, start=1):
        started = time.perf_counter()
        try:
            run.reports[case.id] = agent.run(case.spec)
            note = f"{run.reports[case.id].stats.tool_calls} tool calls"
        except LLMUnavailable:
            raise
        except Exception as exc:
            run.reports[case.id] = None
            run.errors[case.id] = f"{type(exc).__name__}: {exc}"[:500]
            note = f"ERROR {run.errors[case.id][:120]}"
        progress(f"[{number}/{len(cases)}] {case.id} {note} ({time.perf_counter() - started:.0f}s)")
    return run


def results_markdown(
    cases: Sequence[GoldenCase],
    metrics: Metrics,
    items: Sequence[ItemScore],
    checks: list[Check] | None,
    meta: dict,
) -> str:
    def cell(r) -> str:
        if r.value is None:
            return "n/a"
        return f"{r.value:.2f} ({r.low:.2f}-{r.high:.2f}), {r.k}/{r.n}"

    out = [
        "# Evaluation results",
        "",
        f"Model `{meta.get('model')}`, search `{meta.get('search')}`, "
        f"{metrics.n_cases} golden specs, {metrics.n_items} scored verdicts. "
        "Intervals are 95% Wilson; with this few cases one case moves a rate by several points.",
        "",
        "| Metric | Value (95% CI), k/n |",
        "|---|---|",
    ]
    for name, r in metrics.rates.items():
        out.append(f"| `{name}` | {cell(r)} |")
    out.append(f"| `tool_calls_per_parameter` | {metrics.tool_calls_per_parameter or 0:.2f} |")
    out.append(f"| `errors` | {metrics.errors} |")
    if metrics.explanation_quality is not None:
        out.append(f"| `explanation_quality` (report only) | {cell(metrics.explanation_quality)} |")
    ps = metrics.per_spec
    out += [
        "",
        f"Per spec: {ps['tool_calls_mean']:.1f} tool calls, {ps['model_calls_mean']:.1f} model "
        f"calls, {ps['seconds_mean']:.0f} s mean ({ps['seconds_p50']:.0f} s median, "
        f"{ps['seconds_p95']:.0f} s p95; model and search time only, rate-limit waits "
        "excluded)."
        if ps["seconds_mean"] is not None
        else "No spec completed.",
        "",
    ]
    if checks is not None:
        out += [gate_markdown(checks), ""]
    out += ["### By tag (verdict accuracy)", "", "| Tag | Value, k/n |", "|---|---|"]
    for tag, group in metrics.by_tag.items():
        out.append(f"| `{tag}` | {cell(group['verdict_accuracy'])} |")
    out += ["", "### Confusion (rows: golden verdict, columns: agent verdict)", ""]
    columns = sorted({v for row in metrics.confusion.values() for v in row})
    out += ["| golden \\ agent | " + " | ".join(columns) + " |", "|---" * (len(columns) + 1) + "|"]
    for expected, row in metrics.confusion.items():
        out.append(f"| {expected} | " + " | ".join(str(row.get(c, 0)) for c in columns) + " |")
    header = "| Case | Parameter | Golden | Agent | Tools ok | Cited gold |"
    out += ["", "### Every scored verdict", "", header, "|---|---|---|---|---|---|"]
    for i in items:
        mark = "ok" if i.correct else "**WRONG**"
        hit = {True: "yes", False: "no", None: "-"}[i.citation_hit]
        out.append(
            f"| {i.case} | `{i.parameter}` | {i.expected} | {i.verdict or 'error'} ({mark}) | "
            f"{'yes' if i.tool_selection_ok else 'no'} | {hit} |"
        )
    return "\n".join(out) + "\n"


def save_run(
    out: Path,
    cases: Sequence[GoldenCase],
    run: RunResult,
    meta: dict,
    thresholds: dict | None = None,
) -> tuple[Metrics, list[ItemScore], list[Check] | None]:
    out = Path(out)
    (out / "reports").mkdir(parents=True, exist_ok=True)
    for case_id, report in run.reports.items():
        if report is not None:
            (out / "reports" / f"{case_id}.json").write_text(
                report.model_dump_json(indent=2), "utf-8"
            )
            (out / "reports" / f"{case_id}.md").write_text(to_markdown(report), "utf-8")
    items = score_items(cases, run.reports)
    metrics = compute_metrics(cases, run.reports, items)
    checks = check_thresholds(metrics, thresholds) if thresholds is not None else None
    payload = {
        "meta": meta,
        "metrics": json.loads(metrics.model_dump_json()),
        "items": [json.loads(i.model_dump_json()) for i in items],
        "errors": run.errors,
    }
    (out / "metrics.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), "utf-8")
    (out / "summary.md").write_text(results_markdown(cases, metrics, items, checks, meta), "utf-8")
    return metrics, items, checks
