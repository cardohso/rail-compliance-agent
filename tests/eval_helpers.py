"""Build reports for chosen golden cases so metrics can be checked against hand-worked numbers."""

from rail_compliance.golden import GoldenCase, load_golden
from rail_compliance.models import Citation
from rail_compliance.report import ParameterResult, Report, Stats, ToolCall
from rail_compliance.spec import spec_values

CASES = {c.id: c for c in load_golden()}


def call(parameter, name, args=None, ok=True, seconds=1.0, source="agent") -> ToolCall:
    return ToolCall(index=0, parameter=parameter, name=name, args=args or {}, ok=ok,
                    summary="", seconds=seconds, source=source)  # fmt: skip


def citation(passage_id) -> Citation:
    doc = passage_id.split(":")[0]
    return Citation(passage_id=passage_id, doc_id=doc, document="PRM TSI", section="s",
                    quote="q")  # fmt: skip


def good_calls(case: GoldenCase, parameter: str):
    value = spec_values(case.spec)[parameter]
    return [
        call(parameter, "search_regulation", {"question": "q"}),
        call(parameter, "extract_requirement", {"parameter": parameter}),
        call(parameter, "check", {"parameter": parameter, "spec_value": value,
                                  "requirement_id": "R1"}),
    ]  # fmt: skip


def report_for(case_id, verdicts=None, calls=None, cited=None, seconds=10.0) -> Report:
    """A report for `case_id`. By default the agent returns every golden verdict, calls the
    expected tools with the right arguments and cites the gold passages."""
    case = CASES[case_id]
    verdicts, calls, cited = verdicts or {}, calls or {}, cited or {}
    results, trace = [], []
    for parameter, expected in case.expected.items():
        verdict = verdicts.get(parameter, expected.verdict)
        parameter_calls = calls.get(parameter, good_calls(case, parameter))
        trace += parameter_calls
        ids = cited.get(parameter, expected.gold_passages)
        results.append(
            ParameterResult(
                parameter=parameter,
                verdict=verdict,
                reason="r",
                citations=[citation(p) for p in ids],
                consulted=list(expected.gold_passages),
            )
        )
    stats = Stats(
        tool_calls=sum(1 for t in trace if t.source == "agent"),
        llm_calls=len(trace) + 1,
        seconds=seconds,
        agent_model="scripted",
        search_backend="fake",
    )
    return Report(spec_name=case.spec.name, spec={}, results=results, trace=trace, stats=stats)


def perfect(case_ids):
    return {c: report_for(c) for c in case_ids}
