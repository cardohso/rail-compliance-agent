import pytest

from rail_compliance.tools.check import check
from tests.factories import limit, table5, wheelchair_door_rule

DOOR_MIN = limit("exterior_doors.clear_width_mm", ">=", 800, "mm")
STEP_MAX = limit("steps.external_step_height_mm", "<=", 230, "mm")


@pytest.mark.parametrize(
    ("value", "verdict"),
    [(850, "pass"), (800, "pass"), (799.9, "fail"), (0.0001, "fail")],
)
def test_minimum_including_exactly_at_the_limit(value, verdict):
    assert check(value, DOOR_MIN).verdict == verdict


@pytest.mark.parametrize(
    ("value", "verdict"), [(200, "pass"), (230, "pass"), (230.1, "fail"), (250, "fail")]
)
def test_maximum_including_exactly_at_the_limit(value, verdict):
    assert check(value, STEP_MAX).verdict == verdict


def test_strict_comparators_exclude_the_limit():
    assert check(800, limit("p", ">", 800)).verdict == "fail"
    assert check(800.5, limit("p", ">", 800)).verdict == "pass"
    assert check(800, limit("p", "<", 800)).verdict == "fail"
    assert check(799, limit("p", "<", 800)).verdict == "pass"
    assert check(800, limit("p", "==", 800)).verdict == "pass"
    assert check(801, limit("p", "==", 800)).verdict == "fail"


def test_result_carries_margin_and_a_readable_reason():
    result = check(780, DOOR_MIN)
    assert result.verdict == "fail"
    assert result.margin == -20
    assert result.required_value == 800
    assert result.unit == "mm"
    assert "780" in result.reason
    assert "800" in result.reason


def test_missing_spec_value_is_needs_human_not_fail():
    result = check(None, DOOR_MIN)
    assert result.verdict == "needs_human"
    assert "does not supply" in result.reason


def test_metres_are_converted_to_millimetres_exactly():
    assert check(0.8, DOOR_MIN, spec_unit="m").verdict == "pass"  # 0.8 m is exactly 800 mm
    assert check(0.799, DOOR_MIN, spec_unit="m").verdict == "fail"


def test_unconvertible_units_are_needs_human():
    result = check(800, DOOR_MIN, spec_unit="kg")
    assert result.verdict == "needs_human"
    assert "unit" in result.reason


def test_same_unit_needs_no_conversion():
    assert check(800, DOOR_MIN, spec_unit="mm").verdict == "pass"


@pytest.mark.parametrize(
    ("length", "required"),
    [
        (29.9, 1),
        (30, 2),  # "30 to 205 metres": 30 is in the 2-space band
        (105, 2),
        (205, 2),  # 205 is still in the 2-space band
        (205.1, 3),
        (300, 3),  # 300 is still in the 3-space band
        (300.1, 4),
        (450, 4),
    ],
)
def test_table_bands_at_every_boundary(length, required):
    at_requirement = check(required, table5(), context={"unit_length_m": length})
    assert at_requirement.verdict == "pass"
    assert at_requirement.required_value == required
    below = check(required - 1, table5(), context={"unit_length_m": length})
    assert below.verdict == "fail"


def test_more_spaces_than_required_passes():
    assert check(3, table5(), context={"unit_length_m": 120}).verdict == "pass"


def test_table_without_the_selecting_variable_is_needs_human():
    result = check(2, table5(), context={})
    assert result.verdict == "needs_human"
    assert "unit_length_m" in result.reason


def test_table_with_a_gap_is_needs_human():
    from rail_compliance.models import Band, Requirement
    from tests.factories import CITATION

    gappy = Requirement(
        parameter="p",
        subject="s",
        comparator=">=",
        bands=[Band(upper=10, value=1), Band(lower=20, value=2)],
        band_variable="x",
        citation=CITATION,
    )
    result = check(1, gappy, context={"x": 15})
    assert result.verdict == "needs_human"
    assert "no band" in result.reason


def test_table_with_overlapping_bands_is_needs_human():
    from rail_compliance.models import Band, Requirement
    from tests.factories import CITATION

    overlap = Requirement(
        parameter="p",
        subject="s",
        comparator=">=",
        bands=[Band(upper=20, value=1), Band(lower=10, value=2)],
        band_variable="x",
        citation=CITATION,
    )
    assert check(1, overlap, context={"x": 15}).verdict == "needs_human"


def test_condition_met_applies_the_rule():
    ctx = {"design_speed_kmh": 160, "exterior_doors.wheelchair_door_level_access": 1}
    assert check(900, wheelchair_door_rule(), context=ctx).verdict == "fail"
    assert check(1000, wheelchair_door_rule(), context=ctx).verdict == "pass"


def test_condition_not_met_is_not_applicable():
    ctx = {"design_speed_kmh": 300, "exterior_doors.wheelchair_door_level_access": 1}
    result = check(900, wheelchair_door_rule(), context=ctx)
    assert result.verdict == "not_applicable"
    assert "design_speed_kmh" in result.reason


def test_condition_exactly_at_its_boundary_follows_the_literal_text():
    # "lower than 250 km/h": a train designed for exactly 250 km/h is not covered by the rule
    ctx = {"design_speed_kmh": 250, "exterior_doors.wheelchair_door_level_access": 1}
    assert check(900, wheelchair_door_rule(), context=ctx).verdict == "not_applicable"


def test_missing_condition_data_is_needs_human():
    ctx = {"exterior_doors.wheelchair_door_level_access": 1}
    result = check(900, wheelchair_door_rule(), context=ctx)
    assert result.verdict == "needs_human"
    assert "design_speed_kmh" in result.reason


def test_a_false_condition_beats_an_unknown_one():
    ctx = {"exterior_doors.wheelchair_door_level_access": 0}  # speed unknown, level access false
    assert check(900, wheelchair_door_rule(), context=ctx).verdict == "not_applicable"
