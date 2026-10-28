"""Two rule shapes beyond a single limit and a table: a range ("30 mm to 40 mm") and a condition
on a category ("on double-deck units")."""

import pytest
from pydantic import ValidationError

from rail_compliance.models import Condition, RequirementCore, RequirementDraft
from rail_compliance.parameters import SUBJECT_OF
from rail_compliance.report import describe_rule
from rail_compliance.tools.check import check
from rail_compliance.tools.extract import _category_stated, _check_variables, extract_requirement
from tests.factories import CITATION, passage
from tests.test_extract import FakeLLM

DOOR = "exterior_doors.clear_width_mm"


def ranged(lo=30.0, hi=40.0, unit="mm", conditions=()):
    from rail_compliance.models import Requirement

    return Requirement(parameter=DOOR, subject="s", comparator="between", value=lo, value_max=hi,
                       unit=unit, conditions=list(conditions), citation=CITATION)  # fmt: skip


# --- the range shape -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "verdict"),
    [(29.9, "fail"), (30, "pass"), (35, "pass"), (40, "pass"), (40.1, "fail"), (55, "fail")],
)
def test_a_range_includes_both_ends(value, verdict):
    assert check(value, ranged()).verdict == verdict


def test_a_range_result_names_both_bounds_and_the_margin_to_the_nearer_one():
    r = check(38, ranged())
    assert "30" in r.reason and "40" in r.reason
    assert (r.required_value, r.required_max) == (30, 40)
    assert r.margin == 2  # 2 mm inside the upper bound
    assert check(42, ranged()).margin == -2


def test_a_range_converts_units_like_a_limit():
    assert check(0.035, ranged(), spec_unit="m").verdict == "pass"


def test_a_range_is_described_with_both_bounds():
    assert describe_rule("between", 430, "mm", upper=500) == "430–500 mm"


@pytest.mark.parametrize(
    "fields",
    [
        {"comparator": "between", "value": 30},  # no upper bound
        {"comparator": "between", "value": 40, "value_max": 30},  # reversed
        {"comparator": ">=", "value": 30, "value_max": 40},  # upper bound on a plain limit
    ],
)
def test_a_malformed_range_is_rejected(fields):
    with pytest.raises(ValidationError):
        RequirementCore(parameter=DOOR, subject="s", **fields)


HANDRAIL = passage(
    "(1) Handrails shall be of a circular cross section with an outside diameter of 30 mm to "
    "40 mm.",
    id_="tsi-prm:Annex §4.2.2.9#1",
)


def range_draft(**rule_over):
    rule = RequirementCore(parameter=DOOR, subject=SUBJECT_OF[DOOR], comparator="between",
                           value=30, value_max=40, unit="mm")  # fmt: skip
    rule = rule.model_copy(update=rule_over)
    quote = "with an outside diameter of 30 mm to 40 mm"
    return RequirementDraft(found=True, passage_id=HANDRAIL.id, quote=quote, rule=rule)


def test_a_range_is_verified_against_both_bounds():
    result = extract_requirement([HANDRAIL], DOOR, FakeLLM(range_draft()))
    assert result.status == "found"
    assert result.requirement.value_max == 40


def test_a_range_with_an_invented_upper_bound_is_unverified():
    result = extract_requirement([HANDRAIL], DOOR, FakeLLM(range_draft(value_max=45)))
    assert result.status == "unverified" and "45" in result.reason


# --- conditions on a category --------------------------------------------------------------


def double_deck_rule():
    from tests.factories import limit

    return limit("steps.internal_step_height_mm", ">=", 270, "mm",
                 conditions=[Condition(variable="deck", op="==", value="double_deck")])  # fmt: skip


@pytest.mark.parametrize(
    ("deck", "verdict"), [("double_deck", "pass"), ("single_deck", "not_applicable")]
)
def test_a_category_condition_selects_the_rule(deck, verdict):
    assert check(280, double_deck_rule(), context={"deck": deck}).verdict == verdict


def test_an_unknown_category_is_judged_as_if_the_rule_applied():
    assert check(280, double_deck_rule(), context={}).verdict == "pass"
    assert check(260, double_deck_rule(), context={}).verdict == "needs_human"


def test_a_category_condition_is_shown_readably():
    r = check(280, double_deck_rule(), context={"deck": "single_deck"})
    assert "deck == double_deck" in r.reason


def test_a_category_condition_must_use_equality():
    with pytest.raises(ValidationError):
        Condition(variable="deck", op=">=", value="double_deck")


KINDS = {
    "deck": "category",
    "design_speed_kmh": "number",
    "steps.internal_step_height_mm": "number",
}
CHOICES = {"deck": ("single_deck", "double_deck")}


def rule_with(cond):
    return RequirementCore(parameter="steps.internal_step_height_mm", subject="s",
                           comparator=">=", value=270, conditions=[cond])  # fmt: skip


def test_a_category_condition_must_name_one_of_the_choices():
    bad = rule_with(Condition(variable="deck", op="==", value="triple_deck"))
    assert "single_deck, double_deck" in _check_variables(bad, KINDS, CHOICES)
    good = rule_with(Condition(variable="deck", op="==", value="double_deck"))
    assert _check_variables(good, KINDS, CHOICES) is None


def test_a_number_cannot_test_a_category_and_a_word_cannot_test_a_number():
    assert "category" in _check_variables(rule_with(Condition(variable="deck", op="==", value=2)),
                                          KINDS, CHOICES)  # fmt: skip
    word = rule_with(Condition(variable="design_speed_kmh", op="==", value="fast"))
    assert "number" in _check_variables(word, KINDS, CHOICES)


@pytest.mark.parametrize(
    ("value", "quote", "stated"),
    [
        ("double_deck", "On double-deck units the minimum depth shall be 270 mm.", True),
        ("double_deck", "For double deck rolling stock ...", True),
        ("renewed", "When a unit is renewed or upgraded ...", True),
        ("double_deck", "On single-deck units the depth shall be 280 mm.", False),
    ],
)
def test_a_category_value_must_be_stated_in_the_quote(value, quote, stated):
    assert _category_stated(value, quote) is stated


def test_the_prompt_teaches_both_shapes():
    from rail_compliance.tools.extract import SYSTEM

    assert '"between"' in SYSTEM and "value_max" in SYSTEM
    assert 'tested by name with\n  "=="' in SYSTEM


def test_a_category_field_is_listed_with_its_choices(monkeypatch):
    from rail_compliance.tools import extract

    monkeypatch.setattr(extract, "parameter_kinds", lambda: {**KINDS, DOOR: "number"})
    monkeypatch.setattr(extract, "parameter_choices", lambda: CHOICES)
    monkeypatch.setattr(extract, "parameter_info",
                        lambda: {DOOR: ("mm", "door"), "deck": (None, "deck layout")})  # fmt: skip
    monkeypatch.setattr(extract, "condition_variables", lambda: ["deck"])
    prompt = extract._prompt(DOOR, [HANDRAIL], None)
    assert "- deck (category, one of single_deck / double_deck)" in prompt


def test_choices_are_read_from_literal_fields():
    from typing import Literal

    from rail_compliance.spec import _choices

    assert _choices(Literal["new", "renewed"] | None) == ("new", "renewed")
    assert _choices(float | None) == ()


STAIRS = passage(
    "(1) On double-deck units the minimum step depth shall be 270 mm.",
    id_="tsi-prm:Annex §4.2.2.8#1",
)
STEP = "steps.internal_step_height_mm"


def category_draft(deck, quote="On double-deck units the minimum step depth shall be 270 mm."):
    deck_is = Condition(variable="deck", op="==", value=deck)
    rule = RequirementCore(parameter=STEP, subject=SUBJECT_OF[STEP], comparator=">=", value=270,
                           unit="mm", conditions=[deck_is])  # fmt: skip
    return RequirementDraft(found=True, passage_id=STAIRS.id, quote=quote, rule=rule)


@pytest.fixture
def deck_field(monkeypatch):
    from rail_compliance.tools import extract

    real = extract.parameter_kinds()
    monkeypatch.setattr(extract, "parameter_kinds", lambda: {**real, **KINDS})
    monkeypatch.setattr(extract, "parameter_choices", lambda: CHOICES)


@pytest.mark.parametrize(
    ("deck", "status"), [("double_deck", "found"), ("single_deck", "unverified")]
)
def test_extraction_verifies_the_category_against_the_quote(deck_field, deck, status):
    result = extract_requirement([STAIRS], STEP, FakeLLM(category_draft(deck)))
    assert result.status == status, result.reason
