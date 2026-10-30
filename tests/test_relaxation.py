"""A relaxation: a rule that permits a lower standard where its conditions hold ("for double deck
trains it is permitted to reduce this value to 270 mm"). Where it applies and the value meets it, a
failed general rule is excused; where it is unknown whether it applies, a person decides."""

import pytest
from pydantic import ValidationError

from rail_compliance.agent import Scratch, _settle
from rail_compliance.models import Condition, RequirementCore
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
