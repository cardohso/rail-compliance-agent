import json

from rail_compliance.models import CheckResult, Citation, HumanReview
from rail_compliance.report import (
    DISCLAIMER,
    ParameterResult,
    Report,
    Stats,
    ToolCall,
    describe_rule,
    to_markdown,
)

CITE = Citation(
    passage_id="tsi-prm:Annex §4.2.2.3.2#1",
    doc_id="tsi-prm",
    document="PRM TSI",
    section="Annex §4.2.2.3.2",
    url="https://eur-lex.europa.eu/x",
    quote="shall have a minimum clear useable width of 800 mm",
)


def make_report() -> Report:
    check = CheckResult(
        parameter="exterior_doors.clear_width_mm",
        verdict="fail",
        reason="780 mm violates ≥ 800 mm",
        spec_value=780,
        required_value=800,
        comparator=">=",
        unit="mm",
        margin=-20,
    )
    return Report(
        spec_name="Demo | train",
        spec={"unit_length_m": 100},
        results=[
            ParameterResult(
                parameter="exterior_doors.clear_width_mm",
                verdict="fail",
                spec_value=780,
                unit="mm",
                requirement="≥ 800 mm",
                reason="780 mm violates ≥ 800 mm",
                checks=[check],
                citations=[CITE],
            ),
            ParameterResult(
                parameter="steps.internal_step_height_mm",
                verdict="needs_human",
                reason="The spec does not supply steps.internal_step_height_mm",
                reviews=[
                    HumanReview(
                        parameter="steps.internal_step_height_mm",
                        category="missing_data",
                        reason="The spec does not supply it",
                    )
                ],
            ),
        ],
        trace=[
            ToolCall(
                index=0,
                parameter="exterior_doors.clear_width_mm",
                name="check",
                args={"spec_value": 780},
                ok=True,
                summary="fail",
                seconds=0.01,
            )
        ],
        stats=Stats(
            tool_calls=1,
            llm_calls=2,
            seconds=1.5,
            agent_model="scripted:x",
            search_backend="replay",
        ),
    )


def test_counts():
    assert make_report().counts() == {"pass": 0, "fail": 1, "needs_human": 1, "not_applicable": 0}


def test_json_round_trips():
    report = make_report()
    again = Report.model_validate(json.loads(report.model_dump_json()))
    assert again == report


def test_markdown_has_disclaimer_summary_table_and_citation():
    md = to_markdown(make_report())
    assert md.startswith("# Compliance report: Demo | train")
    assert DISCLAIMER in md
    assert "**Summary:** 1 fail, 1 needs human" in md
    assert "| `exterior_doors.clear_width_mm` | 780 mm | ≥ 800 mm | **fail** |" in md
    assert "| `steps.internal_step_height_mm` | not supplied | - | **needs human** |" in md
    assert "[PRM TSI, Annex §4.2.2.3.2](https://eur-lex.europa.eu/x)" in md
    assert "> shall have a minimum clear useable width of 800 mm" in md
    assert "Needs a person (missing data)" in md
    assert "1 tool calls, 2 model calls" in md


def test_markdown_is_deterministic():
    assert to_markdown(make_report()) == to_markdown(make_report())


def test_describe_rule():
    assert describe_rule(">=", 800, "mm") == "≥ 800 mm"
    assert describe_rule("<=", 230.5, "mm") == "≤ 230.5 mm"
    assert describe_rule(">=", 2, None) == "≥ 2"
    assert describe_rule(None, None, None) == ""
