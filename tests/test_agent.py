import itertools

import pytest

from rail_compliance.agent import ComplianceAgent, tool_definitions
from rail_compliance.models import (
    Band,
    Condition,
    RequirementCore,
    RequirementDraft,
    SearchResult,
)
from rail_compliance.parameters import CHECKED_PARAMETERS, SUBJECT_OF
from rail_compliance.retry import LLMUnavailable
from rail_compliance.spec import TrainSpec
from tests.fakes import ScriptedAgentLLM, ai, tool_call
from tests.test_extract import (
    DOOR_PASSAGE,
    DOORS,
    QUOTE_800,
    TABLE,
    TABLE_PASSAGE,
    TOILET,
    door_draft,
    toilet_draft,
)

DOOR = "exterior_doors.clear_width_mm"
WC_DOOR = "exterior_doors.wheelchair_door_clear_width_mm"
LEVEL = "exterior_doors.wheelchair_door_level_access"
ALL_PASSAGES = [DOOR_PASSAGE, TABLE_PASSAGE, TOILET]


class FakeSearch:
    name = "fake"

    def __init__(self):
        self.questions = []

    def search(self, question, k):
        self.questions.append(question)
        return SearchResult(question=question, passages=ALL_PASSAGES[:k], backend="fake")


class FakeExtractor:
    """Pops one draft per extract call (None means: reply that nothing was found)."""

    def __init__(self, drafts):
        self.drafts, self.prompts = list(drafts), []

    def extract(self, system, user, schema):
        self.prompts.append(user)
        draft = self.drafts.pop(0)
        return draft or RequirementDraft(found=False, note="no numeric rule in these passages")


def spec(**kw) -> TrainSpec:
    return TrainSpec.model_validate({"name": "t", "unit_length_m": 120.0, **kw})


def run(spec_, script, drafts=(), **agent_kw):
    llm, extractor, search = ScriptedAgentLLM(script), FakeExtractor(drafts), FakeSearch()
    ticks = itertools.count()
    agent = ComplianceAgent(llm, extractor, search, clock=lambda: next(ticks) * 0.5, **agent_kw)
    return agent.run(spec_), llm, extractor, search


def search_call(q="minimum clear width of exterior doors"):
    return ai(tool_call("search_regulation", question=q))


def extract_call(parameter, ids=(DOOR_PASSAGE.id,), focus=None):
    return ai(
        tool_call("extract_requirement", passage_ids=list(ids), parameter=parameter, focus=focus)
    )


def check_call(parameter, value, rid="R1"):
    return ai(tool_call("check", parameter=parameter, spec_value=value, requirement_id=rid))


DONE = ai(text="Checked.")


def agent_calls(report, parameter=None):
    return [t for t in report.trace if t.source == "agent" and (parameter in (None, t.parameter))]


def test_the_model_sees_four_tools_with_argument_schemas():
    tools = {t.name: t for t in tool_definitions()}
    assert set(tools) == {"search_regulation", "extract_requirement", "check", "needs_human"}
    assert set(tools["check"].args) == {"parameter", "spec_value", "requirement_id"}


def test_a_passing_parameter_follows_search_extract_check():
    script = [search_call(), extract_call(DOOR), check_call(DOOR, 850), DONE]
    report, llm, _, search = run(
        spec(exterior_doors={"clear_width_mm": 850}), script, [door_draft()]
    )
    result = report.result_for(DOOR)
    assert result.verdict == "pass"
    assert result.requirement == "≥ 800 mm"
    assert result.spec_value == 850
    assert result.citations[0].quote == QUOTE_800
    assert result.citations[0].passage_id == DOOR_PASSAGE.id
    assert [t.name for t in agent_calls(report, DOOR)] == [
        "search_regulation",
        "extract_requirement",
        "check",
    ]
    assert all(t.ok for t in report.trace)
    assert report.stats.llm_calls == 4
    assert report.stats.tool_calls == 3
    assert report.stats.agent_model == "scripted:agent"
    assert report.stats.search_backend == "fake"
    assert search.questions == ["minimum clear width of exterior doors"]


def test_a_violation_is_a_fail_with_the_margin():
    script = [search_call(), extract_call(DOOR), check_call(DOOR, 780), DONE]
    report, *_ = run(spec(exterior_doors={"clear_width_mm": 780}), script, [door_draft()])
    result = report.result_for(DOOR)
    assert result.verdict == "fail"
    assert result.checks[0].margin == -20
    assert "780" in result.reason


def test_a_value_exactly_at_the_limit_passes():
    script = [search_call(), extract_call(DOOR), check_call(DOOR, 800), DONE]
    report, *_ = run(spec(exterior_doors={"clear_width_mm": 800}), script, [door_draft()])
    assert report.result_for(DOOR).verdict == "pass"


def test_parameters_the_spec_omits_are_needs_human_without_calling_the_model():
    report, llm, extractor, search = run(spec(), [])
    assert [r.parameter for r in report.results] == list(CHECKED_PARAMETERS)
    assert all(r.verdict == "needs_human" for r in report.results)
    assert all(r.reviews[0].category == "missing_data" for r in report.results)
    assert llm.seen == [] and extractor.prompts == [] and search.questions == []
    assert report.stats.llm_calls == 0
    assert (
        report.stats.tool_calls == 0
    )  # runtime decisions are traced but not counted as agent calls
    assert {t.source for t in report.trace} == {"runtime"}


def test_a_wrong_spec_value_is_rejected_and_never_used():
    script = [
        search_call(),
        extract_call(DOOR),
        check_call(DOOR, 7.8),  # mis-copied
        check_call(DOOR, 780),
        DONE,
    ]
    report, *_ = run(spec(exterior_doors={"clear_width_mm": 780}), script, [door_draft()])
    checks = [t for t in report.trace if t.name == "check"]
    assert [t.ok for t in checks] == [False, True]
    assert "does not match the spec" in checks[0].summary
    result = report.result_for(DOOR)
    assert result.verdict == "fail"
    assert len(result.checks) == 1  # only the accepted call produced a result


def test_a_conditional_rule_that_does_not_apply_leads_to_the_general_rule():
    speed_rule = RequirementCore(
        parameter=WC_DOOR,
        subject=SUBJECT_OF[WC_DOOR],
        comparator=">=",
        value=1000,
        unit="mm",
        conditions=[
            Condition(variable="design_speed_kmh", op="<", value=250),
            Condition(variable=LEVEL, op="==", value=1),
        ],
    )
    quote = DOORS[DOORS.index("On trains") :]
    speed_draft = door_draft(quote=quote, rule=speed_rule)
    general = door_draft(
        rule=RequirementCore(
            parameter=WC_DOOR, subject=SUBJECT_OF[WC_DOOR], comparator=">=", value=800, unit="mm"
        )
    )
    script = [
        search_call("wheelchair door width"),
        extract_call(WC_DOOR, focus="wheelchair doors on trains slower than 250 km/h"),
        check_call(WC_DOOR, 900, "R1"),
        extract_call(WC_DOOR, focus="the general minimum for all doorways"),
        check_call(WC_DOOR, 900, "R2"),
        DONE,
    ]
    fast = spec(
        design_speed_kmh=300,
        exterior_doors={
            "wheelchair_door_clear_width_mm": 900,
            "wheelchair_door_level_access": True,
        },
    )
    report, _, extractor, _ = run(fast, script, [speed_draft, general])
    result = report.result_for(WC_DOOR)
    assert [c.verdict for c in result.checks] == ["not_applicable", "pass"]
    assert result.verdict == "pass"
    assert result.requirement == "≥ 800 mm"
    assert "slower than 250" in extractor.prompts[0]

    slow = spec(
        design_speed_kmh=160,
        exterior_doors={
            "wheelchair_door_clear_width_mm": 900,
            "wheelchair_door_level_access": True,
        },
    )
    report, *_ = run(slow, script, [speed_draft, general])
    result = report.result_for(WC_DOOR)
    assert [c.verdict for c in result.checks] == ["fail", "pass"]
    assert result.verdict == "fail"  # 900 < 1000 where it applies, even though 800 is met


def test_missing_data_that_a_rule_depends_on_becomes_needs_human():
    speed_rule = RequirementCore(
        parameter=WC_DOOR,
        subject=SUBJECT_OF[WC_DOOR],
        comparator=">=",
        value=1000,
        unit="mm",
        conditions=[Condition(variable="design_speed_kmh", op="<", value=250)],
    )
    draft = door_draft(quote=DOORS[DOORS.index("On trains") :], rule=speed_rule)
    script = [search_call(), extract_call(WC_DOOR), check_call(WC_DOOR, 900), DONE]
    no_speed = spec(exterior_doors={"wheelchair_door_clear_width_mm": 900})
    report, *_ = run(no_speed, script, [draft])
    result = report.result_for(WC_DOOR)
    assert result.verdict == "needs_human"
    assert "design_speed_kmh" in result.reason


def test_a_table_rule_uses_the_unit_length_from_the_spec():
    bands = [
        Band(upper=30, upper_inclusive=False, value=1),
        Band(lower=30, upper=205, value=2),
        Band(lower=205, lower_inclusive=False, upper=300, value=3),
        Band(lower=300, lower_inclusive=False, value=4),
    ]
    rule = RequirementCore(
        parameter="wheelchair_spaces",
        subject=SUBJECT_OF["wheelchair_spaces"],
        comparator=">=",
        bands=bands,
        band_variable="unit_length_m",
    )
    draft = RequirementDraft(
        found=True,
        passage_id=TABLE_PASSAGE.id,
        quote=TABLE[TABLE.index("Less than 30 m") :],
        rule=rule,
    )
    script = [
        search_call("wheelchair spaces per unit length"),
        extract_call("wheelchair_spaces", ids=[TABLE_PASSAGE.id]),
        check_call("wheelchair_spaces", 1),
        DONE,
    ]
    report, *_ = run(spec(wheelchair_spaces=1), script, [draft])  # 120 m needs 2
    result = report.result_for("wheelchair_spaces")
    assert result.verdict == "fail"
    assert result.requirement == "≥ 2"
    assert result.checks[0].required_value == 2


def test_an_unverified_extraction_is_escalated_by_the_model():
    bad = door_draft(quote="Doors must be at least 800 mm wide.")  # not in the passage
    script = [
        search_call(),
        extract_call(DOOR),
        ai(tool_call("needs_human", reason="The extracted quote could not be verified.",
                     category="weak_citation")),
    ]  # fmt: skip
    report, *_ = run(spec(exterior_doors={"clear_width_mm": 850}), script, [bad])
    result = report.result_for(DOOR)
    assert result.verdict == "needs_human"
    assert result.reviews[0].category == "weak_citation"
    assert result.checks == []
    extract = next(t for t in report.trace if t.name == "extract_requirement")
    assert "unverified" in extract.summary
    assert [t.name for t in agent_calls(report, DOOR)][-1] == "needs_human"


def test_needs_human_ends_the_parameter_without_another_model_turn():
    script = [
        ai(tool_call("needs_human", reason="The rule is in an external standard.",
                     category="ambiguous_law")),
    ]  # fmt: skip
    report, llm, *_ = run(spec(exterior_doors={"clear_width_mm": 850}), script)
    assert report.result_for(DOOR).verdict == "needs_human"
    assert len(llm.seen) == 1


def test_a_model_that_stops_without_a_verdict_is_needs_human():
    report, *_ = run(spec(exterior_doors={"clear_width_mm": 850}), [DONE])
    result = report.result_for(DOOR)
    assert result.verdict == "needs_human"
    assert "without checking" in result.reason
    assert result.reviews[0].category == "other"


def test_the_tool_call_budget_stops_a_looping_model():
    script = [search_call(f"question number {i}") for i in range(3)]
    report, llm, *_ = run(spec(exterior_doors={"clear_width_mm": 850}), script, max_calls=3)
    result = report.result_for(DOOR)
    assert result.verdict == "needs_human"
    assert "budget of 3" in result.reason
    assert len(llm.seen) == 3


def test_budget_exhaustion_does_not_hide_a_failure_already_found():
    script = [search_call(), extract_call(DOOR), check_call(DOOR, 780)]
    report, *_ = run(
        spec(exterior_doors={"clear_width_mm": 780}), script, [door_draft()], max_calls=3
    )
    assert report.result_for(DOOR).verdict == "fail"


@pytest.mark.parametrize(
    ("call", "expected"),
    [
        (ai(tool_call("fly_to_the_moon")), "unknown tool"),
        (ai(tool_call("search_regulation")), "invalid arguments"),
        (extract_call(DOOR), "call search_regulation first"),
        (
            ai(tool_call("check", parameter=DOOR, spec_value=850.0, requirement_id="R9")),
            "unknown requirement",
        ),
        (search_call("hi"), "search failed"),
    ],
)
def test_bad_calls_are_rejected_with_a_message_and_the_loop_continues(call, expected):
    report, *_ = run(spec(exterior_doors={"clear_width_mm": 850}), [call, DONE])
    rejected = agent_calls(report, DOOR)[0]
    assert rejected.ok is False
    assert expected in rejected.summary
    assert report.result_for(DOOR).verdict == "needs_human"


def test_extracting_for_another_parameter_is_rejected():
    script = [search_call(), extract_call("steps.external_step_height_mm"), DONE]
    report, *_ = run(spec(exterior_doors={"clear_width_mm": 850}), script)
    extract = next(t for t in report.trace if t.name == "extract_requirement")
    assert extract.ok is False
    assert "you are checking" in extract.summary


def test_unknown_passage_ids_are_rejected_and_the_known_ones_listed():
    script = [search_call(), extract_call(DOOR, ids=["tsi-prm:made-up#1"]), DONE]
    report, *_ = run(spec(exterior_doors={"clear_width_mm": 850}), script)
    extract = next(t for t in report.trace if t.name == "extract_requirement")
    assert extract.ok is False
    assert "made-up" in extract.summary
    assert DOOR_PASSAGE.id in extract.summary


def test_the_existence_rule_for_universal_toilets():
    script = [
        search_call("universal toilet"),
        extract_call("toilets.universal", ids=[TOILET.id]),
        check_call("toilets.universal", 0),
        DONE,
    ]
    report, *_ = run(spec(toilets={"fitted": 2, "universal": 0}), script, [toilet_draft()])
    result = report.result_for("toilets.universal")
    assert result.verdict == "fail"
    assert result.requirement == "≥ 1"


def test_a_rule_that_does_not_apply_is_not_applicable_not_a_pass():
    script = [
        search_call("universal toilet"),
        extract_call("toilets.universal", ids=[TOILET.id]),
        check_call("toilets.universal", 0),
        DONE,
    ]
    report, *_ = run(spec(toilets={"fitted": 0, "universal": 0}), script, [toilet_draft()])
    assert report.result_for("toilets.universal").verdict == "not_applicable"


def test_parameters_are_checked_in_registry_order_and_reported_in_that_order():
    script = [
        search_call(), extract_call(DOOR), check_call(DOOR, 850), DONE,
        search_call(), extract_call("toilets.universal", ids=[TOILET.id]),
        check_call("toilets.universal", 1), DONE,
    ]  # fmt: skip
    s = spec(exterior_doors={"clear_width_mm": 850}, toilets={"fitted": 1, "universal": 1})
    report, *_ = run(s, script, [door_draft(), toilet_draft()])
    assert [r.parameter for r in report.results] == list(CHECKED_PARAMETERS)
    assert report.result_for(DOOR).verdict == "pass"
    assert report.result_for("toilets.universal").verdict == "pass"
    agent_params = [t.parameter for t in agent_calls(report)]
    assert agent_params.index(DOOR) < agent_params.index("toilets.universal")
    assert [t.index for t in report.trace] == list(range(len(report.trace)))


def test_tool_call_latency_is_recorded():
    script = [search_call(), DONE]
    report, *_ = run(spec(exterior_doors={"clear_width_mm": 850}), script)
    assert agent_calls(report, DOOR)[0].seconds == 0.5  # the fake clock ticks 0.5 s per read
    assert report.stats.seconds > 0


def test_a_provider_outage_aborts_the_run_instead_of_recording_garbage():
    def outage(messages):
        raise LLMUnavailable("quota spent")

    with pytest.raises(LLMUnavailable):
        run(spec(exterior_doors={"clear_width_mm": 850}), [outage])


def test_one_rule_passing_does_not_hide_an_unresolved_one():
    general = door_draft(
        rule=RequirementCore(
            parameter=WC_DOOR, subject=SUBJECT_OF[WC_DOOR], comparator=">=", value=800, unit="mm"
        )
    )
    speed_rule = RequirementCore(
        parameter=WC_DOOR,
        subject=SUBJECT_OF[WC_DOOR],
        comparator=">=",
        value=1000,
        unit="mm",
        conditions=[Condition(variable="design_speed_kmh", op="<", value=250)],
    )
    conditional = door_draft(quote=DOORS[DOORS.index("On trains") :], rule=speed_rule)
    script = [
        search_call(),
        extract_call(WC_DOOR, focus="the general minimum"),
        check_call(WC_DOOR, 900, "R1"),  # passes
        extract_call(WC_DOOR, focus="the rule for slow trains"),
        check_call(WC_DOOR, 900, "R2"),  # depends on design speed, which the spec omits
        DONE,
    ]
    no_speed = spec(exterior_doors={"wheelchair_door_clear_width_mm": 900})
    report, *_ = run(no_speed, script, [general, conditional])
    result = report.result_for(WC_DOOR)
    assert [c.verdict for c in result.checks] == ["pass", "needs_human"]
    assert result.verdict == "needs_human"


def test_an_escalation_after_a_passing_check_is_still_needs_human():
    script = [
        search_call(),
        extract_call(DOOR),
        check_call(DOOR, 850),
        ai(tool_call("needs_human", reason="A footnote may allow an exception.",
                     category="ambiguous_law")),
    ]  # fmt: skip
    report, *_ = run(spec(exterior_doors={"clear_width_mm": 850}), script, [door_draft()])
    result = report.result_for(DOOR)
    assert result.checks[0].verdict == "pass"
    assert result.verdict == "needs_human"


def test_an_unparseable_extraction_is_a_rejected_call_the_model_can_recover_from():
    from rail_compliance.tools.extract import StructuredOutputError

    class Flaky(FakeExtractor):
        def extract(self, system, user, schema):
            if not self.prompts:
                self.prompts.append(user)
                raise StructuredOutputError("could not parse the extraction reply")
            return super().extract(system, user, schema)

    llm = ScriptedAgentLLM(
        [search_call(), extract_call(DOOR), extract_call(DOOR), check_call(DOOR, 850), DONE]
    )
    extractor = Flaky([door_draft()])
    agent = ComplianceAgent(llm, extractor, FakeSearch())
    report = agent.run(spec(exterior_doors={"clear_width_mm": 850}))
    extracts = [t for t in report.trace if t.name == "extract_requirement"]
    assert [t.ok for t in extracts] == [False, True]
    assert "could not parse" in extracts[0].summary
    assert report.result_for(DOOR).verdict == "pass"


def test_the_system_prompt_asks_for_general_and_special_case_rules_and_whole_tables():
    from rail_compliance.agent import SYSTEM_PROMPT

    text = " ".join(SYSTEM_PROMPT.split())
    assert "Extract the rule for each listed subject" in text
    assert "single call, never row by row" in text
    assert "contingency" in text


# --- run 01 causes A-D: settle precedence, contingent exceptions, intervals, subjects ----------

INT = "steps.internal_step_height_mm"


def internal_step_drafts(contingent=True):
    """The two rules of 4.2.2.11.2(2): 200 mm, and 230 mm if it reduces the number of steps."""
    from tests.test_extract import EXCEPTION_QUOTE, STEP_PASSAGE

    general_quote = (
        "Internal steps for external access shall have a minimum depth of 240 mm between the "
        "vertical edges of the step and a maximum height of 200 mm."
    )
    general = RequirementDraft(
        found=True,
        passage_id=STEP_PASSAGE.id,
        quote=general_quote,
        rule=RequirementCore(
            parameter=INT, subject="internal_step", comparator="<=", value=200, unit="mm"
        ),
    )
    exception = RequirementDraft(
        found=True,
        passage_id=STEP_PASSAGE.id,
        quote=EXCEPTION_QUOTE,
        rule=RequirementCore(
            parameter=INT, subject="internal_step", comparator="<=", value=230, unit="mm",
            contingency="a demonstrated reduction of one in the total number of steps"
            if contingent else None,
        ),
    )  # fmt: skip
    return general, exception


def step_script():
    return [
        search_call("maximum internal step height"),
        extract_call(INT, ids=["tsi-prm:Annex §4.2.2.11.2#1"], focus="the general limit"),
        extract_call(INT, ids=["tsi-prm:Annex §4.2.2.11.2#1"], focus="the exception"),
        check_call(INT, None, "R1"),
        check_call(INT, None, "R2"),
        DONE,
    ]


def run_step(value, escalate=False, contingent=True, drafts=None):
    from tests.test_extract import STEP_PASSAGE

    script = step_script()
    for i in (3, 4):  # fill in the spec value
        call_ = script[i].tool_calls[0]
        call_["args"]["spec_value"] = float(value)
    if escalate:
        script[-1] = ai(
            tool_call("needs_human", reason="An exception may apply that I cannot evaluate.",
                      category="ambiguous_law")
        )  # fmt: skip
    llm, extractor = (
        ScriptedAgentLLM(script),
        FakeExtractor(drafts or internal_step_drafts(contingent)),
    )

    class StepSearch(FakeSearch):
        def search(self, question, k):
            return SearchResult(question=question, passages=[STEP_PASSAGE], backend="fake")

    agent = ComplianceAgent(llm, extractor, StepSearch())
    return agent.run(spec(steps={"internal_step_height_mm": float(value)})).result_for(INT)


def test_a_contingent_exception_that_would_allow_the_value_makes_it_needs_human():
    result = run_step(215)  # fails 200 mm; the 230 mm exception would allow it if demonstrated
    assert result.verdict == "needs_human"
    assert "demonstrated reduction" in result.reason
    assert [c.verdict for c in result.checks] == ["fail", "pass"]


def test_the_contingent_exception_does_not_matter_when_the_general_limit_is_met():
    assert run_step(180).verdict == "pass"


def test_a_value_beyond_even_the_exception_is_a_fail():
    assert run_step(231).verdict == "fail"


def test_an_exception_extracted_without_a_contingency_would_hide_the_problem():
    # documents why the contingency matters: unconditional, the 230 mm rule passes and the 200 mm
    # rule fails, and with no escalation the parameter is simply a fail
    assert run_step(215, contingent=False).verdict == "fail"


def test_the_models_own_escalation_is_binding_even_after_a_failed_check():
    result = run_step(215, escalate=True, contingent=False)
    assert result.verdict == "needs_human"
    assert any(c.verdict == "fail" for c in result.checks)  # the failure stays visible
    assert "exception may apply" in result.reason


def test_only_the_contingent_rule_extracted_still_needs_a_person():
    from tests.test_extract import STEP_PASSAGE

    _, exception = internal_step_drafts()
    script = [
        search_call("maximum internal step height"),
        extract_call(INT, ids=[STEP_PASSAGE.id]),
        check_call(INT, 215, "R1"),
        DONE,
    ]

    class StepSearch(FakeSearch):
        def search(self, question, k):
            return SearchResult(question=question, passages=[STEP_PASSAGE], backend="fake")

    agent = ComplianceAgent(ScriptedAgentLLM(script), FakeExtractor([exception]), StepSearch())
    result = agent.run(spec(steps={"internal_step_height_mm": 215.0})).result_for(INT)
    assert result.verdict == "needs_human" and "demonstrated" in result.reason


def power_head_table_run(spaces_value, includes_head):
    bands = [
        Band(upper=30, upper_inclusive=False, value=1),
        Band(lower=30, upper=205, value=2),
        Band(lower=205, lower_inclusive=False, upper=300, value=3),
        Band(lower=300, lower_inclusive=False, value=4),
    ]
    rule = RequirementCore(
        parameter="wheelchair_spaces", subject="wheelchair_space", comparator=">=", bands=bands,
        band_variable="unit_length_m",
    )  # fmt: skip
    draft = RequirementDraft(
        found=True, passage_id=TABLE_PASSAGE.id, quote=TABLE[TABLE.index("Less than 30 m") :],
        rule=rule,
    )  # fmt: skip
    script = [
        search_call("wheelchair spaces"),
        extract_call("wheelchair_spaces", ids=[TABLE_PASSAGE.id]),
        check_call("wheelchair_spaces", float(spaces_value)),
        DONE,
    ]
    s = spec(
        unit_length_m=210.0,
        length_includes_power_head=includes_head,
        wheelchair_spaces=spaces_value,
    )
    return run(s, script, [draft])[0].result_for("wheelchair_spaces")


def test_a_length_that_includes_a_power_head_is_decided_over_the_possible_lengths():
    assert power_head_table_run(3, True).verdict == "pass"  # enough for any length up to 210 m
    assert power_head_table_run(2, True).verdict == "needs_human"
    assert power_head_table_run(0, True).verdict == "fail"


def test_without_the_power_head_flag_the_stated_length_is_used():
    assert power_head_table_run(2, False).verdict == "fail"  # 210 m needs 3
    assert power_head_table_run(3, None).verdict == "pass"


def test_the_task_message_lists_the_subjects_that_govern_the_parameter():
    spec_ = spec(exterior_doors={"clear_width_mm": 850, "wheelchair_door_clear_width_mm": 900})
    llm = ScriptedAgentLLM([DONE, DONE])
    ComplianceAgent(llm, FakeExtractor([]), FakeSearch()).run(spec_)
    messages = {m[1].content.split("\n")[0]: m[1].content for m in llm.seen}
    wheelchair = messages[f"Parameter to check: {WC_DOOR} (mm)"]
    assert "wheelchair_doorway, exterior_doorway" in wheelchair
    clear = messages["Parameter to check: exterior_doors.clear_width_mm (mm)"]
    assert "(own subject first): exterior_doorway" in clear
    assert "wheelchair_doorway" not in clear
