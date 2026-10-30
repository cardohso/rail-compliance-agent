"""The golden set: specs with the verdicts a careful reader of the PRM TSI expects.

Each case lists expected verdicts only for the parameters it is about; other parameters in the
report are not scored. `GOLD_RULES` encodes the rules as typed requirements with verbatim quotes
from the regulation, and `oracle` applies them with the deterministic `check` tool: a test uses
it to confirm that the verdicts typed into the cases are consistent with the arithmetic, and that
the quotes exist in the corpus. The oracle is not the system under test: it is given the right
rules, so it measures nothing about the agent.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from rail_compliance.models import Band, Citation, Condition, Requirement
from rail_compliance.parameters import SUBJECT_OF
from rail_compliance.report import FinalVerdict
from rail_compliance.spec import TrainSpec, spec_categories, spec_values
from rail_compliance.tools.check import check

GOLDEN_DIR = Path(__file__).resolve().parents[2] / "eval" / "specs"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Expected(_Strict):
    verdict: FinalVerdict
    required: str | None = None  # the rule that decides it, in words
    gold_passages: list[str] = Field(default_factory=list)  # passages that contain that rule
    expected_tools: list[str]  # tools that must be called, in this order (others may be between)
    alt_tools: list[list[str]] = Field(default_factory=list)  # other acceptable sequences
    rationale: str


class GoldenCase(_Strict):
    id: str
    title: str
    tags: list[str]
    why: str
    spec: TrainSpec
    expected: dict[str, Expected]


# Suites of the development set, by file prefix: the original twenty (core) and the cases for the
# parameters added later (prm-extended). Each runs and is gated on its own, so a free-tier day
# can hold one fresh run of either.
SUITES: dict[str, str] = {"core": "g*.json", "prm-extended": "p*.json"}


def load_suite(name: str) -> list[GoldenCase]:
    if name not in SUITES:
        raise ValueError(f"unknown suite {name!r}; known: {', '.join(SUITES)}")
    return load_golden(GOLDEN_DIR, SUITES[name])


def load_golden(directory: Path = GOLDEN_DIR, pattern: str = "g*.json") -> list[GoldenCase]:
    return [
        GoldenCase.model_validate_json(p.read_text(encoding="utf-8"))
        for p in sorted(Path(directory).glob(pattern))
    ]


# --- the rules, as they stand in the regulation -----------------------------------------------

PRM = {"doc_id": "tsi-prm", "document": "PRM TSI"}
URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02014R1300-20230928"


def _rule(
    parameter, comparator, value, unit, passage, section, quote, conditions=(), bands=(),
    subject=None, value_max=None, relaxes=False,
):  # fmt: skip
    return Requirement(
        value_max=value_max,
        relaxes=relaxes,
        parameter=parameter,
        subject=subject or SUBJECT_OF[parameter],
        comparator=comparator,
        value=value,
        unit=unit,
        bands=list(bands),
        band_variable="unit_length_m" if bands else None,
        conditions=list(conditions),
        citation=Citation(passage_id=passage, section=section, url=URL, quote=quote, **PRM),
    )


P_SPACES = "tsi-prm:Annex §4.2.2.2#1"
P_DOORS = "tsi-prm:Annex §4.2.2.3.2#1"
P_STEPS = "tsi-prm:Annex §4.2.2.11.2#1"
P_TOILET = "tsi-prm:Annex §4.2.2.5#1"
P_UNIVERSAL = "tsi-prm:Annex §5.3.2.4#1"

TABLE_5 = _rule(
    "wheelchair_spaces",
    ">=",
    None,
    None,
    P_SPACES,
    "Annex §4.2.2.2",
    "Less than 30 m | 1 wheelchair space 30 to 205 metres | 2 wheelchair spaces More than 205 "
    "to 300 metres | 3 wheelchair spaces More than 300 metres | 4 wheelchair spaces",
    bands=[
        Band(upper=30, upper_inclusive=False, value=1),
        Band(lower=30, upper=205, value=2),
        Band(lower=205, lower_inclusive=False, upper=300, value=3),
        Band(lower=300, lower_inclusive=False, value=4),
    ],
)
DOORS_ALL = _rule(
    "exterior_doors.clear_width_mm", ">=", 800, "mm", P_DOORS, "Annex §4.2.2.3.2",
    "All exterior passenger doorways shall have a minimum clear useable width of 800 mm when open.",
)  # fmt: skip
WHEELCHAIR_GENERAL = _rule(
    "exterior_doors.wheelchair_door_clear_width_mm", ">=", 800, "mm", P_DOORS, "Annex §4.2.2.3.2",
    "All exterior passenger doorways shall have a minimum clear useable width of 800 mm when open.",
    subject="exterior_doorway",
)  # fmt: skip
WHEELCHAIR_LEVEL = _rule(
    "exterior_doors.wheelchair_door_clear_width_mm", ">=", 1000, "mm", P_DOORS, "Annex §4.2.2.3.2",
    "On trains with a design speed lower than 250 km/h, wheelchair access doors offering a level "
    "access as defined in point 2.3 shall have a minimum clear useable width of 1 000 mm when "
    "open.",
    conditions=[
        Condition(variable="design_speed_kmh", op="<", value=250),
        Condition(variable="exterior_doors.wheelchair_door_level_access", op="==", value=1),
    ],
)  # fmt: skip
EXTERNAL_STEP = _rule(
    "steps.external_step_height_mm", "<=", 230, "mm", P_STEPS, "Annex §4.2.2.11.2",
    "An external access step, fixed or moveable, shall have a maximum height of 230 mm between "
    "steps and a minimum depth of 150 mm.",
)  # fmt: skip
INTERNAL_GENERAL = _rule(
    "steps.internal_step_height_mm", "<=", 200, "mm", P_STEPS, "Annex §4.2.2.11.2",
    "Internal steps for external access shall have a minimum depth of 240 mm between the vertical "
    "edges of the step and a maximum height of 200 mm.",
)  # fmt: skip
INTERNAL_EXCEPTION = _rule(
    "steps.internal_step_height_mm", "<=", 230, "mm", P_STEPS, "Annex §4.2.2.11.2",
    "The height of each step may be increased to a maximum of 230 mm if it can be demonstrated "
    "that this achieves a reduction of one in the total number of steps required.",
    subject="internal_step",
)  # fmt: skip
UNIVERSAL_TOILET = _rule(
    "toilets.universal", ">=", 1, None, P_TOILET, "Annex §4.2.2.5",
    "When toilets are fitted in a train, a universal toilet shall be provided",
    conditions=[Condition(variable="toilets.fitted", op=">", value=0)],
)  # fmt: skip
UNIVERSAL_DOOR = _rule(
    "toilets.universal_door_clear_width_mm", ">=", 800, "mm", P_UNIVERSAL, "Annex §5.3.2.4",
    "The toilet access door shall provide a minimum clear useable width of 800 mm.",
)  # fmt: skip

P_SPACE_DIMS = "tsi-prm:Annex §4.2.2.2#1"
P_TURNING = "tsi-prm:Annex §4.2.2.6#1"
P_STAIRS = "tsi-prm:Annex §4.2.2.8#1"
P_HANDRAILS = "tsi-prm:Annex §4.2.2.9#1"
P_PRIORITY = "tsi-prm:Annex §4.2.2.1.2.1#2"

SPACE_WIDTH = _rule(
    "wheelchair_space_layout.width_mm", ">=", 700, "mm", P_SPACE_DIMS, "Annex §4.2.2.2",
    "Over the full length of the wheelchair space the width shall be 700 mm from floor level to a "
    "minimum height of 1 450 mm",
)  # fmt: skip
HAND_CLEARANCE = _rule(
    "wheelchair_space_layout.hand_clearance_mm", ">=", 50, "mm", P_SPACE_DIMS, "Annex §4.2.2.2",
    "with an additional 50 mm width to give clearance for hands on each side that is adjacent to "
    "any obstacle",
    conditions=[Condition(variable="wheelchair_space_layout.sides_next_to_obstacle", op=">",
                          value=0)],
)  # fmt: skip
TURNING_SPACE = _rule(
    "wheelchair_space_layout.turning_space_diameter_mm", ">=", 1500, "mm", P_TURNING,
    "Annex §4.2.2.6",
    "A turning space, with a minimum diameter of 1 500 mm, shall be provided adjacent to the "
    "wheelchair space",
)  # fmt: skip
STAIR_HEIGHT = _rule(
    "stairs.step_height_mm", "<=", 200, "mm", P_STAIRS, "Annex §4.2.2.8",
    "Internal steps (other than those for external access) shall have a maximum height of 200 mm",
)  # fmt: skip
STAIR_DEPTH = _rule(
    "stairs.step_depth_mm", ">=", 280, "mm", P_STAIRS, "Annex §4.2.2.8",
    "Internal steps (other than those for external access) shall have a maximum height of 200 mm "
    "and a minimum depth of 280 mm",
)  # fmt: skip
STAIR_DEPTH_DOUBLE_DECK = _rule(
    "stairs.step_depth_mm", ">=", 270, "mm", P_STAIRS, "Annex §4.2.2.8",
    "For double deck trains it is permitted to reduce this value to 270 mm for the stairs "
    "accessing the upper deck and the lower deck.",
    conditions=[Condition(variable="deck_layout", op="==", value="double_deck")],
    relaxes=True,
)  # fmt: skip
HANDRAIL_DIAMETER = _rule(
    "handrails.outside_diameter_mm", "between", 30, "mm", P_HANDRAILS, "Annex §4.2.2.9",
    "All handrails fitted to a vehicle shall be round in section with an outside diameter of 30 mm "
    "to 40 mm",
    value_max=40,
)  # fmt: skip
SEAT_HEIGHT = _rule(
    "priority_seats.cushion_height_mm", "between", 430, "mm", P_PRIORITY, "Annex §4.2.2.1.2.1",
    "The top of each priority seat cushion shall be between 430 and 500 mm above floor level at "
    "the front edge of the seat.",
    value_max=500,
)  # fmt: skip

GOLD_RULES: dict[str, list[Requirement]] = {
    "wheelchair_spaces": [TABLE_5],
    "exterior_doors.clear_width_mm": [DOORS_ALL],
    "exterior_doors.wheelchair_door_clear_width_mm": [WHEELCHAIR_GENERAL, WHEELCHAIR_LEVEL],
    "steps.external_step_height_mm": [EXTERNAL_STEP],
    "steps.internal_step_height_mm": [INTERNAL_GENERAL, INTERNAL_EXCEPTION],
    "toilets.universal": [UNIVERSAL_TOILET],
    "toilets.universal_door_clear_width_mm": [UNIVERSAL_DOOR],
    "wheelchair_space_layout.width_mm": [SPACE_WIDTH],
    "wheelchair_space_layout.hand_clearance_mm": [HAND_CLEARANCE],
    "wheelchair_space_layout.turning_space_diameter_mm": [TURNING_SPACE],
    "stairs.step_height_mm": [STAIR_HEIGHT],
    "stairs.step_depth_mm": [STAIR_DEPTH, STAIR_DEPTH_DOUBLE_DECK],
    "handrails.outside_diameter_mm": [HANDRAIL_DIAMETER],
    "priority_seats.cushion_height_mm": [SEAT_HEIGHT],
}


def _combine(verdicts: list[str]) -> str:
    for v in ("fail", "needs_human", "pass"):
        if v in verdicts:
            return v
    return "not_applicable"


def oracle(spec: TrainSpec) -> dict[str, FinalVerdict]:
    """The verdict each supplied parameter should get, applying GOLD_RULES with `check`.

    A relaxation (see RuleDraft.relaxes) replaces a failed general rule where it is known to apply.
    Two reading rules are modelled by hand: a unit length that includes a power head is only an
    upper bound on the TSI's length, and an internal step between 200 and 230 mm is allowed only
    if it reduces the number of steps, which the spec cannot show.
    """
    values = spec_values(spec)
    context = {**values, **spec_categories(spec)}
    out: dict[str, FinalVerdict] = {}
    for parameter, rules in GOLD_RULES.items():
        if parameter not in values:
            continue
        results = [
            check(values[parameter], rule, spec_unit=None, context=context) for rule in rules
        ]
        verdicts = [r.verdict for r in results]
        relaxed = [r for r in results if r.relaxes and r.verdict == "pass"]
        if relaxed and "fail" in verdicts:
            # a relaxation known to apply replaces the general rule; one not known to apply leaves
            # the question to a person
            out[parameter] = "pass" if relaxed[0].applies else "needs_human"
            continue
        if parameter == "wheelchair_spaces" and values.get("length_includes_power_head"):
            required = results[0].required_value  # for the stated (upper-bound) length
            if values[parameter] >= required:
                out[parameter] = "pass"  # enough even at the upper bound
            elif values[parameter] < 1:
                out[parameter] = "fail"  # below the smallest requirement at any length
            else:
                out[parameter] = "needs_human"
            continue
        if parameter == "steps.internal_step_height_mm":
            general, exception = verdicts
            out[parameter] = (
                "pass" if general == "pass" else ("needs_human" if exception == "pass" else "fail")
            )
            continue
        out[parameter] = _combine(verdicts)
    return out
