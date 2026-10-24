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
from typing import Annotated

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

    wheelchair_spaces: Count | None = Field(
        default=None, description="Accessible wheelchair spaces in the unit."
    )
    exterior_doors: ExteriorDoors | None = None
    steps: Steps | None = None
    toilets: Toilets | None = None


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
