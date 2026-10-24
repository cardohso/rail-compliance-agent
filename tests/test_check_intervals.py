"""Inputs known only to lie in an interval (a length that includes a power head is <= the stated
value), a contingent rule, and the three-valued conditions both need."""

import pytest

from rail_compliance.models import Band, Condition
from rail_compliance.tools.check import check
from tests.factories import limit, table5

SPACES_LENGTH = {"unit_length_m": 210.0}
UP_TO_210 = {"unit_length_m": (0.0, 210.0)}


def spaces(value, length=210.0, intervals=UP_TO_210):
    return check(value, table5(), context={"unit_length_m": length}, intervals=intervals)


def test_a_value_that_meets_every_possible_requirement_passes():
    result = spaces(3)  # 0-210 m needs 1, 2 or 3 spaces
    assert result.verdict == "pass"
    assert result.required_value == 3  # the strictest requirement it had to meet


def test_a_value_that_meets_none_of_them_fails():
    result = spaces(0)
    assert result.verdict == "fail"
    assert result.required_value == 1  # even the most lenient one


@pytest.mark.parametrize("value", [1, 2])
def test_a_value_that_meets_some_requirements_but_not_others_is_needs_human(value):
    result = spaces(value)
    assert result.verdict == "needs_human"
    assert "unit_length_m" in result.reason and "0" in result.reason and "210" in result.reason


def test_a_narrow_interval_that_touches_one_row_decides_like_an_exact_value():
    assert spaces(1, length=29.0, intervals={"unit_length_m": (0.0, 29.0)}).verdict == "pass"


def test_an_interval_ending_exactly_on_a_row_boundary_follows_the_inclusive_bounds():
    # [0, 205] reaches the "30 to 205" row (2 spaces) but not "more than 205" (3 spaces)
    assert spaces(2, length=205.0, intervals={"unit_length_m": (0.0, 205.0)}).verdict == "pass"
    assert spaces(2, length=205.1, intervals={"unit_length_m": (0.0, 205.1)}).verdict == (
        "needs_human"
    )


def test_without_an_interval_the_stated_value_is_used_as_before():
    assert check(2, table5(), context=SPACES_LENGTH).verdict == "fail"  # 210 m needs 3


def test_band_intersects_a_closed_interval():
    below_30 = Band(upper=30, upper_inclusive=False, value=1)
    from_30 = Band(lower=30, upper=205, value=2)
    above_205 = Band(lower=205, lower_inclusive=False, upper=300, value=3)
    assert below_30.intersects(0, 30) and not below_30.intersects(30, 40)
    assert from_30.intersects(0, 30) and not from_30.intersects(0, 29.99)
    assert not above_205.intersects(0, 205) and above_205.intersects(0, 205.01)
    assert Band(lower=300, lower_inclusive=False, value=4).intersects(299, 300.5)
    assert not Band(lower=300, lower_inclusive=False, value=4).intersects(0, 300)


@pytest.mark.parametrize(
    ("op", "threshold", "expected"),
    [
        (">", 250, "not_applicable"),  # false for every length in [0, 210]
        ("<", 300, "applies"),  # true for every length in [0, 210]
        (">", 100, "needs_human"),  # true for some, false for others
        ("==", 500, "not_applicable"),  # 500 is outside the interval
        ("==", 100, "needs_human"),  # 100 is inside it
    ],
)
def test_conditions_on_an_interval_variable_are_three_valued(op, threshold, expected):
    rule = limit(
        "p", ">=", 5, conditions=[Condition(variable="unit_length_m", op=op, value=threshold)]
    )
    result = check(9, rule, context=SPACES_LENGTH, intervals=UP_TO_210)
    assert result.verdict == ("pass" if expected == "applies" else expected)


def test_a_degenerate_interval_behaves_like_an_exact_value():
    rule = limit("p", ">=", 5, conditions=[Condition(variable="unit_length_m", op="==", value=100)])
    assert (
        check(9, rule, context=SPACES_LENGTH, intervals={"unit_length_m": (100.0, 100.0)}).verdict
        == "pass"
    )


# --- contingent rules -------------------------------------------------------------------------


def test_a_contingent_rule_keeps_its_numeric_verdict_and_carries_the_contingency():
    rule = limit("p", "<=", 230, "mm", contingency="a demonstrated reduction in the step count")
    ok, bad = check(215, rule), check(231, rule)
    assert (ok.verdict, bad.verdict) == ("pass", "fail")
    assert ok.contingency == bad.contingency == "a demonstrated reduction in the step count"


def test_an_ordinary_rule_has_no_contingency():
    assert check(215, limit("p", "<=", 230, "mm")).contingency is None
