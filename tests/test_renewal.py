"""Renewed units (Appendix F): an exemption is a rule that says another rule need not be met where
its conditions hold ("compliance with 4.2.2.9 is only mandatory where existing handrails are being
renewed or upgraded")."""

import pytest
from pydantic import ValidationError

from rail_compliance.agent import Scratch, _settle
from rail_compliance.models import Condition, RequirementCore
from rail_compliance.spec import TrainSpec, spec_categories, spec_values
from rail_compliance.tools.check import check
from tests.factories import passage

RAIL = "handrails.outside_diameter_mm"
RENEWED = Condition(variable="unit_status", op="==", value="renewed")
KEPT = Condition(variable="renewal.handrails_renewed", op="==", value=0)


def diameter():
    from rail_compliance.models import Requirement
    from tests.factories import CITATION

    return Requirement(parameter=RAIL, subject="handrail", comparator="between", value=30,
                       value_max=40, unit="mm", citation=CITATION)  # fmt: skip


def exemption(conditions=(RENEWED, KEPT), contingency=None):
    return RequirementCore(parameter=RAIL, subject="handrail", comparator="exempt",
                           conditions=list(conditions), contingency=contingency)  # fmt: skip


def as_requirement(core):
    from rail_compliance.models import Requirement
    from tests.factories import CITATION

    return Requirement(**core.model_dump(), citation=CITATION)


def settle(value, context, rules=None):
    scratch = Scratch(parameter=RAIL)
    for rule in rules or (diameter(), as_requirement(exemption())):
        scratch.checks.append((check(value, rule, spec_unit="mm", context=context), rule))
    return _settle(scratch, {RAIL: value})


# --- the spec --------------------------------------------------------------------------------


def test_a_unit_is_new_unless_the_spec_says_it_was_renewed():
    s = TrainSpec(name="t", unit_length_m=100)
    assert spec_categories(s) == {"unit_status": "new"}


def test_what_was_renewed_is_given_as_flags():
    renewal = {"handrails_renewed": False, "toilets_completely_renewed": True}
    s = TrainSpec(name="t", unit_length_m=100, unit_status="renewed", renewal=renewal)
    values = spec_values(s)
    assert (
        values["renewal.handrails_renewed"] == 0
        and values["renewal.toilets_completely_renewed"] == 1
    )


def test_renewal_details_on_a_new_unit_are_an_error():
    with pytest.raises(ValidationError, match="renewed"):
        TrainSpec(name="t", unit_length_m=100, renewal={"handrails_renewed": True})


def test_a_layout_altered_in_the_entire_train_is_altered_in_every_vehicle():
    with pytest.raises(ValidationError, match="vehicle"):
        TrainSpec(name="t", unit_length_m=100, unit_status="renewed",
                  renewal={"seating_layout_altered_in_entire_train": True,
                           "seating_layout_altered_in_entire_vehicle": False})  # fmt: skip


# --- the rule shape --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fields",
    [
        {"comparator": "exempt"},  # no conditions: it would cancel the rule everywhere
        {"comparator": "exempt", "value": 30, "conditions": [RENEWED]},  # an exemption has no value
    ],
)
def test_a_malformed_exemption_is_rejected(fields):
    with pytest.raises(ValidationError, match="exempt"):
        RequirementCore(parameter=RAIL, subject="handrail", **fields)


def test_check_reports_an_exemption_that_holds_as_exempt():
    renewed_kept = {"unit_status": "renewed", "renewal.handrails_renewed": 0}
    r = check(45, as_requirement(exemption()), context=renewed_kept)
    assert (r.verdict, r.exempts, r.applies) == ("not_applicable", True, True)
    assert "not mandatory" in r.reason
    r = check(45, as_requirement(exemption()), context={"unit_status": "new"})
    assert (r.verdict, r.applies) == ("not_applicable", False)


# --- settling --------------------------------------------------------------------------------

NEW = {"unit_status": "new"}
KEPT_RAILS = {"unit_status": "renewed", "renewal.handrails_renewed": 0}
NEW_RAILS = {"unit_status": "renewed", "renewal.handrails_renewed": 1}
UNSTATED = {"unit_status": "renewed"}


@pytest.mark.parametrize(
    ("value", "context", "verdict"),
    [
        (45, NEW, "fail"),
        (35, NEW, "pass"),
        (45, KEPT_RAILS, "not_applicable"),  # exempt: the handrails were not renewed
        (35, KEPT_RAILS, "not_applicable"),
        (45, NEW_RAILS, "fail"),  # renewed handrails must comply
        (45, UNSTATED, "needs_human"),  # exempt only if the handrails were kept: unknown
        (35, UNSTATED, "pass"),  # complies either way
    ],
)
def test_an_exemption_that_holds_makes_the_rule_not_applicable(value, context, verdict):
    result = settle(value, context)
    assert result.verdict == verdict, result.reason


def test_the_reason_names_the_exemption():
    reason = settle(45, KEPT_RAILS).reason
    assert "exempt" in reason and "renewal.handrails_renewed" in reason


def test_a_contingent_exemption_turns_a_failure_into_a_question():
    cont = as_requirement(exemption([RENEWED], contingency="the work would need structural "
                                    "alterations to the door portals"))  # fmt: skip
    failing = settle(45, NEW_RAILS, rules=[diameter(), cont])
    assert failing.verdict == "needs_human" and "structural" in failing.reason
    assert settle(35, NEW_RAILS, rules=[diameter(), cont]).verdict == "pass"


# --- extraction ------------------------------------------------------------------------------

HANDRAILS_F = (
    "Compliance with the requirements of point 4.2.2.9 is only mandatory where existing handrails "
    "are being renewed or upgraded."
)


def extract_exemption(quote, conditions=(RENEWED, KEPT)):
    from rail_compliance.models import RequirementDraft
    from rail_compliance.tools.extract import extract_requirement
    from tests.factories import passage
    from tests.test_extract import FakeLLM

    p = passage(HANDRAILS_F, id_="tsi-prm:Appendix F §Handrails#1", section="Appendix F §Handrails")
    draft = RequirementDraft(found=True, passage_id=p.id, quote=quote,
                             rule=exemption(conditions))  # fmt: skip
    return extract_requirement([p], RAIL, FakeLLM(draft))


def test_an_exemption_is_verified_against_its_quote():
    assert extract_exemption(HANDRAILS_F).status == "found"


def test_an_exemption_must_quote_that_compliance_is_not_mandatory():
    result = extract_exemption("existing handrails are being renewed or upgraded")
    assert result.status == "unverified" and "mandatory" in result.reason


def test_renewal_wording_names_the_renewed_category():
    from rail_compliance.tools.extract import _category_stated

    assert _category_stated("renewed", "is not mandatory at renewal or upgrade")
    assert _category_stated("renewed", "being renewed or upgraded")
    assert not _category_stated("renewed", "placed on the market after 28 September 2023")


def test_an_exemption_must_be_conditioned_on_a_renewed_unit():
    result = extract_exemption(HANDRAILS_F, conditions=[KEPT])
    assert result.status == "unverified" and "unit_status" in result.reason


def test_none_of_a_count_needs_no_zero_in_the_quote():
    from rail_compliance.tools.extract import _is_existence

    assert _is_existence(Condition(variable="wheelchair_spaces", op="==", value=0))


def test_only_a_renewed_unit_is_told_to_look_for_exemptions():
    from rail_compliance.agent import _task_message

    values = {RAIL: 45.0}
    new = _task_message(RAIL, values, {"unit_status": "new"})
    renewed = _task_message(RAIL, values, {"unit_status": "renewed"})
    assert "Appendix F" not in new and "renewal.handrails_renewed" not in new
    assert "Appendix F" in renewed and "renewal.handrails_renewed" in renewed


def test_a_quote_from_appendix_f_states_a_renewal_without_the_word():
    from rail_compliance.tools.extract import _category_stated

    quote = "The provision of wheelchair spaces is only required when the seating layout is altered"
    assert _category_stated("renewed", quote, "Appendix F §Wheelchair spaces")
    assert not _category_stated("renewed", quote, "Annex §4.2.2.2")


# --- found by the first run of the renewal suite (4/11) -----------------------------------------
# r03, r10: the agent never searched Appendix F, though the task asked it to.
# r04: the exemption could not be decided, so the agent escalated a value that passes either way.
# r06, r08: exemptions encoded as limits ("number 1 not stated", "exactly one of value or bands").


def appendix_f(section, text):
    return passage(text, id_=f"tsi-prm:Appendix F §{section}#1", section=f"Appendix F §{section}")


APPENDIX_PASSAGES = [
    appendix_f("Handrails", HANDRAILS_F),
    appendix_f("Structures", "Compliance is not mandatory if the work would require structural "
                             "alterations to door portals."),
]  # fmt: skip


class RecordingSearch:
    """Answers the runtime's Appendix F queries, and fails on request."""

    name = "fake"

    def __init__(self, passages=APPENDIX_PASSAGES, fail=False):
        self.questions, self.passages, self.fail = [], passages, fail

    def search(self, question, k):
        from rail_compliance.models import SearchResult
        from rail_compliance.tools.search import SearchError

        self.questions.append(question)
        if self.fail:
            raise SearchError("down")
        return SearchResult(question=question, passages=self.passages, backend="fake")


def run_agent(spec, search, script=(), drafts=()):
    import itertools

    from rail_compliance.agent import ComplianceAgent
    from tests.fakes import ScriptedAgentLLM, ai
    from tests.test_agent import FakeExtractor

    llm = ScriptedAgentLLM(list(script) or [ai(text="Checked.")] * 40)
    ticks = itertools.count()
    agent = ComplianceAgent(
        llm, FakeExtractor(list(drafts)), search, clock=lambda: next(ticks) * 0.5
    )
    return agent.run(spec), llm


def renewed_spec(**kw):
    return TrainSpec(name="t", unit_length_m=100, unit_status="renewed",
                     handrails={"outside_diameter_mm": 45}, **kw)  # fmt: skip


def test_for_a_renewed_unit_the_runtime_searches_appendix_f_itself_and_says_so():
    search = RecordingSearch()
    report, llm = run_agent(renewed_spec(), search)
    mine = [t for t in report.trace if t.parameter == RAIL and t.source == "runtime"]
    assert [t.name for t in mine] == ["search_regulation"] * 2
    assert any("handrail" in q and "Appendix F" in q for q in search.questions)
    assert any("structural alterations" in q for q in search.questions)  # the clause for all
    first_message = llm.seen[0][1].content if isinstance(llm.seen[0], tuple) else str(llm.seen[0])
    assert "tsi-prm:Appendix F §Handrails#1" in first_message


def test_the_appendix_f_passages_can_be_extracted_from_without_a_search_by_the_model():
    report, _ = run_agent(renewed_spec(), RecordingSearch())
    assert not any(t.name == "search_regulation" and t.source == "agent" for t in report.trace)
    assert all(t.ok for t in report.trace if t.source == "runtime")


def test_a_new_unit_gets_no_runtime_search():
    search = RecordingSearch()
    new = TrainSpec(name="t", unit_length_m=100, handrails={"outside_diameter_mm": 45})
    report, _ = run_agent(new, search)
    ran = [t for t in report.trace if t.source == "runtime" and t.name == "search_regulation"]
    assert search.questions == [] and ran == []


def test_noise_is_not_searched_in_appendix_f_even_for_a_renewed_unit():
    search = RecordingSearch()
    noisy = TrainSpec(
        name="t", unit_length_m=100, unit_status="renewed", noise={"stationary_db": 60}
    )
    run_agent(noisy, search)
    assert search.questions == []


def test_only_appendix_f_passages_are_kept_from_the_runtime_search():
    mixed = [*APPENDIX_PASSAGES, passage("A handrail rule", id_="tsi-prm:Annex §4.2.2.9#1")]
    _, llm = run_agent(renewed_spec(), RecordingSearch(mixed))
    assert "Annex §4.2.2.9#1" not in str(llm.seen[0])


def test_a_failed_runtime_search_does_not_stop_the_agent():
    report, _ = run_agent(renewed_spec(), RecordingSearch(fail=True))
    assert report.result_for(RAIL).verdict == "needs_human"  # no rule extracted, escalated by code


def test_an_exemption_encoded_as_a_limit_is_told_what_an_exemption_looks_like():
    """r08: 'exactly one of value or bands'. r06: 'the number 1 is not stated'."""
    bare = RequirementCore.model_validate  # the schema-level message first
    with pytest.raises(ValidationError, match="exempt"):
        bare(dict(parameter=RAIL, subject="handrail", comparator=">="))
    from rail_compliance.models import RequirementDraft, RuleDraft
    from rail_compliance.tools.extract import extract_requirement
    from tests.test_extract import FakeLLM

    p = APPENDIX_PASSAGES[0]
    as_limit = RuleDraft(parameter=RAIL, subject="handrail", comparator=">=", value=1,
                         conditions=[RENEWED, KEPT])  # fmt: skip
    draft = RequirementDraft(found=True, passage_id=p.id, quote=HANDRAILS_F, rule=as_limit)
    result = extract_requirement([p], RAIL, FakeLLM(draft))
    assert result.status == "unverified" and "exempt" in result.reason


def test_an_exemption_the_spec_cannot_decide_does_not_ask_for_an_escalation():
    r = check(35, as_requirement(exemption()), context={"unit_status": "renewed"})
    assert r.verdict == "needs_human"
    assert "no verdict on its own" in r.reason


def test_the_prompts_cover_exemptions_that_cannot_be_decided_and_one_call_per_sentence():
    from rail_compliance.agent import SYSTEM_PROMPT
    from rail_compliance.tools.extract import SYSTEM

    flat = " ".join(SYSTEM.split())
    assert "its own exemption" in flat and "`contingency`" in flat
    agent = " ".join(SYSTEM_PROMPT.split())
    assert "Appendix F" in agent and "one call per" in agent
    assert "needs_human" in agent and "exemption" in agent


def test_the_runtime_search_itself_refuses_a_noise_parameter():
    """Renewed noise never reaches `begin` (it is decided in `plan`), so test the guard directly."""
    from rail_compliance.agent import Scratch, _Runner
    from tests.test_extract import FakeLLM

    runner = _Runner(RecordingSearch(), FakeLLM(None), 8)
    scratch = Scratch(parameter="noise.stationary_db", categories={"unit_status": "renewed"})
    assert runner.appendix_f(scratch, "noise.stationary_db", lambda: 0.0) == ([], [])


def test_an_appendix_f_passage_the_runtime_fetched_can_be_extracted_from_without_a_model_search():
    from rail_compliance.models import RequirementDraft
    from tests.fakes import ai, tool_call

    handrails = APPENDIX_PASSAGES[0]
    draft = RequirementDraft(found=True, passage_id=handrails.id, quote=HANDRAILS_F,
                             rule=exemption())  # fmt: skip
    script = [
        ai(
            tool_call("extract_requirement", passage_ids=[handrails.id], parameter=RAIL, focus=None)
        ),
        ai(text="Checked."),
    ]
    report, _ = run_agent(renewed_spec(), RecordingSearch(), script, drafts=[draft])
    extract = next(t for t in report.trace if t.name == "extract_requirement")
    assert extract.ok and extract.summary.startswith("found R1")
