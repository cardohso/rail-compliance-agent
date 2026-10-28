"""Writes eval/heldout/h*.json and eval/heldout/REVIEW.md: a HELD-OUT set.

Written on 2026-10-24 from the text of the PRM TSI, after the dev set (eval/specs) had been used to
design the fixes, and BEFORE the agent was run on any of these specs. Same rules as the dev set (the
corpus has no others for the spec's parameters), so this tests new values and combinations, not new
rules. Run it once; if a verdict here is later found wrong, say so next to the result rather than
quietly editing.

    uv run python eval/build_heldout.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from build_golden import (  # noqa: E402
    DOORS,
    ESCALATE,
    EXT,
    INT,
    RULE,
    SPACES,
    TABLE_ROWS,
    UNI_DOOR,
    UNIVERSAL,
    WC_DOOR,
    case,
    e,
    key_values,
)

from rail_compliance.golden import (  # noqa: E402
    P_DOORS,
    P_SPACES,
    P_STEPS,
    P_TOILET,
    P_UNIVERSAL,
    GoldenCase,
)

CASES = [
    case(
        "h01",
        "400 m high-speed unit, compliant",
        ["heldout", "baseline", "high-speed", "length-dependent"],
        "A 400 m unit sits in the top table row, and at 320 km/h only the 800 mm door rule applies.",
        {
            "unit_length_m": 400.0,
            "length_includes_power_head": False,
            "design_speed_kmh": 320,
            "wheelchair_spaces": 4,
            "exterior_doors": {
                "clear_width_mm": 850,
                "wheelchair_door_clear_width_mm": 850,
                "wheelchair_door_level_access": True,
            },
            "steps": {"external_step_height_mm": 220, "internal_step_height_mm": 190},
            "toilets": {"fitted": 4, "universal": 2, "universal_door_clear_width_mm": 900},
        },
        {
            SPACES: e(
                "pass",
                "≥ 4 (over 300 m row)",
                [P_SPACES],
                f"{TABLE_ROWS}: 400 m is 'More than 300 metres' (4 spaces); 4 ≥ 4.",
            ),
            DOORS: e("pass", "≥ 800 mm", [P_DOORS], "4.2.2.3.2(1): 850 ≥ 800."),
            WC_DOOR: e(
                "pass",
                "≥ 800 mm (the 1000 mm rule needs a speed below 250)",
                [P_DOORS],
                "4.2.2.3.2(2) is for 'lower than 250 km/h'; at 320 km/h only (1) applies: 850 ≥ 800.",
            ),
            EXT: e("pass", "≤ 230 mm", [P_STEPS], "4.2.2.11.2(5): 220 ≤ 230."),
            INT: e("pass", "≤ 200 mm", [P_STEPS], "4.2.2.11.2(2): 190 ≤ 200."),
            UNIVERSAL: e(
                "pass",
                "≥ 1 when toilets are fitted",
                [P_TOILET],
                "4.2.2.5(1): 4 toilets fitted, 2 universal.",
            ),
            UNI_DOOR: e("pass", "≥ 800 mm", [P_UNIVERSAL], "5.3.2.4(3): 900 ≥ 800."),
        },
    ),
    case(
        "h02",
        "250 m unit with two spaces and no universal toilet",
        ["heldout", "violation", "length-dependent"],
        "250 m is in the 3-space row, and toilets are fitted but none is universal.",
        {
            "unit_length_m": 250.0,
            "length_includes_power_head": False,
            "wheelchair_spaces": 2,
            "toilets": {"fitted": 3, "universal": 0},
        },
        {
            SPACES: e(
                "fail",
                "≥ 3 (205 to 300 m row)",
                [P_SPACES],
                f"{TABLE_ROWS}: 250 m is 'More than 205 to 300 metres' (3 spaces); 2 < 3.",
            ),
            UNIVERSAL: e(
                "fail",
                "≥ 1 when toilets are fitted",
                [P_TOILET],
                "4.2.2.5(1): 3 toilets are fitted and none is universal.",
            ),
        },
    ),
    case(
        "h03",
        "Wheelchair door 990 mm at 249.9 km/h",
        ["heldout", "conditional-rule", "exact-limit"],
        "Just below 250 km/h the 1000 mm rule applies, and 990 mm misses it.",
        {
            "unit_length_m": 100.0,
            "design_speed_kmh": 249.9,
            "exterior_doors": {
                "wheelchair_door_clear_width_mm": 990,
                "wheelchair_door_level_access": True,
            },
        },
        {
            WC_DOOR: e(
                "fail",
                "≥ 1000 mm",
                [P_DOORS],
                "4.2.2.3.2(2) applies (249.9 < 250 km/h, level access): 990 < 1000.",
            )
        },
    ),
    case(
        "h04",
        "Wheelchair door 990 mm at 250.1 km/h",
        ["heldout", "conditional-rule", "exact-limit"],
        "Just above 250 km/h the 1000 mm rule no longer applies, so 990 mm meets the 800 mm rule.",
        {
            "unit_length_m": 100.0,
            "design_speed_kmh": 250.1,
            "exterior_doors": {
                "wheelchair_door_clear_width_mm": 990,
                "wheelchair_door_level_access": True,
            },
        },
        {
            WC_DOOR: e(
                "pass",
                "≥ 800 mm (the 1000 mm rule needs a speed below 250)",
                [P_DOORS],
                "4.2.2.3.2(2) does not apply at 250.1 km/h; 4.2.2.3.2(1): 990 ≥ 800.",
            )
        },
    ),
    case(
        "h05",
        "320 m including a power head, three spaces",
        ["heldout", "needs-human", "length-dependent", "ambiguous-data"],
        "Up to 320 m the requirement could be 1, 2, 3 or 4 spaces depending on the length without the power head.",
        {"unit_length_m": 320.0, "length_includes_power_head": True, "wheelchair_spaces": 3},
        {
            SPACES: e(
                "needs_human",
                "≥ 3 or ≥ 4 depending on the length without the power head",
                [P_SPACES],
                "4.2.2.2(1) excludes the power head. The true length is at most 320 m: above 300 m it needs 4 spaces, up to 300 m at most 3. 3 meets some of these and not others.",
                ESCALATE,
                alt=[RULE],
            )
        },
    ),
    case(
        "h06",
        "28 m including a power head, one space",
        ["heldout", "length-dependent", "ambiguous-data"],
        "Even if the whole length counts, 28 m is in the 1-space row, so the answer is safe.",
        {"unit_length_m": 28.0, "length_includes_power_head": True, "wheelchair_spaces": 1},
        {
            SPACES: e(
                "pass",
                "≥ 1 (under 30 m row)",
                [P_SPACES],
                f"{TABLE_ROWS}: the true length is at most 28 m, which needs 1 space whatever the power head's length; 1 ≥ 1.",
            )
        },
    ),
    case(
        "h07",
        "25 m unit with no wheelchair space",
        ["heldout", "violation", "length-dependent"],
        "Every unit needs at least one wheelchair space.",
        {"unit_length_m": 25.0, "length_includes_power_head": False, "wheelchair_spaces": 0},
        {
            SPACES: e(
                "fail",
                "≥ 1 (under 30 m row)",
                [P_SPACES],
                f"{TABLE_ROWS}: 'Less than 30 m' needs 1 space; 0 < 1.",
            )
        },
    ),
    case(
        "h08",
        "Both steps at 229.9 mm",
        ["heldout", "needs-human", "exception", "exact-limit"],
        "229.9 mm meets the external step limit but exceeds the internal default, within the exception band.",
        {
            "unit_length_m": 100.0,
            "steps": {"external_step_height_mm": 229.9, "internal_step_height_mm": 229.9},
        },
        {
            EXT: e("pass", "≤ 230 mm", [P_STEPS], "4.2.2.11.2(5): 229.9 ≤ 230."),
            INT: e(
                "needs_human",
                "≤ 200 mm, or ≤ 230 mm if it reduces the number of steps",
                [P_STEPS],
                "4.2.2.11.2(2): 229.9 exceeds 200 but not 230; allowed only if a reduction of one step is demonstrated, which the spec cannot show.",
                ESCALATE,
                alt=[RULE],
            ),
        },
    ),
    case(
        "h09",
        "Universal toilet door 799.5 mm with two universal toilets",
        ["heldout", "other-section", "exact-limit"],
        "The count is fine; the door width, stated in a different section (5.3.2.4), misses by 0.5 mm.",
        {
            "unit_length_m": 100.0,
            "toilets": {"fitted": 3, "universal": 2, "universal_door_clear_width_mm": 799.5},
        },
        {
            UNIVERSAL: e(
                "pass",
                "≥ 1 when toilets are fitted",
                [P_TOILET],
                "4.2.2.5(1): 3 toilets fitted, 2 universal.",
            ),
            UNI_DOOR: e("fail", "≥ 800 mm", [P_UNIVERSAL], "5.3.2.4(3): 799.5 < 800."),
        },
    ),
    case(
        "h10",
        "Wheelchair door exactly 1000 mm, design speed not given",
        ["heldout", "known-limit", "judgment-call", "missing-data"],
        "Whether the 1000 mm rule applies is unknown, but the door meets it either way. KNOWN LIMIT: the agent's check treats an unknown condition as needs_human.",
        {
            "unit_length_m": 100.0,
            "exterior_doors": {
                "wheelchair_door_clear_width_mm": 1000,
                "wheelchair_door_level_access": True,
            },
        },
        {
            WC_DOOR: e(
                "pass",
                "≥ 1000 mm if design speed < 250 km/h, else ≥ 800 mm; 1000 mm meets both",
                [P_DOORS],
                "If the speed is below 250 km/h, 4.2.2.3.2(2) applies and 1000 ≥ 1000; otherwise only (1) applies and 1000 ≥ 800. The outcome does not depend on the missing speed. Expected to be missed: `check` returns needs_human whenever a condition is unknown, even when both branches pass. A person would call it a pass; the tool is more cautious.",
            )
        },
    ),
]

# h10 was written as a known limit; the limit has since been fixed, so the oracle agrees everywhere.
# The case text is left as written: it is the record of what was predicted before the run.
KNOWN_ORACLE_DISAGREEMENTS: set = set()


def main() -> None:
    out = HERE / "heldout"
    out.mkdir(exist_ok=True)
    for old in out.glob("h*.json"):
        old.unlink()
    cases = []
    for raw in CASES:
        golden = GoldenCase.model_validate(raw)
        cases.append(golden)
        words = re.sub(r"[^a-z0-9]+", " ", golden.title.lower()).split()[:5]
        path = out / f"{golden.id}_{'_'.join(words)}.json"
        text = json.dumps(
            json.loads(golden.model_dump_json(exclude_none=True)), indent=2, ensure_ascii=False
        )
        path.write_text(text + "\n", encoding="utf-8")
    (out / "REVIEW.md").write_text(review(cases), encoding="utf-8")
    print(f"{len(cases)} held-out cases -> {out}")


def review(cases: list[GoldenCase]) -> str:
    n = sum(len(c.expected) for c in cases)
    counts: dict[str, int] = {}
    for c in cases:
        for x in c.expected.values():
            counts[x.verdict] = counts.get(x.verdict, 0) + 1
    lines = [
        "# Held-out set: verdicts written before the first run",
        "",
        "Written from the text of the PRM TSI after the dev set (`eval/specs`) had been used to design "
        "the fixes, and **before the agent was run on any of these specs**. Same 7 rules as the dev "
        "set: this tests new values and combinations, not new rules (the corpus has no others for "
        "the spec's parameters). One reviewer; run once.",
        "",
        f"**{len(cases)} specs, {n} scored verdicts:** "
        + ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in sorted(counts.items()))
        + ".",
        "",
        "| Id | Title | Spec (supplied values) | Expected |",
        "|---|---|---|---|",
    ]
    for c in cases:
        exp = "<br>".join(
            f"`{p.split('.')[-1]}`: **{x.verdict.replace('_', ' ')}**"
            for p, x in c.expected.items()
        )
        lines.append(f"| {c.id} | {c.title} | {key_values(c.spec)} | {exp} |")
    lines += ["", "## Reasoning", ""]
    for c in cases:
        lines += [f"### {c.id}: {c.title}", "", f"*{c.why}* Tags: {', '.join(c.tags)}.", ""]
        lines += [
            f"- `{p}` → **{x.verdict.replace('_', ' ')}**. {x.rationale}"
            for p, x in c.expected.items()
        ]
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
