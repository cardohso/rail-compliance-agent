"""Writes eval/heldout2/k*.json, REVIEW.md: held-out set 2, for everything added after v0.1.0.

Written on 2026-10-30 from the text of the PRM TSI (including Appendix F) and the Noise TSI, after
the prm-extended, renewal and noise suites had been written and BEFORE the agent was run on any of
them or on these specs. The first held-out set became a development set when h10 was fixed; this
one is the fresh measurement for the new parameters, renewed units and noise. Same rules as those
suites (new values and combinations, not new rules). Run it once; if a verdict here is later found
wrong, say so next to the result rather than quietly editing.

    uv run python eval/build_heldout2.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from build_golden import (  # noqa: E402
    CAB,
    ESCALATE,
    F_CLEARWAYS,
    F_HEIGHT,
    F_RAILS,
    F_SEATS,
    F_SPACES,
    F_TOILETS,
    HANDS,
    HORN,
    PB80,
    PB250,
    RAIL,
    RENEWED,
    SEAT,
    SPACE_W,
    SPACES,
    STAIR_D,
    STAIR_H,
    STAIRS_TEXT,
    STAT,
    T2,
    T4,
    T5,
    TURN,
    UNIVERSAL,
    case,
    e,
    unit,
)

from rail_compliance.golden import (  # noqa: E402
    P_CAB,
    P_HANDRAILS,
    P_PASS_BY,
    P_PRIORITY,
    P_SPACE_DIMS,
    P_SPACES,
    P_STAIRS,
    P_STATIONARY,
    P_TURNING,
    GoldenCase,
)

OUT = HERE / "heldout2"
T = ["heldout2"]

CASES = [
    case(
        "k01",
        "Handrail and priority seat at the other ends of their ranges",
        [*T, "range", "exact-limit"],
        "40 mm and 430 mm are both included in their ranges.",
        {
            "unit_length_m": 80.0,
            "handrails": {"outside_diameter_mm": 40},
            "priority_seats": {"cushion_height_mm": 430},
        },
        {
            RAIL: e(
                "pass",
                "30–40 mm",
                [P_HANDRAILS],
                "4.2.2.9(1): 40 is the upper bound of '30 mm to 40 mm', included.",
            ),
            SEAT: e(
                "pass",
                "430–500 mm",
                [P_PRIORITY],
                "4.2.2.1.2.1(9): 430 is the lower bound of 'between 430 and 500 mm', included.",
            ),
        },
    ),
    case(
        "k02",
        "Thin handrail and a turning space just short",
        [*T, "range", "thousand-separator"],
        "29.5 mm is below the range; 1 499 mm is 1 mm under the minimum diameter.",
        {
            "unit_length_m": 80.0,
            "handrails": {"outside_diameter_mm": 29.5},
            "wheelchair_space_layout": {"turning_space_diameter_mm": 1499},
        },
        {
            RAIL: e("fail", "30–40 mm", [P_HANDRAILS], "4.2.2.9(1): 29.5 < 30."),
            TURN: e("fail", "≥ 1500 mm", [P_TURNING], "4.2.2.6(3): 1499 < 1500."),
        },
    ),
    case(
        "k03",
        "Double-deck stairs exactly at the relaxed depth",
        [*T, "category", "relaxation", "exact-limit"],
        "270 mm is the permitted minimum on a double deck train; the height rule is unchanged.",
        {
            "unit_length_m": 80.0,
            "deck_layout": "double_deck",
            "stairs": {"step_height_mm": 199, "step_depth_mm": 270},
        },
        {
            STAIR_H: e("pass", "≤ 200 mm", [P_STAIRS], f"{STAIRS_TEXT}: 199 ≤ 200."),
            STAIR_D: e(
                "pass",
                "≥ 270 mm (double deck)",
                [P_STAIRS],
                f"{STAIRS_TEXT}: double deck, 270 ≥ 270.",
            ),
        },
    ),
    case(
        "k04",
        "Wheelchair space between two walls",
        [*T, "conditional"],
        "Both sides are next to an obstacle, so each needs 50 mm of hand clearance.",
        {
            "unit_length_m": 80.0,
            "wheelchair_space_layout": {
                "width_mm": 701,
                "sides_next_to_obstacle": 2,
                "hand_clearance_mm": 49,
            },
        },
        {
            SPACE_W: e("pass", "≥ 700 mm", [P_SPACE_DIMS], "4.2.2.2(3): 701 ≥ 700."),
            HANDS: e(
                "fail",
                "≥ 50 mm (sides next to an obstacle)",
                [P_SPACE_DIMS],
                "4.2.2.2(3): an additional 50 mm on each side next to an obstacle; 49 < 50.",
            ),
        },
    ),
    case(
        "k05",
        "Stair depth 279 mm, deck layout not stated",
        [*T, "category", "relaxation", "missing-data", "needs-human"],
        "279 mm fails 280 and meets 270; only the deck layout decides.",
        {"unit_length_m": 80.0, "stairs": {"step_depth_mm": 279}},
        {
            STAIR_D: e(
                "needs_human",
                "≥ 280 mm, or ≥ 270 mm if double deck",
                [P_STAIRS],
                f"{STAIRS_TEXT}: deck_layout is not supplied.",
                alt=[ESCALATE],
            )
        },
    ),
    case(
        "k06",
        "Renewal with new handrails and old stairs",
        [*T, "renewal", "exemption"],
        "Renewed handrails must comply (31 mm does); 4.2.2.8 is not mandatory at renewal.",
        {
            **RENEWED,
            "renewal": {"handrails_renewed": True},
            "handrails": {"outside_diameter_mm": 31},
            "stairs": {"step_depth_mm": 250},
        },
        {
            RAIL: e(
                "pass",
                "30–40 mm",
                [P_HANDRAILS, F_RAILS],
                "Appendix F, Handrails: renewed, so 4.2.2.9(1) applies; 31 is within 30–40 mm.",
            ),
            STAIR_D: e(
                "not_applicable",
                None,
                [F_HEIGHT],
                "Appendix F, Height Changes: 'Compliance with the requirements of point 4.2.2.8 is not mandatory at renewal or upgrade.'",
            ),
        },
    ),
    case(
        "k07",
        "Renewal that re-lays the whole train but keeps its toilet",
        [*T, "renewal", "exemption", "length-dependent"],
        "Spaces are required (layout altered in the whole train): 3 at 210 m. The toilet is not completely renewed.",
        {
            "unit_length_m": 210.0,
            "unit_status": "renewed",
            "renewal": {
                "seating_layout_altered_in_entire_train": True,
                "seating_layout_altered_in_entire_vehicle": True,
                "toilets_completely_renewed": False,
            },
            "wheelchair_spaces": 3,
            "toilets": {"fitted": 1, "universal": 0},
        },
        {
            SPACES: e(
                "pass",
                "≥ 3 (205 to 300 m row)",
                [P_SPACES, F_SPACES],
                "Appendix F: the layout is altered within the complete train, so Table 5 applies; 210 m needs 3; 3 ≥ 3.",
            ),
            UNIVERSAL: e(
                "not_applicable",
                None,
                [F_TOILETS],
                "Appendix F, Toilets: 'only mandatory when existing toilets are being completely renewed or upgraded'; they are not.",
            ),
        },
    ),
    case(
        "k08",
        "Renewal that leaves every vehicle's layout alone",
        [*T, "renewal", "exemption"],
        "4.2.2.6 is only mandatory if the layout is altered within an entire vehicle.",
        {
            **RENEWED,
            "renewal": {"seating_layout_altered_in_entire_vehicle": False},
            "wheelchair_space_layout": {"turning_space_diameter_mm": 1200},
        },
        {
            TURN: e(
                "not_applicable",
                None,
                [F_CLEARWAYS],
                "Appendix F, Clearways: 'only mandatory if the seating layout is altered within an entire vehicle'; it is not.",
            )
        },
    ),
    case(
        "k09",
        "Renewal that re-lays the train with high priority seats",
        [*T, "renewal", "exemption", "needs-human"],
        "Priority-seat dimensions are mandatory only if achievable without reducing capacity, which the spec cannot show.",
        {
            **RENEWED,
            "renewal": {
                "seating_layout_altered_in_entire_train": True,
                "seating_layout_altered_in_entire_vehicle": True,
            },
            "priority_seats": {"cushion_height_mm": 520},
        },
        {
            SEAT: e(
                "needs_human",
                "430–500 mm, unless it would reduce capacity",
                [P_PRIORITY, F_SEATS],
                "4.2.2.1.2.1(9): 520 > 500. Appendix F, Seats: 'only mandatory if the seating layout is altered within an entire train and this can be achieved without reducing the existing capacity of the train'. A person must judge capacity.",
                alt=[ESCALATE],
            )
        },
    ),
    case(
        "k10",
        "DMU at 250 km/h",
        [*T, "noise", "category-table", "exact-limit"],
        "At exactly 250 km/h the 250 km/h pass-by limit applies; the DMU stationary row is 72.",
        unit("dmu", speed=250, stationary_db=73, pass_by_250_db=96),
        {
            STAT: e("fail", "≤ 72 dB (DMUs)", [P_STATIONARY], f"{T2}: DMU row, 73 > 72."),
            PB250: e(
                "pass",
                "≤ 96 dB (DMUs, 250 km/h)",
                [P_PASS_BY],
                f"{T4}: design speed 250 ≥ 250, DMU row, 96 ≤ 96.",
            ),
        },
    ),
    case(
        "k11",
        "Diesel locomotive",
        [*T, "noise", "category-table"],
        "The diesel locomotive rows: 71 dB stationary, 85 dB at 80 km/h.",
        unit("diesel_locomotive", stationary_db=71, pass_by_80_db=86),
        {
            STAT: e("pass", "≤ 71 dB (diesel locomotives)", [P_STATIONARY], f"{T2}: 71 ≤ 71."),
            PB80: e("fail", "≤ 85 dB (diesel locomotives)", [P_PASS_BY], f"{T4}: 86 > 85."),
        },
    ),
    case(
        "k12",
        "EMU just below 250 km/h",
        [*T, "noise", "table-boundary"],
        "249 km/h: the cab row is the one below 250 km/h, and the 250 km/h pass-by does not apply.",
        unit("emu", speed=249, cab=True, cab_max_speed_db=78, pass_by_250_db=99),
        {
            CAB: e(
                "pass", "≤ 78 dB (vmax < 250 km/h)", [P_CAB], f"{T5}: 249 < 250, so 78 dB; 78 ≤ 78."
            ),
            PB250: e(
                "not_applicable",
                None,
                [P_PASS_BY],
                f"{T4}: design speed 249 < 250, so the 250 km/h limit does not apply.",
            ),
        },
    ),
    case(
        "k13",
        "Loud horn, cab not stated",
        [*T, "noise", "missing-data", "needs-human"],
        "98 dB fails the cab limit if the unit has a cab, and the spec does not say.",
        unit("coach", cab_standstill_horn_db=98),
        {
            HORN: e(
                "needs_human",
                "≤ 95 dB, for a unit fitted with a cab",
                [P_CAB],
                f"{T5}: has_drivers_cab is not supplied and 98 > 95.",
                alt=[ESCALATE],
            )
        },
    ),
]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("k*.json"):
        old.unlink()
    cases = []
    for raw in CASES:
        golden = GoldenCase.model_validate(raw)
        cases.append(golden)
        words = re.sub(r"[^a-z0-9]+", " ", golden.title.lower()).split()[:5]
        text = json.dumps(
            json.loads(golden.model_dump_json(exclude_none=True)), indent=2, ensure_ascii=False
        )
        (OUT / f"{golden.id}_{'_'.join(words)}.json").write_text(text + "\n", encoding="utf-8")
    (OUT / "REVIEW.md").write_text(review(cases), encoding="utf-8")
    print(f"{len(cases)} held-out cases -> {OUT}")


def review(cases: list[GoldenCase]) -> str:
    n = sum(len(c.expected) for c in cases)
    lines = [
        "# Held-out set 2: verdicts written before any run",
        "",
        "Written on 2026-10-30 for the parameters, renewal rules and noise limits added after "
        "v0.1.0, **before the agent was run on these specs or on the suites they mirror**. "
        f"{len(cases)} specs, {n} scored verdicts.",
        "",
        "| Case | Title | Parameter | Expected | Rule |",
        "|---|---|---|---|---|",
    ]
    for c in cases:
        for p, x in c.expected.items():
            lines.append(f"| {c.id} | {c.title} | `{p}` | {x.verdict} | {x.required or '—'} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
