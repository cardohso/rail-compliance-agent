"""The train design spec: what a user submits, validated before the agent sees it.

Scope is the PRM TSI rolling-stock requirements (Regulation (EU) No 1300/2014, point 4.2.2).
Only `name` and `unit_length_m` are required. Every other parameter is optional: a parameter the
user did not supply is not a failure, it is data the agent cannot check, and it ends as
`needs_human`. Unknown fields are errors, so a typo cannot silently drop a parameter.

    uv run python -m rail_compliance.spec validate examples/*.json
    uv run python -m rail_compliance.spec schema        # rewrite schema/train-spec.schema.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Annotated, Literal, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "train-spec.schema.json"

Mm = Annotated[float, Field(gt=0, le=5000)]
Count = Annotated[int, Field(ge=0, le=50)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExteriorDoors(_Strict):
    clear_width_mm: Mm | None = Field(
        default=None,
        description="Minimum clear useable width, when open, of the narrowest exterior "
        "passenger doorway.",
    )
    wheelchair_door_clear_width_mm: Mm | None = Field(
        default=None,
        description="Minimum clear useable width, when open, of the doorways designated "
        "for wheelchair access.",
    )
    wheelchair_door_level_access: bool | None = Field(
        default=None,
        description="Whether the wheelchair access doorways give level access as the TSI "
        "defines it (gap to the platform at most 75 mm horizontal and 50 mm vertical, "
        "no internal step between sill and vestibule).",
    )


class Steps(_Strict):
    external_step_height_mm: Mm | None = Field(
        default=None, description="Height of the highest external access step, fixed or moveable."
    )
    internal_step_height_mm: Mm | None = Field(
        default=None, description="Height of the highest internal step used for external access."
    )


class Toilets(_Strict):
    fitted: Count | None = Field(default=None, description="Toilets fitted in the unit.")
    universal: Count | None = Field(
        default=None, description="Of those, toilets designed as universal toilets."
    )
    universal_door_clear_width_mm: Mm | None = Field(
        default=None, description="Clear useable width of the universal toilet access door."
    )

    @model_validator(mode="after")
    def _universal_is_a_subset(self) -> Toilets:
        if self.fitted is not None and self.universal is not None and self.universal > self.fitted:
            raise ValueError(
                f"universal ({self.universal}) cannot exceed fitted toilets ({self.fitted})"
            )
        return self


class WheelchairSpaceLayout(_Strict):
    width_mm: Mm | None = Field(
        default=None,
        description="Width of the wheelchair space over its full length, from floor level to "
        "1 450 mm, not counting any hand clearance.",
    )
    sides_next_to_obstacle: Annotated[int, Field(ge=0, le=2)] | None = Field(
        default=None,
        description="Sides of the wheelchair space (0, 1 or 2) next to a wall or structure that "
        "would inhibit the user's hands; a side open to the aisle does not count.",
    )
    hand_clearance_mm: Mm | None = Field(
        default=None,
        description="Smallest additional width for the user's hands, 400 to 800 mm above floor "
        "level, on a side next to an obstacle.",
    )
    turning_space_diameter_mm: Mm | None = Field(
        default=None,
        description="Diameter of the wheelchair turning space next to the wheelchair space.",
    )


class Stairs(_Strict):
    step_height_mm: Mm | None = Field(
        default=None,
        description="Height of the highest internal step, other than steps for external access.",
    )
    step_depth_mm: Mm | None = Field(
        default=None,
        description="Smallest depth of an internal step, other than steps for external access, at "
        "the central axis of the stairs.",
    )


class Handrails(_Strict):
    outside_diameter_mm: Mm | None = Field(
        default=None,
        description="Outside diameter of the handrails, if all are the same (else the one "
        "furthest from 30-40 mm).",
    )


class PrioritySeats(_Strict):
    cushion_height_mm: Mm | None = Field(
        default=None,
        description="Height of the top of the priority seat cushion above floor level at its "
        "front edge (the one furthest from 430-500 mm, if they differ).",
    )


class TrainSpec(_Strict):
    spec_version: str = Field(default="1", description="Version of this spec format.")
    name: str = Field(min_length=1, max_length=120, description="Label for reports.")
    description: str | None = Field(default=None, max_length=500)

    unit_length_m: Annotated[float, Field(gt=0, le=500)] = Field(
        description="Length of the unit in metres, excluding any locomotive or power head "
        "(the basis the TSI uses for the wheelchair-space table)."
    )
    length_includes_power_head: bool | None = Field(
        default=None,
        description="Set true if unit_length_m includes a locomotive or power head: the length "
        "is then not on the TSI's basis.",
    )
    design_speed_kmh: Annotated[float, Field(gt=0, le=500)] | None = Field(
        default=None, description="Design speed of the train in km/h."
    )
    deck_layout: Literal["single_deck", "double_deck"] | None = Field(
        default=None, description="Whether the unit has one passenger deck or two."
    )

    wheelchair_spaces: Count | None = Field(
        default=None, description="Accessible wheelchair spaces in the unit."
    )
    exterior_doors: ExteriorDoors | None = None
    steps: Steps | None = None
    toilets: Toilets | None = None
    wheelchair_space_layout: WheelchairSpaceLayout | None = None
    stairs: Stairs | None = None
    handrails: Handrails | None = None
    priority_seats: PrioritySeats | None = None


def spec_values(spec: TrainSpec) -> dict[str, float]:
    """Every parameter the spec supplies, keyed by dotted path ("steps.external_step_height_mm").

    Booleans become 1.0 / 0.0 so a condition such as "level access" is a plain number test.
    Parameters the spec leaves out are absent, which is how `check` knows data is missing.
    """
    out: dict[str, float] = {}

    def walk(model: BaseModel, prefix: str) -> None:
        for name in type(model).model_fields:
            value = getattr(model, name)
            if isinstance(value, BaseModel):
                walk(value, f"{prefix}{name}.")
            elif isinstance(value, bool):
                out[f"{prefix}{name}"] = 1.0 if value else 0.0
            elif isinstance(value, int | float):
                out[f"{prefix}{name}"] = float(value)

    walk(spec, "")
    return out


def spec_categories(spec: TrainSpec) -> dict[str, str]:
    """Every category parameter the spec supplies, by name ("deck_layout" -> "double_deck")."""
    out: dict[str, str] = {}

    def walk(model: BaseModel, prefix: str) -> None:
        for name in type(model).model_fields:
            value = getattr(model, name)
            if isinstance(value, BaseModel):
                walk(value, f"{prefix}{name}.")
            elif isinstance(value, str) and f"{prefix}{name}" in parameter_choices():
                out[f"{prefix}{name}"] = value

    walk(spec, "")
    return out


def _walk_parameters():
    """Every checkable parameter: (dotted path, field name, field info)."""

    def walk(model: type[BaseModel], prefix: str):
        for name, field in model.model_fields.items():
            nested = [
                t
                for t in (field.annotation, *get_args(field.annotation))
                if isinstance(t, type) and issubclass(t, BaseModel)
            ]
            if nested:
                yield from walk(nested[0], f"{prefix}{name}.")
            elif name not in {"spec_version", "name", "description"}:
                yield f"{prefix}{name}", name, field

    yield from walk(TrainSpec, "")


def parameter_info() -> dict[str, tuple[str | None, str]]:
    """Every checkable parameter path -> (unit, description), for prompts and tool descriptions."""
    return {
        path: (unit_of(name), field.description or "") for path, name, field in _walk_parameters()
    }


def parameter_kinds() -> dict[str, str]:
    """Every parameter path -> "bool" (true/false), "count" (whole number) or "number"."""

    def leaves(annotation):
        """The plain types inside Annotated[...] and unions such as `int | None`."""
        if get_origin(annotation) is Annotated:
            yield from leaves(get_args(annotation)[0])
        elif get_args(annotation):
            for arg in get_args(annotation):
                yield from leaves(arg)
        else:
            yield annotation

    def kind(annotation) -> str:
        if _choices(annotation):
            return "category"
        types = set(leaves(annotation))
        if bool in types:
            return "bool"
        return "count" if int in types else "number"

    return {path: kind(field.annotation) for path, _, field in _walk_parameters()}


def _choices(annotation) -> tuple[str, ...]:
    """The names a Literal["a", "b"] field (optionally `| None`) allows; empty for other types."""
    if get_origin(annotation) is Literal:
        return tuple(a for a in get_args(annotation) if isinstance(a, str))
    return next((c for a in get_args(annotation) if (c := _choices(a))), ())


def parameter_choices() -> dict[str, tuple[str, ...]]:
    """Every category parameter path -> the names it allows."""
    return {path: c for path, _, field in _walk_parameters() if (c := _choices(field.annotation))}


# A qualifier says how another parameter's value was measured; it is not a circumstance that
# selects a rule. The flag below says the stated length includes a power head, which the TSI's
# table excludes: the length it counts is then at most the stated one. Rules may not be
# conditioned on a qualifier; the evaluation of `check` handles it as an interval instead.
QUALIFIERS: dict[str, str] = {"length_includes_power_head": "unit_length_m"}


def condition_variables() -> list[str]:
    """Spec parameters a rule's condition or table may refer to (qualifiers excluded)."""
    return [path for path in parameter_info() if path not in QUALIFIERS]


def spec_intervals(spec: TrainSpec) -> dict[str, tuple[float, float]]:
    """Parameters whose true value is only known to lie in [low, high], from the qualifiers."""
    values = spec_values(spec)
    return {
        target: (0.0, values[target])
        for flag, target in QUALIFIERS.items()
        if values.get(flag) == 1.0 and target in values
    }


UNIT_SUFFIXES = {"_mm": "mm", "_m": "m", "_kmh": "km/h"}


def unit_of(parameter: str) -> str | None:
    """The unit a spec parameter is expressed in, from its name suffix (None for counts/flags)."""
    return next((u for suffix, u in UNIT_SUFFIXES.items() if parameter.endswith(suffix)), None)


def load_spec(path: Path | str) -> TrainSpec:
    """Read and validate a spec file. Errors name the file, so batch runs say which one failed."""
    path = Path(path)
    try:
        return TrainSpec.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as exc:
        raise ValueError(f"{path.name}: invalid spec\n{exc}") from exc


def schema_json() -> str:
    return json.dumps(TrainSpec.model_json_schema(), indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    check = sub.add_parser("validate", help="validate spec files")
    check.add_argument("files", nargs="+", type=Path)
    sub.add_parser("schema", help="write the JSON Schema to schema/train-spec.schema.json")
    args = ap.parse_args(argv)

    if args.cmd == "schema":
        SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
        SCHEMA_PATH.write_text(schema_json(), encoding="utf-8")
        print(f"wrote {SCHEMA_PATH}")
        return 0

    failed = 0
    for path in args.files:
        try:
            load_spec(path)
            print(f"ok      {path}")
        except ValueError as exc:
            failed += 1
            print(f"INVALID {exc}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
