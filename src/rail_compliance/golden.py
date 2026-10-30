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
from rail_compliance.parameters import REGULATION_OF, SUBJECT_OF
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


# Suites of the development set, by file prefix: the original twenty (core), the cases for the
# parameters added later (prm-extended), renewed units under Appendix F (renewal) and the Noise
# TSI (noise). Each runs
# and is gated on its own, so a free-tier day can hold one fresh run of any of them.
SUITES: dict[str, str] = {
    "core": "g*.json",
    "prm-extended": "p*.json",
    "renewal": "r*.json",
    "noise": "n*.json",
}


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

URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02014R1300-20230928"
NOISE_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02014R1304-20230928"
PRM = {"doc_id": "tsi-prm", "document": "PRM TSI", "url": URL}
NOI = {"doc_id": "tsi-noi", "document": "Noise TSI", "url": NOISE_URL}


def _rule(
    parameter, comparator, value, unit, passage, section, quote, conditions=(), bands=(),
    subject=None, value_max=None, relaxes=False, band_variable=None, regulation=None,
):  # fmt: skip
    regulation = regulation or PRM
    return Requirement(
        value_max=value_max,
        relaxes=relaxes,
        parameter=parameter,
        subject=subject or SUBJECT_OF[parameter],
        comparator=comparator,
        value=value,
        unit=unit,
        bands=list(bands),
        band_variable=band_variable or ("unit_length_m" if bands else None),
        conditions=list(conditions),
        citation=Citation(passage_id=passage, section=section, quote=quote, **regulation),
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

# --- Appendix F: exemptions for a renewed unit (comparator "exempt") -------------------------

RENEWED = Condition(variable="unit_status", op="==", value="renewed")
F = "tsi-prm:Appendix F"
F_HEIGHT = (
    "Compliance with the requirements of point 4.2.2.8 is not mandatory at renewal or upgrade."
)
F_STEPS = (
    "Compliance with the requirements of points 4.2.2.11 and 4.2.2.12 is not mandatory at renewal "
    "or upgrade."
)
F_HANDRAILS = (
    "Compliance with the requirements of point 4.2.2.9 is only mandatory where existing handrails "
    "are being renewed or upgraded."
)
F_PRIORITY = (
    "Compliance with point 4.2.2.1.2 with regard to the dimensions of priority seats and their "
    "surroundings is only mandatory if the seating layout is altered within an entire train and "
    "this can be achieved without reducing the existing capacity of the train."
)
F_SPACES = (
    "The provision of wheelchair spaces is only required when the seating layout is altered within "
    "a complete train formation."
)
F_SPACES_DOORWAY = (
    "if the entrance doorway, or clearways, cannot be modified to enable wheelchair access, a "
    "wheelchair space does not need to be provided if the seating layout is altered."
)
F_CLEARWAYS = (
    "Compliance with the requirements of point 4.2.2.6 is only mandatory if the seating layout is "
    "altered within an entire vehicle and a wheelchair space is being provided."
)
F_TOILETS = (
    "Provision of a fully compliant universal toilet is only mandatory when existing toilets are "
    "being completely renewed or upgraded and a wheelchair space is provided, and a compliant "
    "universal toilet can be accommodated without structural alteration to the vehicle body."
)
F_STRUCTURES = (
    "Compliance is not mandatory if the work would require structural alterations to door portals "
    "(interior or external)"
)


def _flag(name: str, value: float = 0) -> Condition:
    return Condition(variable=name, op="==", value=value)


NOT_IN_TRAIN = _flag("renewal.seating_layout_altered_in_entire_train")
NOT_IN_VEHICLE = _flag("renewal.seating_layout_altered_in_entire_vehicle")
NO_SPACES = _flag("wheelchair_spaces")


def _exempt(parameter, section, quote, conditions=(), contingency=None):
    return Requirement(
        parameter=parameter, subject=SUBJECT_OF[parameter], comparator="exempt",
        conditions=[RENEWED, *conditions], contingency=contingency,
        citation=Citation(passage_id=f"{F} §{section}#1", section=f"Appendix F §{section}",
                          quote=quote, **PRM),
    )  # fmt: skip


def _renewal_exemptions(parameter: str) -> list[Requirement]:
    """What Appendix F says about `parameter` for a renewed unit."""
    door = ("Structures", F_STRUCTURES, (),
            "the work would require structural alterations to door portals")  # fmt: skip
    toilet = [
        ("Toilets", F_TOILETS, (_flag("renewal.toilets_completely_renewed"),), None),
        ("Toilets", F_TOILETS, (NO_SPACES,), None),
        ("Toilets", F_TOILETS, (), "a compliant universal toilet cannot be accommodated without "
         "structural alteration to the vehicle body"),
    ]  # fmt: skip
    spaces = [("Wheelchair spaces", F_SPACES, (NOT_IN_TRAIN,), None)]
    table = {
        "wheelchair_spaces": [*spaces, ("Wheelchair spaces", F_SPACES_DOORWAY, (),
                              "the entrance doorway or clearways cannot be modified to enable "
                              "wheelchair access")],
        "exterior_doors.clear_width_mm": [door],
        "exterior_doors.wheelchair_door_clear_width_mm": [door],
        "steps.external_step_height_mm": [("Step positions, steps and boarding aids", F_STEPS, (),
                                           None)],
        "steps.internal_step_height_mm": [("Step positions, steps and boarding aids", F_STEPS, (),
                                           None)],
        "toilets.universal": toilet,
        "toilets.universal_door_clear_width_mm": [*toilet, door],
        "wheelchair_space_layout.width_mm": spaces,
        "wheelchair_space_layout.hand_clearance_mm": spaces,
        "wheelchair_space_layout.turning_space_diameter_mm": [
            ("Clearways", F_CLEARWAYS, (NOT_IN_VEHICLE,), None),
            ("Clearways", F_CLEARWAYS, (NO_SPACES,), None),
        ],
        "stairs.step_height_mm": [("Height Changes", F_HEIGHT, (), None)],
        "stairs.step_depth_mm": [("Height Changes", F_HEIGHT, (), None)],
        "handrails.outside_diameter_mm": [
            ("Handrails", F_HANDRAILS, (_flag("renewal.handrails_renewed"),), None)
        ],
        "priority_seats.cushion_height_mm": [
            ("Seats", F_PRIORITY, (NOT_IN_TRAIN,), None),
            ("Seats", F_PRIORITY, (), "the dimensions cannot be achieved without reducing the "
             "existing capacity of the train"),
        ],
    }  # fmt: skip
    return [_exempt(parameter, *row) for row in table.get(parameter, [])]


# --- the Noise TSI (Regulation (EU) No 1304/2014) -----------------------------------------

P_STATIONARY = "tsi-noi:Annex §4.2.1#1"
P_PASS_BY = "tsi-noi:Annex §4.2.3#1"
P_CAB = "tsi-noi:Annex §4.2.4#1"
CATEGORY = "rolling_stock_category"


def _rows(**rows: float) -> list[Band]:
    return [Band(category=c, value=v) for c, v in rows.items()]


STATIONARY = _rule(
    "noise.stationary_db", "<=", None, "dB", P_STATIONARY, "Annex §4.2.1",
    "Electric locomotives and special vehicles with electric traction | 70 | 75 | 85 Diesel "
    "locomotives and special vehicles with diesel traction | 71 | 78 EMUs | 65 | 68 DMUs | 72 | 76 "
    "Coaches | 64 | 68 Wagons | 65",
    bands=_rows(electric_locomotive=70, diesel_locomotive=71, emu=65, dmu=72, coach=64, wagon=65),
    band_variable=CATEGORY, regulation=NOI,
)  # fmt: skip
PASS_BY_80 = _rule(
    "noise.pass_by_80_db", "<=", None, "dB", P_PASS_BY, "Annex §4.2.3",
    "Electric locomotives and special vehicles with electric traction | 84 | 99 Diesel locomotives "
    "and special vehicles with diesel traction | 85 | n.a. EMUs | 80 | 95 DMUs | 81 | 96 Coaches | "
    "79 | n.a. Wagons (normalised to APL = 0,225) (1) | 83",
    bands=_rows(electric_locomotive=84, diesel_locomotive=85, emu=80, dmu=81, coach=79, wagon=83),
    band_variable=CATEGORY, regulation=NOI,
)  # fmt: skip
PASS_BY_250 = _rule(
    "noise.pass_by_250_db", "<=", None, "dB", P_PASS_BY, "Annex §4.2.3",
    "if applicable, at 250 km/h ... Electric locomotives and special vehicles with electric "
    "traction | 84 | 99 ... EMUs | 80 | 95 DMUs | 81 | 96",
    bands=_rows(electric_locomotive=99, emu=95, dmu=96),
    band_variable=CATEGORY, regulation=NOI,
    conditions=[Condition(variable="design_speed_kmh", op=">=", value=250)],
)  # fmt: skip
CAB_HORN = _rule(
    "noise.cab_standstill_horn_db", "<=", 95, "dB", P_CAB, "Annex §4.2.4",
    "coaches fitted with a cab are set out in Table 5 ... At standstill with horns sounding | 95",
    conditions=[Condition(variable="has_drivers_cab", op="==", value=1)], regulation=NOI,
)  # fmt: skip
CAB_SPEED = _rule(
    "noise.cab_max_speed_db", "<=", None, "dB", P_CAB, "Annex §4.2.4",
    "coaches fitted with a cab are set out in Table 5 ... At maximum speed vmax if vmax < 250 km/h "
    "| 78 At maximum speed vmax if 250 km/h ≤ vmax < 350 km/h | 80",
    bands=[Band(upper=250, upper_inclusive=False, value=78),
           Band(lower=250, upper=350, upper_inclusive=False, value=80)],
    band_variable="design_speed_kmh", regulation=NOI,
    conditions=[Condition(variable="has_drivers_cab", op="==", value=1)],
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
    "noise.stationary_db": [STATIONARY],
    "noise.pass_by_80_db": [PASS_BY_80],
    "noise.pass_by_250_db": [PASS_BY_250],
    "noise.cab_standstill_horn_db": [CAB_HORN],
    "noise.cab_max_speed_db": [CAB_SPEED],
}
GOLD_EXEMPTIONS: dict[str, list[Requirement]] = {p: _renewal_exemptions(p) for p in GOLD_RULES}


def _combine(verdicts: list[str]) -> str:
    for v in ("fail", "needs_human", "pass"):
        if v in verdicts:
            return v
    return "not_applicable"


def oracle(spec: TrainSpec) -> dict[str, FinalVerdict]:
    """The verdict each supplied parameter should get, applying GOLD_RULES with `check`.

    A relaxation (see RuleDraft.relaxes) replaces a failed general rule where it is known to apply.
    An exemption (GOLD_EXEMPTIONS, renewed units) that holds makes the parameter not_applicable;
    one that holds only if something is shown, or whose conditions are unknown, turns a failure
    into needs_human. Two reading rules are modelled by hand: a unit length that includes a power
    head is only an upper bound on the TSI's length, and an internal step between 200 and 230 mm
    is allowed only if it reduces the number of steps, which the spec cannot show.
    """
    values = spec_values(spec)
    context = {**values, **spec_categories(spec)}
    out: dict[str, FinalVerdict] = {}
    for parameter, rules in GOLD_RULES.items():
        if parameter not in values:
            continue
        if REGULATION_OF[parameter] == "tsi-noi" and context["unit_status"] == "renewed":
            out[parameter] = "needs_human"  # Noise TSI 7.2.1: limits of the first authorisation
            continue
        verdict = _rule_verdict(parameter, rules, values, context)
        exemptions = [
            check(values[parameter], e, context=context) for e in GOLD_EXEMPTIONS[parameter]
        ]
        if any(e.applies is True and not e.contingency for e in exemptions):
            verdict = "not_applicable"
        elif verdict == "fail" and any(
            e.applies is None or (e.applies and e.contingency) for e in exemptions
        ):
            verdict = "needs_human"
        out[parameter] = verdict
    return out


def _rule_verdict(parameter, rules, values, context) -> FinalVerdict:
    results = [check(values[parameter], rule, spec_unit=None, context=context) for rule in rules]
    verdicts = [r.verdict for r in results]
    relaxed = [r for r in results if r.relaxes and r.verdict == "pass"]
    if relaxed and "fail" in verdicts:
        # a relaxation known to apply replaces the general rule; one not known to apply leaves
        # the question to a person
        return "pass" if relaxed[0].applies else "needs_human"
    if parameter == "wheelchair_spaces" and values.get("length_includes_power_head"):
        required = results[0].required_value  # for the stated (upper-bound) length
        if values[parameter] >= required:
            return "pass"  # enough even at the upper bound
        if values[parameter] < 1:
            return "fail"  # below the smallest requirement at any length
        return "needs_human"
    if parameter == "steps.internal_step_height_mm":
        general, exception = verdicts
        return "pass" if general == "pass" else ("needs_human" if exception == "pass" else "fail")
    return _combine(verdicts)
