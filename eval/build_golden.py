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
    P_DOORS,
    P_SPACES,
    P_STEPS,
    P_TOILET,
    P_UNIVERSAL,
    GoldenCase,
)
from rail_compliance.spec import spec_values

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
    return ", ".join(parts)


def main() -> None:
    specs = HERE / "specs"
    specs.mkdir(exist_ok=True)
    for old in specs.glob("g*.json"):
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
        "and 5.3.2) by one reviewer (the author, with Claude drafting). **Not yet reviewed by "
        "anyone else, and not yet used by any evaluation.**",
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
        "## Judgment calls: please decide",
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
