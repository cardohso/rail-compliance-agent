"""A relaxation: a rule that permits a lower standard where its conditions hold ("for double deck
trains it is permitted to reduce this value to 270 mm"). Where it applies and the value meets it, a
failed general rule is excused; where it is unknown whether it applies, a person decides."""

import pytest
from pydantic import ValidationError

from rail_compliance.agent import Scratch, _settle
from rail_compliance.models import Condition, RequirementCore, RuleDraft
from rail_compliance.tools.check import check
from tests.factories import limit

DEPTH = "stairs.step_depth_mm"
DOUBLE = Condition(variable="deck_layout", op="==", value="double_deck")


def general():
    return limit(DEPTH, ">=", 280, "mm", subject="internal_stairs")


def relaxed():
    r = limit(DEPTH, ">=", 270, "mm", conditions=[DOUBLE], subject="internal_stairs")
    return r.model_copy(update={"relaxes": True})


def settle(value, deck=None, rules=None):
    context = {DEPTH: value} | ({"deck_layout": deck} if deck else {})
    scratch = Scratch(parameter=DEPTH)
    for rule in rules or (general(), relaxed()):
        scratch.checks.append((check(value, rule, spec_unit="mm", context=context), rule))
    return _settle(scratch, {DEPTH: value})


def test_check_reports_whether_a_rule_is_known_to_apply():
    assert check(275, relaxed(), context={"deck_layout": "double_deck"}).applies is True
    assert check(275, relaxed(), context={}).applies is None
    assert check(275, general()).applies is True
    assert check(275, relaxed(), context={}).relaxes is True


@pytest.mark.parametrize(
    ("value", "deck", "verdict"),
    [
        (285, "single_deck", "pass"),
        (275, "single_deck", "fail"),  # the relaxation does not apply
        (275, "double_deck", "pass"),  # it applies and excuses the 280 mm rule
        (265, "double_deck", "fail"),  # below the relaxed value too
        (275, None, "needs_human"),  # unknown whether it applies
        (285, None, "pass"),  # meets the general rule anyway
    ],
)
def test_a_relaxation_excuses_a_failed_general_rule_only_where_it_is_known_to_apply(
    value, deck, verdict
):
    result = settle(value, deck)
    assert result.verdict == verdict, result.reason


def test_the_excused_failure_is_stated_in_the_reason():
    reason = settle(275, "double_deck").reason
    assert "280" in reason and "270" in reason and "deck_layout == double_deck" in reason


def test_an_unknown_relaxation_says_what_would_decide_it():
    assert "deck_layout" in settle(275, None).reason


def test_a_relaxation_that_always_applied_would_cancel_the_rule_so_it_needs_a_condition():
    with pytest.raises(ValidationError, match="relax"):
        RequirementCore(parameter=DEPTH, subject="internal_stairs", comparator=">=", value=270,
                        relaxes=True)  # fmt: skip


STAIRS_TEXT = (
    "(1) Internal steps (other than those for external access) shall have a maximum height of "
    "200 mm and a minimum depth of 280 mm, measured at the central axis of the stairs. For double "
    "deck trains it is permitted to reduce this value to 270 mm for the stairs accessing the upper "
    "deck and the lower deck."
)


def relaxed_draft(quote):
    from rail_compliance.models import RequirementDraft
    from tests.factories import passage

    p = passage(STAIRS_TEXT, id_="tsi-prm:Annex §4.2.2.8#1")
    rule = RequirementCore(parameter=DEPTH, subject="internal_stairs", comparator=">=",
                           value=270, unit="mm", conditions=[DOUBLE], relaxes=True)  # fmt: skip
    return p, RequirementDraft(found=True, passage_id=p.id, quote=quote, rule=rule)


@pytest.mark.parametrize(
    ("quote", "status"),
    [
        ("For double deck trains it is permitted to reduce this value to 270 mm", "found"),
        # the number and the category are there, the permission is not
        ("For double deck trains ... 270 mm", "unverified"),
    ],
)
def test_a_relaxation_must_quote_the_permission(quote, status):
    from rail_compliance.tools.extract import extract_requirement
    from tests.test_extract import FakeLLM

    p, draft = relaxed_draft(quote)
    result = extract_requirement([p], DEPTH, FakeLLM(draft))
    assert result.status == status, result.reason


def test_a_relaxation_checked_alone_whose_application_is_unknown_is_not_a_pass():
    assert settle(275, None, rules=[relaxed()]).verdict == "needs_human"


@pytest.mark.parametrize(("deck", "verdict"), [("double_deck", "pass"), ("single_deck", "fail")])
def test_end_to_end_the_spec_deck_layout_decides_the_relaxation(deck, verdict):
    import itertools

    from rail_compliance.agent import ComplianceAgent
    from rail_compliance.models import RequirementDraft, SearchResult
    from rail_compliance.spec import TrainSpec
    from tests.factories import passage
    from tests.fakes import ScriptedAgentLLM, ai, tool_call
    from tests.test_agent import FakeExtractor

    stairs = passage(STAIRS_TEXT, id_="tsi-prm:Annex §4.2.2.8#1")

    class Search:
        name = "fake"

        def search(self, question, k):
            return SearchResult(question=question, passages=[stairs], backend="fake")

    general_rule = RequirementCore(parameter=DEPTH, subject="internal_stairs", comparator=">=",
                                   value=280, unit="mm")  # fmt: skip
    drafts = [
        RequirementDraft(found=True, passage_id=stairs.id, rule=general_rule,
                         quote="a minimum depth of 280 mm"),
        relaxed_draft("For double deck trains it is permitted to reduce this value to 270 mm")[1],
    ]  # fmt: skip
    script = [
        ai(tool_call("search_regulation", question="internal stair step depth")),
        ai(tool_call("extract_requirement", passage_ids=[stairs.id], parameter=DEPTH, focus=None)),
        ai(tool_call("extract_requirement", passage_ids=[stairs.id], parameter=DEPTH,
                     focus="double deck")),
        ai(tool_call("check", parameter=DEPTH, spec_value=275, requirement_id="R1")),
        ai(tool_call("check", parameter=DEPTH, spec_value=275, requirement_id="R2")),
        ai(text="Checked."),
    ]  # fmt: skip
    spec = TrainSpec.model_validate({"name": "t", "unit_length_m": 100.0, "deck_layout": deck,
                                     "stairs": {"step_depth_mm": 275}})  # fmt: skip
    ticks = itertools.count()
    agent = ComplianceAgent(ScriptedAgentLLM(script), FakeExtractor(drafts), Search(),
                            clock=lambda: next(ticks) * 0.5)  # fmt: skip
    result = agent.run(spec).result_for(DEPTH)
    assert result.verdict == verdict, result.reason


# --- found by the first runs of the new suites (core g08/g09, prm-extended p10) ----------------

CONTINGENT_QUOTE = (
    "The height of each step may be increased to a maximum of 230 mm if it can be demonstrated "
    "that this achieves a reduction of one in the total number of steps required."
)
HEIGHT = "steps.internal_step_height_mm"
STAIRS_QUOTE = "For double deck trains it is permitted to reduce this value to 270 mm"


def extract_height(rule_fields, quote=CONTINGENT_QUOTE):
    from rail_compliance.models import RequirementDraft
    from rail_compliance.tools.extract import extract_requirement
    from tests.factories import passage
    from tests.test_extract import FakeLLM

    extra = [
        "The height of each step may be increased to a maximum of 230 mm.",
        "For double deck trains the height of each step may be increased to a maximum of 230 mm.",
        "For double deck trains it is permitted to use 270 mm for the lower deck.",
    ]
    text = " ".join([CONTINGENT_QUOTE, STAIRS_QUOTE, quote, *extra])
    p = passage(text, id_="tsi-prm:Annex §4.2.2.11.2#1")
    base = dict(parameter=HEIGHT, subject="internal_step", comparator="<=", value=230, unit="mm")
    draft = RequirementDraft(found=True, passage_id=p.id, quote=quote,
                             rule=RuleDraft(**{**base, **rule_fields}))  # fmt: skip
    return extract_requirement([p], HEIGHT, FakeLLM(draft))


def test_a_demonstration_exception_filed_as_a_relaxation_is_told_what_it_is_instead():
    """The model marked 'if it can be demonstrated' as a relaxation with no conditions, which
    cost the agent the rule and two verdicts. The message must say what to do."""
    result = extract_height({"relaxes": True, "contingency": "a reduction of one in the steps"})
    assert result.status == "unverified"
    assert "contingency" in result.reason and "relaxes to false" in result.reason


def test_the_same_exception_as_a_contingency_is_found():
    result = extract_height({"contingency": "a reduction of one in the total number of steps"})
    assert result.status == "found"


@pytest.mark.parametrize(
    ("comparator", "status"),
    [
        (">=", "found"),  # a minimum may be reduced: that is a relaxation
        ("<=", "unverified"),  # a maximum cannot be relaxed by reducing it: that is stricter
    ],
)
def test_a_relaxation_must_move_the_limit_the_way_its_verb_says(comparator, status):
    """p10: 'reduce this value to 270 mm' was read as a new maximum for the step HEIGHT, which
    turned 210 mm from a fail into a pass."""
    result = extract_height({"comparator": comparator, "value": 270, "relaxes": True,
                             "conditions": [DOUBLE]}, quote=STAIRS_QUOTE)  # fmt: skip
    assert result.status == status, result.reason
    if status == "unverified":
        assert "stricter" in result.reason and "minimum" in result.reason


def test_the_word_lower_in_lower_deck_is_not_a_reduction():
    quote = "For double deck trains it is permitted to use 270 mm for the lower deck"
    result = extract_height({"comparator": "<=", "value": 270, "relaxes": True,
                             "conditions": [DOUBLE]}, quote=quote)  # fmt: skip
    assert result.status == "found", result.reason


def test_an_increase_may_relax_a_maximum_but_not_a_minimum():
    quote = "For double deck trains the height of each step may be increased to a maximum of 230 mm"
    ok = extract_height({"relaxes": True, "conditions": [DOUBLE]}, quote=quote)
    assert ok.status == "found", ok.reason
    bad = extract_height({"comparator": ">=", "relaxes": True, "conditions": [DOUBLE]}, quote=quote)
    assert bad.status == "unverified" and "stricter" in bad.reason


def test_the_prompt_separates_a_relaxation_from_a_demonstration_and_asks_for_the_case_condition():
    from rail_compliance.tools.extract import SYSTEM

    flat = " ".join(SYSTEM.split())
    assert "not a relaxation" in flat and "`contingency`" in flat
    assert "holds for every spec" in flat  # a rule with no condition is a rule for every spec
