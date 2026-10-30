"""Writes eval/specs/g*.json and eval/GOLDEN_SET_REVIEW.md from the case table below.

The verdicts are written by hand from the text of the PRM TSI (Regulation (EU) No 1300/2014,
rolling stock, point 4.2.2 and 5.3.2). Every case is a NEW unit placed on the market after
28 September 2023 (point 7.1.2): the renewal and upgrade exemptions of Appendix F are out of
scope because the spec has no field for them.

    uv run python eval/build_golden.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from rail_compliance.golden import (
    P_CAB,
    P_DOORS,
    P_HANDRAILS,
    P_PASS_BY,
    P_PRIORITY,
    P_SPACE_DIMS,
    P_SPACES,
    P_STAIRS,
    P_STATIONARY,
    P_STEPS,
    P_TOILET,
    P_TURNING,
    P_UNIVERSAL,
    SUITES,
    GoldenCase,
)
from rail_compliance.spec import spec_categories, spec_values

HERE = Path(__file__).parent
RULE = ["search_regulation", "extract_requirement", "check"]
ESCALATE = ["search_regulation", "extract_requirement", "needs_human"]

SPACES = "wheelchair_spaces"
DOORS = "exterior_doors.clear_width_mm"
WC_DOOR = "exterior_doors.wheelchair_door_clear_width_mm"
EXT = "steps.external_step_height_mm"
INT = "steps.internal_step_height_mm"
UNIVERSAL = "toilets.universal"
UNI_DOOR = "toilets.universal_door_clear_width_mm"
SPACE_W = "wheelchair_space_layout.width_mm"
HANDS = "wheelchair_space_layout.hand_clearance_mm"
TURN = "wheelchair_space_layout.turning_space_diameter_mm"
STAIR_H = "stairs.step_height_mm"
STAIR_D = "stairs.step_depth_mm"
RAIL = "handrails.outside_diameter_mm"
SEAT = "priority_seats.cushion_height_mm"
F_RAILS = "tsi-prm:Appendix F §Handrails#1"
F_HEIGHT = "tsi-prm:Appendix F §Height Changes#1"
F_STEPS = "tsi-prm:Appendix F §Step positions, steps and boarding aids#1"
F_SPACES = "tsi-prm:Appendix F §Wheelchair spaces#1"
F_TOILETS = "tsi-prm:Appendix F §Toilets#1"
F_CLEARWAYS = "tsi-prm:Appendix F §Clearways#1"
F_SEATS = "tsi-prm:Appendix F §Seats#1"
F_STRUCTURES = "tsi-prm:Appendix F §Structures#1"
RENEWED = {"unit_length_m": 100.0, "unit_status": "renewed"}
STAT = "noise.stationary_db"
PB80 = "noise.pass_by_80_db"
PB250 = "noise.pass_by_250_db"
HORN = "noise.cab_standstill_horn_db"
CAB = "noise.cab_max_speed_db"
T2 = "Noise TSI 4.2.1 Table 2 (LpAeq,T[unit]: electric locomotives 70, diesel locomotives 71, EMUs 65, DMUs 72, coaches 64, wagons 65 dB)"
T4 = "Noise TSI 4.2.3 Table 4 (80 km/h: electric locomotives 84, diesel 85, EMUs 80, DMUs 81, coaches 79, wagons 83 dB; 250 km/h, if applicable: electric locomotives 99, EMUs 95, DMUs 96 dB)"
T5 = "Noise TSI 4.2.4 Table 5 (cab, for units fitted with a cab: standstill with horns 95 dB; at vmax 78 dB if vmax < 250 km/h, 80 dB if 250 ≤ vmax < 350 km/h)"


def unit(category, speed=None, cab=None, **noise):
    out = (
        {"unit_length_m": 100.0, "rolling_stock_category": category}
        if category
        else {"unit_length_m": 100.0}
    )
    if speed is not None:
        out["design_speed_kmh"] = speed
    if cab is not None:
        out["has_drivers_cab"] = cab
    return {**out, "noise": noise}


STAIRS_TEXT = "4.2.2.8(1): 'maximum height of 200 mm and a minimum depth of 280 mm ... For double deck trains it is permitted to reduce this value to 270 mm'"


def e(verdict, required, passages, rationale, tools=RULE, alt=()):
    return {
        "verdict": verdict,
        "required": required,
        "gold_passages": passages,
        "expected_tools": tools,
        "alt_tools": [list(a) for a in alt],
        "rationale": rationale,
    }


def case(id_, title, tags, why, spec, expected):
    return {
        "id": id_,
        "title": title,
        "tags": tags,
        "why": why,
        "spec": {"name": title, **spec},
        "expected": expected,
    }


TABLE_ROWS = "Table 5 of point 4.2.2.2(1)"

CASES = [
    case(
        "g01",
        "Compliant regional EMU",
        ["baseline"],
        "Every supplied value is comfortably inside its limit: no trap, a sanity floor.",
        {
            "unit_length_m": 105.0,
            "length_includes_power_head": False,
            "design_speed_kmh": 160,
            "wheelchair_spaces": 2,
            "exterior_doors": {
                "clear_width_mm": 850,
                "wheelchair_door_clear_width_mm": 1100,
                "wheelchair_door_level_access": True,
            },
            "steps": {"external_step_height_mm": 200, "internal_step_height_mm": 180},
            "toilets": {"fitted": 2, "universal": 1, "universal_door_clear_width_mm": 900},
        },
        {
            SPACES: e(
                "pass",
                "≥ 2 (30 to 205 m row)",
                [P_SPACES],
                f"{TABLE_ROWS}: 105 m is in the '30 to 205 metres' row, 2 spaces; 2 ≥ 2.",
            ),
            DOORS: e("pass", "≥ 800 mm", [P_DOORS], "4.2.2.3.2(1): 850 ≥ 800."),
            WC_DOOR: e(
                "pass",
                "≥ 1000 mm (and ≥ 800 mm)",
                [P_DOORS],
                "4.2.2.3.2(2) applies (160 < 250 km/h, level access): 1100 ≥ 1000, and ≥ 800.",
                RULE,
            ),
            EXT: e("pass", "≤ 230 mm", [P_STEPS], "4.2.2.11.2(5): 200 ≤ 230."),
            INT: e("pass", "≤ 200 mm", [P_STEPS], "4.2.2.11.2(2): 180 ≤ 200."),
            UNIVERSAL: e(
                "pass",
                "≥ 1 when toilets are fitted",
                [P_TOILET],
                "4.2.2.5(1): toilets are fitted (2) and 1 is universal.",
            ),
            UNI_DOOR: e(
                "pass",
                "≥ 800 mm",
                [P_UNIVERSAL],
                "5.3.2.4(3): 900 ≥ 800. The rule sits in 5.3.2.4, not in 4.2.2.5, which only points to it.",
            ),
        },
    ),
    case(
        "g02",
        "Regional train violating six rules",
        ["violation", "length-dependent"],
        "Every supplied rule is broken, including the internal step beyond even the 230 mm exception.",
        {
            "unit_length_m": 150.0,
            "length_includes_power_head": False,
            "design_speed_kmh": 160,
            "wheelchair_spaces": 1,
            "exterior_doors": {
                "clear_width_mm": 760,
                "wheelchair_door_clear_width_mm": 950,
                "wheelchair_door_level_access": True,
            },
            "steps": {"external_step_height_mm": 260, "internal_step_height_mm": 240},
            "toilets": {"fitted": 3, "universal": 0},
        },
        {
            SPACES: e(
                "fail",
                "≥ 2 (30 to 205 m row)",
                [P_SPACES],
                f"{TABLE_ROWS}: 150 m needs 2 spaces; 1 < 2.",
            ),
            DOORS: e("fail", "≥ 800 mm", [P_DOORS], "4.2.2.3.2(1): 760 < 800."),
            WC_DOOR: e(
                "fail",
                "≥ 1000 mm",
                [P_DOORS],
                "4.2.2.3.2(2) applies (160 < 250 km/h, level access): 950 < 1000.",
            ),
            EXT: e("fail", "≤ 230 mm", [P_STEPS], "4.2.2.11.2(5): 260 > 230."),
            INT: e(
                "fail",
                "≤ 200 mm (230 mm at most)",
                [P_STEPS],
                "4.2.2.11.2(2): 240 exceeds 200 and also exceeds the 230 mm the exception allows.",
                RULE,
            ),
            UNIVERSAL: e(
                "fail",
                "≥ 1 when toilets are fitted",
                [P_TOILET],
                "4.2.2.5(1): 3 toilets are fitted, 0 are universal.",
            ),
        },
    ),
    case(
        "g03",
        "Internal step exactly at the exception limit",
        ["needs-human", "exception", "exact-limit"],
        "230 mm is allowed only if the step count is reduced, which the spec cannot show.",
        {"unit_length_m": 100.0, "steps": {"internal_step_height_mm": 230}},
        {
            INT: e(
                "needs_human",
                "≤ 200 mm, or ≤ 230 mm if it reduces the number of steps",
                [P_STEPS],
                "4.2.2.11.2(2): 230 exceeds 200; the 230 mm maximum is allowed only 'if it can be demonstrated that this achieves a reduction of one in the total number of steps'. The spec has no such data: a person must decide.",
                ESCALATE,
                alt=[RULE],
            )
        },
    ),
    case(
        "g04",
        "Length exactly 30 m with one wheelchair space",
        ["table-boundary", "length-dependent", "exact-limit"],
        "'Less than 30 m' excludes 30: a 30 m unit is in the 2-space row.",
        {"unit_length_m": 30.0, "wheelchair_spaces": 1},
        {
            SPACES: e(
                "fail",
                "≥ 2 (30 to 205 m row)",
                [P_SPACES],
                f"{TABLE_ROWS}: 'Less than 30 m' is 1 space, '30 to 205 metres' is 2. 30 is in the second row, so 1 < 2.",
            )
        },
    ),
    case(
        "g05",
        "Length exactly 205 m with two wheelchair spaces",
        ["table-boundary", "length-dependent", "exact-limit"],
        "'30 to 205 metres' includes 205: still the 2-space row.",
        {"unit_length_m": 205.0, "wheelchair_spaces": 2},
        {
            SPACES: e(
                "pass",
                "≥ 2 (30 to 205 m row)",
                [P_SPACES],
                f"{TABLE_ROWS}: 205 is the top of '30 to 205 metres' (2 spaces); 2 ≥ 2.",
            )
        },
    ),
    case(
        "g06",
        "Length exactly 300 m with three wheelchair spaces",
        ["table-boundary", "length-dependent", "exact-limit"],
        "'More than 205 to 300 metres' includes 300: still the 3-space row.",
        {"unit_length_m": 300.0, "wheelchair_spaces": 3},
        {
            SPACES: e(
                "pass",
                "≥ 3 (205 to 300 m row)",
                [P_SPACES],
                f"{TABLE_ROWS}: 300 is the top of 'More than 205 to 300 metres' (3 spaces); 3 ≥ 3.",
            )
        },
    ),
    case(
        "g07",
        "Length 300.1 m with three wheelchair spaces",
        ["table-boundary", "length-dependent", "exact-limit"],
        "'More than 300 metres' starts just above 300: the 4-space row.",
        {"unit_length_m": 300.1, "wheelchair_spaces": 3},
        {
            SPACES: e(
                "fail",
                "≥ 4 (over 300 m row)",
                [P_SPACES],
                f"{TABLE_ROWS}: 300.1 is 'More than 300 metres' (4 spaces); 3 < 4.",
            )
        },
    ),
    case(
        "g08",
        "Every value exactly at its limit",
        ["exact-limit", "other-section", "length-dependent"],
        "Each limit is met with equality, so every rule must read as a pass (30 m is also a table boundary).",
        {
            "unit_length_m": 30.0,
            "length_includes_power_head": False,
            "design_speed_kmh": 160,
            "wheelchair_spaces": 2,
            "exterior_doors": {
                "clear_width_mm": 800,
                "wheelchair_door_clear_width_mm": 1000,
                "wheelchair_door_level_access": True,
            },
            "steps": {"external_step_height_mm": 230, "internal_step_height_mm": 200},
            "toilets": {"fitted": 1, "universal": 1, "universal_door_clear_width_mm": 800},
        },
        {
            SPACES: e(
                "pass",
                "≥ 2 (30 to 205 m row)",
                [P_SPACES],
                f"{TABLE_ROWS}: 30 m is in the 2-space row; 2 ≥ 2.",
            ),
            DOORS: e(
                "pass",
                "≥ 800 mm",
                [P_DOORS],
                "4.2.2.3.2(1): 800 ≥ 800 ('minimum' includes the value).",
            ),
            WC_DOOR: e(
                "pass",
                "≥ 1000 mm (and ≥ 800 mm)",
                [P_DOORS],
                "4.2.2.3.2(2) applies (160 km/h, level access): 1000 ≥ 1000.",
            ),
            EXT: e(
                "pass",
                "≤ 230 mm",
                [P_STEPS],
                "4.2.2.11.2(5): 230 ≤ 230 ('maximum' includes the value).",
            ),
            INT: e("pass", "≤ 200 mm", [P_STEPS], "4.2.2.11.2(2): 200 ≤ 200."),
            UNIVERSAL: e(
                "pass",
                "≥ 1 when toilets are fitted",
                [P_TOILET],
                "4.2.2.5(1): 1 toilet fitted, 1 universal.",
            ),
            UNI_DOOR: e("pass", "≥ 800 mm", [P_UNIVERSAL], "5.3.2.4(3): 800 ≥ 800."),
        },
    ),
    case(
        "g09",
        "Every value just past its limit",
        ["exact-limit", "other-section", "violation", "length-dependent"],
        "Each limit is missed by the smallest step (0.1 mm, one table row): no rule may pass.",
        {
            "unit_length_m": 205.1,
            "length_includes_power_head": False,
            "design_speed_kmh": 160,
            "wheelchair_spaces": 2,
            "exterior_doors": {
                "clear_width_mm": 799.9,
                "wheelchair_door_clear_width_mm": 999.9,
                "wheelchair_door_level_access": True,
            },
            "steps": {"external_step_height_mm": 230.1, "internal_step_height_mm": 230.1},
            "toilets": {"fitted": 1, "universal": 1, "universal_door_clear_width_mm": 799.9},
        },
        {
            SPACES: e(
                "fail",
                "≥ 3 (205 to 300 m row)",
                [P_SPACES],
                f"{TABLE_ROWS}: 205.1 is 'More than 205 to 300 metres' (3 spaces); 2 < 3.",
            ),
            DOORS: e("fail", "≥ 800 mm", [P_DOORS], "4.2.2.3.2(1): 799.9 < 800."),
            WC_DOOR: e(
                "fail",
                "≥ 1000 mm",
                [P_DOORS],
                "4.2.2.3.2(2) applies (160 km/h, level access): 999.9 < 1000.",
            ),
            EXT: e("fail", "≤ 230 mm", [P_STEPS], "4.2.2.11.2(5): 230.1 > 230."),
            INT: e(
                "fail",
                "≤ 200 mm (230 mm at most)",
                [P_STEPS],
                "4.2.2.11.2(2): 230.1 exceeds even the 230 mm the exception allows, so no demonstration could save it.",
            ),
            UNIVERSAL: e(
                "pass",
                "≥ 1 when toilets are fitted",
                [P_TOILET],
                "4.2.2.5(1): 1 toilet fitted, 1 universal.",
            ),
            UNI_DOOR: e("fail", "≥ 800 mm", [P_UNIVERSAL], "5.3.2.4(3): 799.9 < 800."),
        },
    ),
    case(
        "g10",
        "300 km/h train, wheelchair door 780 mm",
        ["conditional-rule", "high-speed"],
        "The 1000 mm rule needs a speed below 250 km/h, but the general 800 mm rule still applies to the wheelchair door.",
        {
            "unit_length_m": 200.0,
            "design_speed_kmh": 300,
            "exterior_doors": {
                "wheelchair_door_clear_width_mm": 780,
                "wheelchair_door_level_access": True,
            },
        },
        {
            WC_DOOR: e(
                "fail",
                "≥ 800 mm (the 1000 mm rule does not apply at 300 km/h)",
                [P_DOORS],
                "4.2.2.3.2(2) is for 'a design speed lower than 250 km/h': not met. 4.2.2.3.2(1) covers 'all exterior passenger doorways': 780 < 800.",
            )
        },
    ),
    case(
        "g11",
        "300 km/h train, wheelchair door 900 mm",
        ["conditional-rule", "high-speed"],
        "Above 250 km/h only the 800 mm rule applies, so 900 mm passes; a 1000 mm rule wrongly applied would fail it.",
        {
            "unit_length_m": 200.0,
            "design_speed_kmh": 300,
            "exterior_doors": {
                "wheelchair_door_clear_width_mm": 900,
                "wheelchair_door_level_access": True,
            },
        },
        {
            WC_DOOR: e(
                "pass",
                "≥ 800 mm (the 1000 mm rule does not apply at 300 km/h)",
                [P_DOORS],
                "4.2.2.3.2(2) does not apply at 300 km/h; 4.2.2.3.2(1): 900 ≥ 800.",
            )
        },
    ),
    case(
        "g12",
        "160 km/h train, wheelchair door 900 mm without level access",
        ["conditional-rule"],
        "The 1000 mm rule is only for doors 'offering a level access': without it only 800 mm applies.",
        {
            "unit_length_m": 100.0,
            "design_speed_kmh": 160,
            "exterior_doors": {
                "wheelchair_door_clear_width_mm": 900,
                "wheelchair_door_level_access": False,
            },
        },
        {
            WC_DOOR: e(
                "pass",
                "≥ 800 mm (the 1000 mm rule needs level access)",
                [P_DOORS],
                "4.2.2.3.2(2) is limited to doors 'offering a level access': this door does not. 4.2.2.3.2(1): 900 ≥ 800.",
            )
        },
    ),
    case(
        "g13",
        "Design speed exactly 250 km/h",
        ["conditional-rule", "exact-limit", "judgment-call"],
        "The text says 'lower than 250 km/h'; 250 is not lower. JUDGMENT CALL for your review.",
        {
            "unit_length_m": 100.0,
            "design_speed_kmh": 250,
            "exterior_doors": {
                "wheelchair_door_clear_width_mm": 900,
                "wheelchair_door_level_access": True,
            },
        },
        {
            WC_DOOR: e(
                "pass",
                "≥ 800 mm (read literally, the 1000 mm rule needs a speed below 250)",
                [P_DOORS],
                "4.2.2.3.2(2) says 'lower than 250 km/h', so it does not apply at exactly 250; 4.2.2.3.2(1): 900 ≥ 800. A cautious engineer might still ask whether the boundary was intended; this case expects the literal reading.",
            )
        },
    ),
    case(
        "g14",
        "Wheelchair door rule needs a design speed the spec omits",
        ["missing-data", "needs-human", "conditional-rule"],
        "Whether the 1000 mm rule applies depends on design speed, which is not supplied.",
        {
            "unit_length_m": 100.0,
            "exterior_doors": {
                "wheelchair_door_clear_width_mm": 900,
                "wheelchair_door_level_access": True,
            },
        },
        {
            WC_DOOR: e(
                "needs_human",
                "≥ 1000 mm if design speed < 250 km/h, else ≥ 800 mm",
                [P_DOORS],
                "900 passes 800 but fails 1000, and whether 4.2.2.3.2(2) applies depends on the design speed, which the spec does not give.",
                RULE,
                alt=[ESCALATE],
            )
        },
    ),
    case(
        "g15",
        "Wheelchair door rule needs level-access data the spec omits",
        ["missing-data", "needs-human", "conditional-rule"],
        "Whether the 1000 mm rule applies depends on level access, which is not supplied.",
        {
            "unit_length_m": 100.0,
            "design_speed_kmh": 160,
            "exterior_doors": {"wheelchair_door_clear_width_mm": 900},
        },
        {
            WC_DOOR: e(
                "needs_human",
                "≥ 1000 mm if the door offers level access, else ≥ 800 mm",
                [P_DOORS],
                "At 160 km/h, 4.2.2.3.2(2) applies if the door offers level access; the spec does not say. 900 passes 800 but fails 1000.",
                RULE,
                alt=[ESCALATE],
            )
        },
    ),
    case(
        "g16",
        "Internal step of 215 mm",
        ["needs-human", "exception"],
        "Above the 200 mm default but within the 230 mm exception, which needs a demonstration the spec cannot give.",
        {"unit_length_m": 100.0, "steps": {"internal_step_height_mm": 215}},
        {
            INT: e(
                "needs_human",
                "≤ 200 mm, or ≤ 230 mm if it reduces the number of steps",
                [P_STEPS],
                "4.2.2.11.2(2): 215 exceeds 200 but not 230; it is allowed only 'if it can be demonstrated' that it reduces the total number of steps by one. A person must decide.",
                ESCALATE,
                alt=[RULE],
            )
        },
    ),
    case(
        "g17",
        "Train with no toilets",
        ["not-applicable"],
        "'When toilets are fitted' is false, so no universal toilet is required: not a pass, not a fail.",
        {"unit_length_m": 100.0, "toilets": {"fitted": 0, "universal": 0}},
        {
            UNIVERSAL: e(
                "not_applicable",
                "≥ 1 only when toilets are fitted",
                [P_TOILET],
                "4.2.2.5(1) applies 'when toilets are fitted in a train'; none are fitted.",
            )
        },
    ),
    case(
        "g18",
        "Toilets fitted but none universal",
        ["violation"],
        "Toilets are fitted, so a universal toilet is required.",
        {"unit_length_m": 100.0, "toilets": {"fitted": 2, "universal": 0}},
        {
            UNIVERSAL: e(
                "fail",
                "≥ 1 when toilets are fitted",
                [P_TOILET],
                "4.2.2.5(1): 2 toilets are fitted and 0 are universal.",
            )
        },
    ),
    case(
        "g19",
        "Length includes a power head, two wheelchair spaces",
        ["needs-human", "length-dependent", "ambiguous-data"],
        "Table 5 uses the unit length 'excluding the locomotive or power head'. At 210 m 3 spaces are needed, at 205 m or less 2: the true length is unknown.",
        {"unit_length_m": 210.0, "length_includes_power_head": True, "wheelchair_spaces": 2},
        {
            SPACES: e(
                "needs_human",
                "≥ 2 or ≥ 3 depending on the length without the power head",
                [P_SPACES],
                "4.2.2.2(1) counts the length 'excluding the locomotive or power head'. The stated 210 m includes it, so the true length is ≤ 210 m: it needs 3 spaces if above 205 m and 2 if not. The spec cannot settle it.",
                ESCALATE,
                alt=[RULE],
            )
        },
    ),
    case(
        "g20",
        "Length includes a power head, three wheelchair spaces",
        ["length-dependent", "ambiguous-data"],
        "Same length basis problem, but 3 spaces meet the largest possible requirement (3 up to 300 m), so the answer is safe.",
        {"unit_length_m": 210.0, "length_includes_power_head": True, "wheelchair_spaces": 3},
        {
            SPACES: e(
                "pass",
                "≥ 3 (at most, for a length up to 210 m)",
                [P_SPACES],
                f"{TABLE_ROWS}: whatever the power head's length, the true length is ≤ 210 m, which needs at most 3 spaces; 3 ≥ 3.",
            )
        },
    ),
    # --- suite prm-extended (p*): seven more parameters (4.2.2.1.2.1, 4.2.2.2, 4.2.2.6, 4.2.2.8, 4.2.2.9)
    case(
        "p01",
        "Handrail diameter at the bottom of the range",
        ["range", "exact-limit"],
        "'30 mm to 40 mm' includes 30.",
        {"unit_length_m": 100.0, "handrails": {"outside_diameter_mm": 30}},
        {
            RAIL: e(
                "pass",
                "30–40 mm",
                [P_HANDRAILS],
                "4.2.2.9(1): 'outside diameter of 30 mm to 40 mm'; 30 is the lower bound, included.",
            )
        },
    ),
    case(
        "p02",
        "Handrail too thick, priority seat at the top of the range",
        ["range", "exact-limit"],
        "A range fails above its upper bound; 'between 430 and 500 mm' includes 500.",
        {
            "unit_length_m": 100.0,
            "handrails": {"outside_diameter_mm": 41},
            "priority_seats": {"cushion_height_mm": 500},
        },
        {
            RAIL: e(
                "fail",
                "30–40 mm",
                [P_HANDRAILS],
                "4.2.2.9(1): 41 mm is above the 40 mm upper bound.",
            ),
            SEAT: e(
                "pass",
                "430–500 mm",
                [P_PRIORITY],
                "4.2.2.1.2.1(9): 'between 430 and 500 mm above floor level'; 500 is the upper bound, included.",
            ),
        },
    ),
    case(
        "p03",
        "Priority seat too low",
        ["range"],
        "A range fails below its lower bound.",
        {"unit_length_m": 100.0, "priority_seats": {"cushion_height_mm": 425}},
        {
            SEAT: e(
                "fail",
                "430–500 mm",
                [P_PRIORITY],
                "4.2.2.1.2.1(9): 425 mm is below the 430 mm lower bound.",
            )
        },
    ),
    case(
        "p04",
        "Wheelchair space and turning space exactly at the minimum",
        ["exact-limit"],
        "Both minimums are inclusive.",
        {
            "unit_length_m": 100.0,
            "wheelchair_space_layout": {"width_mm": 700, "turning_space_diameter_mm": 1500},
        },
        {
            SPACE_W: e(
                "pass",
                "≥ 700 mm",
                [P_SPACE_DIMS],
                "4.2.2.2(3): 'the width shall be 700 mm', read as a minimum; 700 ≥ 700.",
            ),
            TURN: e(
                "pass",
                "≥ 1500 mm",
                [P_TURNING],
                "4.2.2.6(3): 'a minimum diameter of 1 500 mm'; 1500 ≥ 1500.",
            ),
        },
    ),
    case(
        "p05",
        "Wheelchair space and turning space too small",
        ["thousand-separator"],
        "Just below both minimums; the regulation writes 1 500 with a space.",
        {
            "unit_length_m": 100.0,
            "wheelchair_space_layout": {"width_mm": 690, "turning_space_diameter_mm": 1450},
        },
        {
            SPACE_W: e("fail", "≥ 700 mm", [P_SPACE_DIMS], "4.2.2.2(3): 690 < 700."),
            TURN: e("fail", "≥ 1500 mm", [P_TURNING], "4.2.2.6(3): 1450 < 1500."),
        },
    ),
    case(
        "p06",
        "Hand clearance on a side next to a wall",
        ["conditional", "exact-limit"],
        "The extra 50 mm applies on each side next to an obstacle; one side is.",
        {
            "unit_length_m": 100.0,
            "wheelchair_space_layout": {"sides_next_to_obstacle": 1, "hand_clearance_mm": 50},
        },
        {
            HANDS: e(
                "pass",
                "≥ 50 mm (side next to an obstacle)",
                [P_SPACE_DIMS],
                "4.2.2.2(3): 'an additional 50 mm width ... on each side that is adjacent to any obstacle'; 50 ≥ 50.",
            )
        },
    ),
    case(
        "p07",
        "Too little hand clearance, sides not stated",
        ["conditional", "missing-data", "needs-human"],
        "40 mm fails the rule if any side is next to an obstacle, and the spec does not say: a person decides.",
        {"unit_length_m": 100.0, "wheelchair_space_layout": {"hand_clearance_mm": 40}},
        {
            HANDS: e(
                "needs_human",
                "≥ 50 mm if a side is next to an obstacle",
                [P_SPACE_DIMS],
                "4.2.2.2(3): the 50 mm applies only to sides next to an obstacle; sides_next_to_obstacle is not supplied and 40 < 50, so the answer depends on it.",
                alt=[ESCALATE],
            )
        },
    ),
    case(
        "p08",
        "Wheelchair space open on both sides",
        ["conditional", "not-applicable"],
        "No side is next to an obstacle, so the extra-width rule does not apply.",
        {
            "unit_length_m": 100.0,
            "wheelchair_space_layout": {"sides_next_to_obstacle": 0, "hand_clearance_mm": 20},
        },
        {
            HANDS: e(
                "not_applicable",
                None,
                [P_SPACE_DIMS],
                "4.2.2.2(3): 'if one side of the wheelchair is adjacent to the aisle there is no additional 50 mm requirement for that side'; with no side next to an obstacle the rule has nothing to apply to.",
            )
        },
    ),
    case(
        "p09",
        "Single-deck stairs: height at the limit, depth too short",
        ["category", "exact-limit"],
        "The 270 mm depth is permitted only on double deck trains.",
        {
            "unit_length_m": 100.0,
            "deck_layout": "single_deck",
            "stairs": {"step_height_mm": 200, "step_depth_mm": 275},
        },
        {
            STAIR_H: e("pass", "≤ 200 mm", [P_STAIRS], f"{STAIRS_TEXT}: 200 ≤ 200."),
            STAIR_D: e(
                "fail",
                "≥ 280 mm",
                [P_STAIRS],
                f"{STAIRS_TEXT}: the unit is single deck, so 280 mm applies; 275 < 280.",
            ),
        },
    ),
    case(
        "p10",
        "Double-deck stairs with the relaxed depth",
        ["category", "relaxation"],
        "On a double deck train 275 mm meets the permitted 270 mm, though not the general 280 mm.",
        {
            "unit_length_m": 100.0,
            "deck_layout": "double_deck",
            "stairs": {"step_height_mm": 210, "step_depth_mm": 275},
        },
        {
            STAIR_H: e(
                "fail",
                "≤ 200 mm",
                [P_STAIRS],
                f"{STAIRS_TEXT}: the relaxation is for the depth only; 210 > 200.",
            ),
            STAIR_D: e(
                "pass",
                "≥ 270 mm (double deck)",
                [P_STAIRS],
                f"{STAIRS_TEXT}: double deck, so 270 mm is permitted; 275 ≥ 270.",
            ),
        },
    ),
    case(
        "p11",
        "Stair depth between the two limits, deck layout not stated",
        ["category", "relaxation", "missing-data", "needs-human"],
        "275 mm passes only if the train is double deck, which the spec does not say.",
        {"unit_length_m": 100.0, "stairs": {"step_depth_mm": 275}},
        {
            STAIR_D: e(
                "needs_human",
                "≥ 280 mm, or ≥ 270 mm if double deck",
                [P_STAIRS],
                f"{STAIRS_TEXT}: 275 fails 280 and meets 270; deck_layout is not supplied.",
                alt=[ESCALATE],
            )
        },
    ),
    case(
        "p12",
        "Double-deck stairs below even the relaxed depth",
        ["category", "relaxation"],
        "The relaxation does not save a value below 270 mm.",
        {"unit_length_m": 100.0, "deck_layout": "double_deck", "stairs": {"step_depth_mm": 265}},
        {STAIR_D: e("fail", "≥ 270 mm (double deck)", [P_STAIRS], f"{STAIRS_TEXT}: 265 < 270.")},
    ),
    # --- suite renewal (r*): renewed units under Appendix F ---------------------------------
    case(
        "r01",
        "Renewal keeps the old handrails",
        ["renewal", "exemption"],
        "4.2.2.9 is only mandatory where existing handrails are renewed: these were not.",
        {
            **RENEWED,
            "renewal": {"handrails_renewed": False},
            "handrails": {"outside_diameter_mm": 45},
        },
        {
            RAIL: e(
                "not_applicable",
                None,
                [F_RAILS],
                "Appendix F, Handrails: 'only mandatory where existing handrails are being renewed or upgraded'; handrails_renewed is false, so 45 mm need not meet 30–40 mm.",
            )
        },
    ),
    case(
        "r02",
        "Renewal replaces the handrails with thick ones",
        ["renewal", "exemption"],
        "Renewed handrails must comply.",
        {
            **RENEWED,
            "renewal": {"handrails_renewed": True},
            "handrails": {"outside_diameter_mm": 45},
        },
        {
            RAIL: e(
                "fail",
                "30–40 mm",
                [P_HANDRAILS, F_RAILS],
                "Appendix F, Handrails: the handrails are renewed, so 4.2.2.9(1) applies; 45 > 40.",
            )
        },
    ),
    case(
        "r03",
        "Renewal that does not say what happened to the handrails",
        ["renewal", "exemption", "missing-data", "needs-human"],
        "45 mm fails unless the handrails were kept, and the spec does not say.",
        {**RENEWED, "renewal": {}, "handrails": {"outside_diameter_mm": 45}},
        {
            RAIL: e(
                "needs_human",
                "30–40 mm, unless the handrails are not renewed",
                [P_HANDRAILS, F_RAILS],
                "4.2.2.9(1) fails (45 > 40); Appendix F exempts handrails that are not renewed, and handrails_renewed is not supplied.",
                alt=[ESCALATE],
            )
        },
    ),
    case(
        "r04",
        "Renewal that complies anyway",
        ["renewal", "exemption", "missing-data"],
        "35 mm meets 30–40 mm, so whether the exemption holds does not matter.",
        {**RENEWED, "handrails": {"outside_diameter_mm": 35}},
        {
            RAIL: e(
                "pass",
                "30–40 mm",
                [P_HANDRAILS],
                "4.2.2.9(1): 35 is within 30–40 mm; the Appendix F exemption could only remove the rule.",
                alt=[["search_regulation", "extract_requirement", "check"]],
            )
        },
    ),
    case(
        "r05",
        "Renewal with steep stairs and a high external step",
        ["renewal", "exemption"],
        "4.2.2.8 and 4.2.2.11 are not mandatory at renewal or upgrade.",
        {**RENEWED, "stairs": {"step_height_mm": 220}, "steps": {"external_step_height_mm": 260}},
        {
            STAIR_H: e(
                "not_applicable",
                None,
                [F_HEIGHT],
                "Appendix F, Height Changes: 'Compliance with the requirements of point 4.2.2.8 is not mandatory at renewal or upgrade.'",
            ),
            EXT: e(
                "not_applicable",
                None,
                [F_STEPS],
                "Appendix F, Step positions: 'Compliance with the requirements of points 4.2.2.11 and 4.2.2.12 is not mandatory at renewal or upgrade.'",
            ),
        },
    ),
    case(
        "r06",
        "Renewal that keeps the seating layout, no wheelchair space",
        ["renewal", "exemption", "length-dependent"],
        "Wheelchair spaces are only required when the layout is altered within a complete train.",
        {
            **RENEWED,
            "renewal": {"seating_layout_altered_in_entire_train": False},
            "wheelchair_spaces": 0,
        },
        {
            SPACES: e(
                "not_applicable",
                None,
                [F_SPACES],
                "Appendix F, Wheelchair spaces: 'only required when the seating layout is altered within a complete train formation'; it was not.",
            )
        },
    ),
    case(
        "r07",
        "Renewal that alters the whole layout but adds one wheelchair space",
        ["renewal", "exemption", "needs-human"],
        "Table 5 needs 2 at 100 m; Appendix F waives spaces only if the doorways cannot be modified, which the spec cannot show.",
        {
            **RENEWED,
            "renewal": {"seating_layout_altered_in_entire_train": True},
            "wheelchair_spaces": 1,
        },
        {
            SPACES: e(
                "needs_human",
                "≥ 2, unless the doorways cannot be modified",
                [P_SPACES, F_SPACES],
                "Table 5: 1 < 2 at 100 m. Appendix F: 'if the entrance doorway, or clearways, cannot be modified to enable wheelchair access, a wheelchair space does not need to be provided'. A person must judge the doorways.",
                alt=[ESCALATE],
            )
        },
    ),
    case(
        "r08",
        "Renewal that keeps the old toilets",
        ["renewal", "exemption"],
        "A universal toilet is only mandatory when the toilets are completely renewed.",
        {
            **RENEWED,
            "renewal": {"toilets_completely_renewed": False},
            "toilets": {"fitted": 2, "universal": 0},
        },
        {
            UNIVERSAL: e(
                "not_applicable",
                None,
                [F_TOILETS],
                "Appendix F, Toilets: 'only mandatory when existing toilets are being completely renewed or upgraded'; they are not.",
            )
        },
    ),
    case(
        "r09",
        "Renewal that alters a vehicle's layout with a small turning space",
        ["renewal", "exemption"],
        "4.2.2.6 is mandatory when a vehicle's layout is altered and a wheelchair space is provided: both hold.",
        {
            **RENEWED,
            "renewal": {"seating_layout_altered_in_entire_vehicle": True},
            "wheelchair_spaces": 2,
            "wheelchair_space_layout": {"turning_space_diameter_mm": 1400},
        },
        {
            TURN: e(
                "fail",
                "≥ 1500 mm",
                [P_TURNING, F_CLEARWAYS],
                "Appendix F, Clearways: the layout is altered within an entire vehicle and 2 wheelchair spaces are provided, so 4.2.2.6(3) applies; 1400 < 1500.",
            )
        },
    ),
    case(
        "r10",
        "Renewal with a narrow exterior door",
        ["renewal", "exemption", "needs-human"],
        "800 mm is required, but widening a door portal is a structural alteration, which Appendix F does not require.",
        {**RENEWED, "exterior_doors": {"clear_width_mm": 750}},
        {
            DOORS: e(
                "needs_human",
                "≥ 800 mm, unless it needs structural alteration to the door portal",
                [P_DOORS, F_STRUCTURES],
                "4.2.2.3.2(1): 750 < 800. Appendix F, Structures: 'Compliance is not mandatory if the work would require structural alterations to door portals'. A person must judge the work.",
                alt=[ESCALATE],
            )
        },
    ),
    # --- suite noise (n*): the Noise TSI (Regulation (EU) No 1304/2014), new units -----------
    case(
        "n01",
        "EMU at the stationary and 80 km/h pass-by limits",
        ["noise", "category-table", "exact-limit", "cross-document"],
        "The EMU rows apply; the PRM TSI's dB figures for door signals are not noise limits.",
        unit("emu", stationary_db=65, pass_by_80_db=80),
        {
            STAT: e("pass", "≤ 65 dB (EMUs)", [P_STATIONARY], f"{T2}: EMU row, 65 ≤ 65."),
            PB80: e("pass", "≤ 80 dB (EMUs)", [P_PASS_BY], f"{T4}: EMU row, 80 ≤ 80."),
        },
    ),
    case(
        "n02",
        "Coach with an EMU-level stationary noise",
        ["noise", "category-table"],
        "65 dB is the EMU limit but a coach's is 64: the category decides.",
        unit("coach", stationary_db=65, pass_by_80_db=79),
        {
            STAT: e("fail", "≤ 64 dB (coaches)", [P_STATIONARY], f"{T2}: coach row, 65 > 64."),
            PB80: e("pass", "≤ 79 dB (coaches)", [P_PASS_BY], f"{T4}: coach row, 79 ≤ 79."),
        },
    ),
    case(
        "n03",
        "DMU too loud at 80 km/h",
        ["noise", "category-table"],
        "The DMU row: 72 dB stationary is allowed, 82 dB pass-by is not.",
        unit("dmu", stationary_db=72, pass_by_80_db=82),
        {
            STAT: e("pass", "≤ 72 dB (DMUs)", [P_STATIONARY], f"{T2}: DMU row, 72 ≤ 72."),
            PB80: e("fail", "≤ 81 dB (DMUs)", [P_PASS_BY], f"{T4}: DMU row, 82 > 81."),
        },
    ),
    case(
        "n04",
        "High-speed EMU within every limit",
        ["noise", "category-table", "table-boundary", "exact-limit"],
        "300 km/h: the 250 km/h pass-by applies, and the cab row for 250 to 350 km/h.",
        unit(
            "emu",
            speed=300,
            cab=True,
            pass_by_250_db=95,
            cab_standstill_horn_db=95,
            cab_max_speed_db=80,
        ),
        {
            PB250: e(
                "pass",
                "≤ 95 dB (EMUs, 250 km/h)",
                [P_PASS_BY],
                f"{T4}: the design speed is 300 km/h, so the 250 km/h limit applies; EMU 95 ≤ 95.",
            ),
            HORN: e("pass", "≤ 95 dB", [P_CAB], f"{T5}: 95 ≤ 95."),
            CAB: e(
                "pass",
                "≤ 80 dB (250 to 350 km/h)",
                [P_CAB],
                f"{T5}: 250 ≤ 300 < 350, so 80 dB; 80 ≤ 80.",
            ),
        },
    ),
    case(
        "n05",
        "Regional EMU with a loud cab",
        ["noise", "table-boundary"],
        "Below 250 km/h the cab limit at maximum speed is 78 dB.",
        unit("emu", speed=200, cab=True, cab_standstill_horn_db=96, cab_max_speed_db=79),
        {
            HORN: e("fail", "≤ 95 dB", [P_CAB], f"{T5}: 96 > 95."),
            CAB: e(
                "fail", "≤ 78 dB (vmax < 250 km/h)", [P_CAB], f"{T5}: 200 < 250, so 78 dB; 79 > 78."
            ),
        },
    ),
    case(
        "n06",
        "250 km/h pass-by measured on a 200 km/h EMU",
        ["noise", "conditional", "not-applicable"],
        "The 250 km/h limit applies only to units that run at 250 km/h.",
        unit("emu", speed=200, pass_by_250_db=97),
        {
            PB250: e(
                "not_applicable",
                None,
                [P_PASS_BY],
                f"{T4}: the 250 km/h value applies 'if applicable'; read as design speed ≥ 250 km/h. At 200 km/h it does not apply.",
            )
        },
    ),
    case(
        "n07",
        "Coach without a cab",
        ["noise", "conditional", "not-applicable"],
        "The cab limits are for units fitted with a cab.",
        unit("coach", cab=False, cab_standstill_horn_db=97),
        {
            HORN: e(
                "not_applicable",
                None,
                [P_CAB],
                f"{T5}: has_drivers_cab is false, so there is no cab to limit.",
            )
        },
    ),
    case(
        "n08",
        "Category not stated",
        ["noise", "category-table", "missing-data", "needs-human"],
        "70 dB meets some rows of Table 2 and not others; 78 dB meets every row of Table 4.",
        unit(None, stationary_db=70, pass_by_80_db=78),
        {
            STAT: e(
                "needs_human",
                "≤ 64 to 72 dB, by category",
                [P_STATIONARY],
                f"{T2}: 70 meets the electric locomotive, diesel and DMU rows and fails the others; the category is not supplied.",
                alt=[ESCALATE],
            ),
            PB80: e(
                "pass",
                "≤ 79 dB (the lowest row)",
                [P_PASS_BY],
                f"{T4}: 78 is within every row (the lowest is 79), so the category does not matter.",
            ),
        },
    ),
    case(
        "n09",
        "Electric locomotive too loud passing by",
        ["noise", "category-table"],
        "The locomotive rows are higher than the EMU rows.",
        unit("electric_locomotive", stationary_db=70, pass_by_80_db=85),
        {
            STAT: e("pass", "≤ 70 dB (electric locomotives)", [P_STATIONARY], f"{T2}: 70 ≤ 70."),
            PB80: e("fail", "≤ 84 dB (electric locomotives)", [P_PASS_BY], f"{T4}: 85 > 84."),
        },
    ),
    case(
        "n10",
        "Cab noise with the design speed not stated",
        ["noise", "missing-data", "needs-human"],
        "79 dB meets the 80 dB row and fails the 78 dB row; the speed picks the row.",
        unit("emu", cab=True, cab_max_speed_db=79),
        {
            CAB: e(
                "needs_human",
                "≤ 78 or 80 dB, by design speed",
                [P_CAB],
                f"{T5}: the row depends on vmax, which is not supplied; 79 passes one row and fails the other.",
                alt=[ESCALATE],
            )
        },
    ),
]


def slug(title: str) -> str:
    words = re.sub(r"[^a-z0-9]+", " ", title.lower()).split()
    return "_".join(words[:5])


def key_values(spec) -> str:
    values = spec_values(spec)
    short = {
        "unit_length_m": "len",
        "design_speed_kmh": "speed",
        "length_includes_power_head": "head",
    }
    parts = []
    for path, v in values.items():
        name = short.get(
            path,
            path.split(".")[-1]
            .replace("_clear_width_mm", "")
            .replace("_height_mm", "")
            .replace("wheelchair_door_level_access", "level"),
        )
        parts.append(f"{name} {v:g}")
    parts += [v for v in spec_categories(spec).values()]
    return ", ".join(parts)


def main() -> None:
    specs = HERE / "specs"
    specs.mkdir(exist_ok=True)
    for old in [p for pattern in SUITES.values() for p in specs.glob(pattern)]:
        old.unlink()
    cases = []
    for raw in CASES:
        golden = GoldenCase.model_validate(raw)  # fails loudly on a typo
        cases.append(golden)
        path = specs / f"{golden.id}_{slug(golden.title)}.json"
        path.write_text(
            json.dumps(
                json.loads(golden.model_dump_json(exclude_none=True)), indent=2, ensure_ascii=False
            )
            + "\n",
            encoding="utf-8",
        )
    (HERE / "GOLDEN_SET_REVIEW.md").write_text(review(cases), encoding="utf-8")
    print(f"{len(cases)} cases -> {specs}")


def review(cases: list[GoldenCase]) -> str:
    n_params = sum(len(c.expected) for c in cases)
    verdicts: dict[str, int] = {}
    for c in cases:
        for x in c.expected.values():
            verdicts[x.verdict] = verdicts.get(x.verdict, 0) + 1
    tags: dict[str, list[str]] = {}
    for c in cases:
        for t in c.tags:
            tags.setdefault(t, []).append(c.id)
    out = [
        "# Golden set: review draft",
        "",
        "Written by hand from the text of the PRM TSI (Regulation (EU) No 1300/2014, point 4.2.2 "
        "and 5.3.2): drafted with Claude, reviewed by the repository owner, who confirmed the four "
        "judgment calls below on 2026-10-24. One reviewer only.",
        "",
        f"**{len(cases)} specs, {n_params} scored parameter verdicts:** "
        + ", ".join(f"{n} {v.replace('_', ' ')}" for v, n in sorted(verdicts.items()))
        + ".",
        "",
        "## Assumptions to confirm",
        "",
        "1. **Every unit is new** (placed on the market after 28 Sept 2023, point 7.1.2). Appendix F "
        "exempts parts of several rules at renewal or upgrade (for example 'Compliance with the "
        "requirements of points 4.2.2.11 [steps] ... is not mandatory at renewal or upgrade'). The "
        "spec has no field for new vs renewed, so that is out of scope; it is listed as a limitation.",
        "2. **No 'different document' case.** The other six documents in the corpus (Directive, "
        "CCS, ENE, SRT, NOI, OPE) contain no passage about these parameters (0 matches for "
        "wheelchair, door width, step height, universal toilet). The nearest real traps are a rule "
        "in a *different section* (universal toilet door width is in 5.3.2.4, while 4.2.2.5 only "
        "points to it: tag `other-section`) and near-identical passages in the PRM TSI itself "
        "(Appendix F, national specific cases). If you want a true cross-document trap, a document "
        "that states one of these rules differently would have to be added to the corpus.",
        "3. **Only the listed parameters are scored per spec.** The report always has 7 parameters; "
        "those a spec does not supply are `needs_human` (missing data) by construction, decided in "
        "code without a model call, and are not scored here.",
        "4. **Exemptions that need data the spec lacks are not applied.** 4.2.2.11.2(8) lets some "
        "rolling stock for platforms below 380 mm skip the step rules (2) and (5); the spec has no "
        "platform height, so a step above the limit is a `fail`, not `needs_human`.",
        "",
        "## Judgment calls (confirmed as drafted)",
        "",
        "- **g13** design speed exactly 250 km/h: I expect `pass` (literal reading of 'lower than "
        "250 km/h'). Alternative: `needs_human` because the boundary may be unintended.",
        "- **g03 / g16** internal step in (200, 230] mm: I expect `needs_human` (the exception needs "
        "a demonstration). Alternative: `fail` against the 200 mm default.",
        "- **g19** length including a power head, 2 spaces: I expect `needs_human`. This is a case "
        "the current agent has no special logic for, so it may well fail; it is here on purpose.",
        "- **g10** 300 km/h, wheelchair door 780 mm: I expect `fail` (the general 800 mm rule). In a "
        "first probe the agent said `needs_human` instead; I have not changed the expectation to fit.",
        "",
        "## Limits of this set",
        "",
        "- **Small:** 20 specs, 43 scored verdicts; only 5 expect `needs_human` and 1 `not_applicable`, "
        "so precision and recall for escalation rest on a handful of cases and carry wide error bars.",
        "- **Not independent:** g08 and g09 carry 14 of the 43 verdicts; the verdicts for one "
        "parameter across cases share one rule.",
        "- **One reviewer.** The verdicts are my reading of the regulation, not a notified body's.",
        "- **Selection bias:** g10 and g11 (and the wish for g19) came from weaknesses seen in a first "
        "real run of the agent on three examples, so the set is harder for this agent than a random "
        "set would be. The expectations were not changed to fit what the agent did.",
        "- **Consistency is checked, correctness is not.** A test confirms the typed verdicts agree "
        "with the rules applied by the deterministic `check`, and that every gold quote and passage "
        "id exists in the corpus. It cannot confirm that I read the law right: that is this review.",
        "",
        "## Coverage",
        "",
        "| Trap | Cases |",
        "|---|---|",
    ]
    for t, ids in sorted(tags.items()):
        out.append(f"| `{t}` | {', '.join(ids)} |")
    out += [
        "",
        "## Cases",
        "",
        "| Id | Title | Spec (supplied values) | Expected |",
        "|---|---|---|---|",
    ]
    for c in cases:
        exp = "<br>".join(
            f"`{p.split('.')[-1]}`: **{x.verdict.replace('_', ' ')}**"
            for p, x in c.expected.items()
        )
        out.append(f"| {c.id} | {c.title} | {key_values(c.spec)} | {exp} |")
    out += ["", "## Reasoning per case", ""]
    for c in cases:
        out += [f"### {c.id}: {c.title}", "", f"*{c.why}* Tags: {', '.join(c.tags)}.", ""]
        for p, x in c.expected.items():
            out.append(f"- `{p}` → **{x.verdict.replace('_', ' ')}**. {x.rationale}")
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    main()
