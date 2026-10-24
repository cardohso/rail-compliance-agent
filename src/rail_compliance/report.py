"""The compliance report: per parameter a verdict, the requirement, the spec value and citations.

Verdicts are `pass`, `fail`, `needs_human`, plus `not_applicable` for a rule whose conditions are
false for this spec (for example a toilet rule on a train with no toilets). The JSON also carries
the agent's tool-call trace, which the evaluation scores.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from rail_compliance.models import CheckResult, Citation, Comparator, HumanReview

FinalVerdict = Literal["pass", "fail", "needs_human", "not_applicable"]

DISCLAIMER = (
    "Not legal advice. This report is an engineering aid produced by software from the text of "
    "the PRM TSI (Regulation (EU) No 1300/2014); it can be wrong or incomplete. Conformity is "
    "assessed by a notified body, not by this tool."
)
SYMBOL: dict[str, str] = {">=": "≥", "<=": "≤", "==": "=", ">": ">", "<": "<"}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ToolCall(_Strict):
    index: int  # position in the whole run
    parameter: str
    name: str
    args: dict[str, Any]
    ok: bool  # False when the runtime rejected the call (bad arguments, unknown id, wrong order)
    summary: str
    seconds: float
    source: Literal["agent", "runtime"] = "agent"  # runtime = decided by code, not the model


class ParameterResult(_Strict):
    parameter: str
    verdict: FinalVerdict
    spec_value: float | None = None
    unit: str | None = None
    requirement: str | None = None  # e.g. "≥ 800 mm"
    reason: str
    checks: list[CheckResult] = Field(default_factory=list)
    reviews: list[HumanReview] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    consulted: list[str] = Field(default_factory=list)  # passage ids the searches returned


class Stats(_Strict):
    tool_calls: int
    llm_calls: int
    seconds: float
    agent_model: str
    search_backend: str


class Report(_Strict):
    spec_name: str
    spec: dict[str, Any]
    disclaimer: str = DISCLAIMER
    results: list[ParameterResult]
    trace: list[ToolCall]
    stats: Stats

    def counts(self) -> dict[str, int]:
        out = {"pass": 0, "fail": 0, "needs_human": 0, "not_applicable": 0}
        for r in self.results:
            out[r.verdict] += 1
        return out

    def result_for(self, parameter: str) -> ParameterResult:
        return next(r for r in self.results if r.parameter == parameter)


def describe_rule(comparator: Comparator | None, required: float | None, unit: str | None) -> str:
    if comparator is None or required is None:
        return ""
    return f"{SYMBOL[comparator]} {required:g}" + (f" {unit}" if unit else "")


def _fmt_value(value: float | None, unit: str | None) -> str:
    if value is None:
        return "not supplied"
    return f"{value:g}" + (f" {unit}" if unit else "")


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def to_markdown(report: Report) -> str:
    counts = report.counts()
    lines = [
        f"# Compliance report: {report.spec_name}",
        "",
        f"> {report.disclaimer}",
        "",
        "**Summary:** "
        + ", ".join(f"{n} {name.replace('_', ' ')}" for name, n in counts.items() if n),
        "",
        "| Parameter | Spec value | Requirement | Verdict |",
        "|---|---|---|---|",
    ]
    for r in report.results:
        lines.append(
            f"| `{r.parameter}` | {_fmt_value(r.spec_value, r.unit)} | "
            f"{_cell(r.requirement or '-')} | **{r.verdict.replace('_', ' ')}** |"
        )
    for r in report.results:
        lines += ["", f"## `{r.parameter}`: {r.verdict.replace('_', ' ')}", "", r.reason]
        for review in r.reviews:
            lines += [
                "",
                f"- Needs a person ({review.category.replace('_', ' ')}): {review.reason}",
            ]
        for c in r.citations:
            link = (
                f"[{c.document}, {c.section}]({c.url})" if c.url else f"{c.document}, {c.section}"
            )
            lines += ["", f"{link} (`{c.passage_id}`):", "", f"> {c.quote}"]
    s = report.stats
    lines += [
        "",
        "---",
        f"{s.tool_calls} tool calls, {s.llm_calls} model calls, {s.seconds:.1f} s. "
        f"Model `{s.agent_model}`, search `{s.search_backend}`.",
        "",
    ]
    return "\n".join(lines)
