import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from rail_compliance.spec import TrainSpec, load_spec, schema_json

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
