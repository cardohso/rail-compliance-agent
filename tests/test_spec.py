import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from rail_compliance.spec import (
    TrainSpec,
    load_spec,
    parameter_info,
    schema_json,
    spec_values,
    unit_of,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = sorted((ROOT / "examples").glob("*.json"))
MINIMAL = {"name": "minimal", "unit_length_m": 100.0}


def test_minimal_spec_leaves_everything_else_unset():
    spec = TrainSpec.model_validate(MINIMAL)
    assert spec.wheelchair_spaces is None
    assert spec.exterior_doors is None
    assert spec.steps is None
    assert spec.toilets is None


def test_unknown_field_is_rejected_so_a_typo_cannot_hide_a_parameter():
    with pytest.raises(ValidationError, match="wheelchair_space"):
        TrainSpec.model_validate({**MINIMAL, "wheelchair_space": 2})


@pytest.mark.parametrize(
    "patch",
    [
        {"unit_length_m": 0},
        {"unit_length_m": -5},
        {"unit_length_m": 900},
        {"design_speed_kmh": 0},
        {"wheelchair_spaces": -1},
        {"wheelchair_spaces": 1.5},
        {"exterior_doors": {"clear_width_mm": 0}},
        {"steps": {"external_step_height_mm": -230}},
    ],
)
def test_out_of_range_values_are_rejected(patch):
    with pytest.raises(ValidationError):
        TrainSpec.model_validate({**MINIMAL, **patch})


def test_more_universal_toilets_than_toilets_is_rejected():
    toilets = {"fitted": 1, "universal": 2}
    with pytest.raises(ValidationError, match="universal"):
        TrainSpec.model_validate({**MINIMAL, "toilets": toilets})


def test_toilets_object_may_be_partial():
    spec = TrainSpec.model_validate({**MINIMAL, "toilets": {"fitted": 2}})
    assert spec.toilets.universal is None


def test_load_spec_reports_the_file_name_on_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="bad.json"):
        load_spec(bad)


def test_load_spec_reports_the_file_name_on_schema_violation(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"name": "x"}), encoding="utf-8")
    with pytest.raises(ValueError, match="bad.json"):
        load_spec(bad)


def test_there_are_three_examples():
    assert len(EXAMPLES) == 3


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_example_specs_are_valid(path):
    spec = load_spec(path)
    assert spec.name
    assert spec.description


def test_committed_json_schema_matches_the_model():
    committed = json.loads((ROOT / "schema" / "train-spec.schema.json").read_text("utf-8"))
    assert committed == json.loads(schema_json()), (
        "schema/train-spec.schema.json is stale: run `uv run python -m rail_compliance.spec schema`"
    )


def test_spec_values_flattens_nested_parameters_and_drops_missing_ones():
    spec = load_spec(ROOT / "examples" / "03_incomplete_highspeed.json")
    values = spec_values(spec)
    assert values["unit_length_m"] == 210.0
    assert values["exterior_doors.wheelchair_door_clear_width_mm"] == 900.0
    assert values["steps.external_step_height_mm"] == 220.0
    assert "design_speed_kmh" not in values  # the spec leaves it out
    assert "toilets.fitted" not in values


def test_spec_values_turns_booleans_into_numbers():
    spec = load_spec(ROOT / "examples" / "03_incomplete_highspeed.json")
    values = spec_values(spec)
    assert values["length_includes_power_head"] == 1.0
    assert values["exterior_doors.wheelchair_door_level_access"] == 1.0


def test_false_is_a_value_not_a_missing_parameter():
    spec = load_spec(ROOT / "examples" / "01_compliant_emu.json")
    assert spec_values(spec)["length_includes_power_head"] == 0.0


@pytest.mark.parametrize(
    ("parameter", "unit"),
    [
        ("unit_length_m", "m"),
        ("design_speed_kmh", "km/h"),
        ("exterior_doors.clear_width_mm", "mm"),
        ("wheelchair_spaces", None),
        ("toilets.fitted", None),
    ],
)
def test_unit_of(parameter, unit):
    assert unit_of(parameter) == unit


def test_parameter_info_lists_every_checkable_path_with_unit_and_description():
    info = parameter_info()
    assert info["unit_length_m"][0] == "m"
    assert info["exterior_doors.clear_width_mm"][0] == "mm"
    assert info["toilets.fitted"][0] is None
    assert "level access" in info["exterior_doors.wheelchair_door_level_access"][1]
    assert "name" not in info
    assert all(description for _, description in info.values())


def test_every_spec_value_path_is_in_parameter_info():
    spec = load_spec(ROOT / "examples" / "01_compliant_emu.json")
    assert set(spec_values(spec)) <= set(parameter_info())


def test_parameter_kinds_distinguish_flags_counts_and_numbers():
    from rail_compliance.spec import parameter_kinds

    kinds = parameter_kinds()
    assert kinds["exterior_doors.wheelchair_door_level_access"] == "bool"
    assert kinds["length_includes_power_head"] == "bool"
    assert kinds["toilets.fitted"] == "count"
    assert kinds["wheelchair_spaces"] == "count"
    assert kinds["design_speed_kmh"] == "number"
    assert kinds["exterior_doors.clear_width_mm"] == "number"
    assert set(kinds) == set(parameter_info())
