# Held-out set: verdicts written before the first run

Written from the text of the PRM TSI after the dev set (`eval/specs`) had been used to design the fixes, and **before the agent was run on any of these specs**. Same 7 rules as the dev set: this tests new values and combinations, not new rules (the corpus has no others for the spec's parameters). One reviewer; run once.

**10 specs, 19 scored verdicts:** 5 fail, 2 needs human, 12 pass.

| Id | Title | Spec (supplied values) | Expected |
|---|---|---|---|
| h01 | 400 m high-speed unit, compliant | len 400, head 0, speed 320, wheelchair_spaces 4, clear_width_mm 850, wheelchair_door 850, level 1, external_step 220, internal_step 190, fitted 4, universal 2, universal_door 900 | `wheelchair_spaces`: **pass**<br>`clear_width_mm`: **pass**<br>`wheelchair_door_clear_width_mm`: **pass**<br>`external_step_height_mm`: **pass**<br>`internal_step_height_mm`: **pass**<br>`universal`: **pass**<br>`universal_door_clear_width_mm`: **pass** |
| h02 | 250 m unit with two spaces and no universal toilet | len 250, head 0, wheelchair_spaces 2, fitted 3, universal 0 | `wheelchair_spaces`: **fail**<br>`universal`: **fail** |
| h03 | Wheelchair door 990 mm at 249.9 km/h | len 100, speed 249.9, wheelchair_door 990, level 1 | `wheelchair_door_clear_width_mm`: **fail** |
| h04 | Wheelchair door 990 mm at 250.1 km/h | len 100, speed 250.1, wheelchair_door 990, level 1 | `wheelchair_door_clear_width_mm`: **pass** |
| h05 | 320 m including a power head, three spaces | len 320, head 1, wheelchair_spaces 3 | `wheelchair_spaces`: **needs human** |
| h06 | 28 m including a power head, one space | len 28, head 1, wheelchair_spaces 1 | `wheelchair_spaces`: **pass** |
| h07 | 25 m unit with no wheelchair space | len 25, head 0, wheelchair_spaces 0 | `wheelchair_spaces`: **fail** |
| h08 | Both steps at 229.9 mm | len 100, external_step 229.9, internal_step 229.9 | `external_step_height_mm`: **pass**<br>`internal_step_height_mm`: **needs human** |
| h09 | Universal toilet door 799.5 mm with two universal toilets | len 100, fitted 3, universal 2, universal_door 799.5 | `universal`: **pass**<br>`universal_door_clear_width_mm`: **fail** |
| h10 | Wheelchair door exactly 1000 mm, design speed not given | len 100, wheelchair_door 1000, level 1 | `wheelchair_door_clear_width_mm`: **pass** |

## Reasoning

### h01: 400 m high-speed unit, compliant

*A 400 m unit sits in the top table row, and at 320 km/h only the 800 mm door rule applies.* Tags: heldout, baseline, high-speed, length-dependent.

- `wheelchair_spaces` → **pass**. Table 5 of point 4.2.2.2(1): 400 m is 'More than 300 metres' (4 spaces); 4 ≥ 4.
- `exterior_doors.clear_width_mm` → **pass**. 4.2.2.3.2(1): 850 ≥ 800.
- `exterior_doors.wheelchair_door_clear_width_mm` → **pass**. 4.2.2.3.2(2) is for 'lower than 250 km/h'; at 320 km/h only (1) applies: 850 ≥ 800.
- `steps.external_step_height_mm` → **pass**. 4.2.2.11.2(5): 220 ≤ 230.
- `steps.internal_step_height_mm` → **pass**. 4.2.2.11.2(2): 190 ≤ 200.
- `toilets.universal` → **pass**. 4.2.2.5(1): 4 toilets fitted, 2 universal.
- `toilets.universal_door_clear_width_mm` → **pass**. 5.3.2.4(3): 900 ≥ 800.

### h02: 250 m unit with two spaces and no universal toilet

*250 m is in the 3-space row, and toilets are fitted but none is universal.* Tags: heldout, violation, length-dependent.

- `wheelchair_spaces` → **fail**. Table 5 of point 4.2.2.2(1): 250 m is 'More than 205 to 300 metres' (3 spaces); 2 < 3.
- `toilets.universal` → **fail**. 4.2.2.5(1): 3 toilets are fitted and none is universal.

### h03: Wheelchair door 990 mm at 249.9 km/h

*Just below 250 km/h the 1000 mm rule applies, and 990 mm misses it.* Tags: heldout, conditional-rule, exact-limit.

- `exterior_doors.wheelchair_door_clear_width_mm` → **fail**. 4.2.2.3.2(2) applies (249.9 < 250 km/h, level access): 990 < 1000.

### h04: Wheelchair door 990 mm at 250.1 km/h

*Just above 250 km/h the 1000 mm rule no longer applies, so 990 mm meets the 800 mm rule.* Tags: heldout, conditional-rule, exact-limit.

- `exterior_doors.wheelchair_door_clear_width_mm` → **pass**. 4.2.2.3.2(2) does not apply at 250.1 km/h; 4.2.2.3.2(1): 990 ≥ 800.

### h05: 320 m including a power head, three spaces

*Up to 320 m the requirement could be 1, 2, 3 or 4 spaces depending on the length without the power head.* Tags: heldout, needs-human, length-dependent, ambiguous-data.

- `wheelchair_spaces` → **needs human**. 4.2.2.2(1) excludes the power head. The true length is at most 320 m: above 300 m it needs 4 spaces, up to 300 m at most 3. 3 meets some of these and not others.

### h06: 28 m including a power head, one space

*Even if the whole length counts, 28 m is in the 1-space row, so the answer is safe.* Tags: heldout, length-dependent, ambiguous-data.

- `wheelchair_spaces` → **pass**. Table 5 of point 4.2.2.2(1): the true length is at most 28 m, which needs 1 space whatever the power head's length; 1 ≥ 1.

### h07: 25 m unit with no wheelchair space

*Every unit needs at least one wheelchair space.* Tags: heldout, violation, length-dependent.

- `wheelchair_spaces` → **fail**. Table 5 of point 4.2.2.2(1): 'Less than 30 m' needs 1 space; 0 < 1.

### h08: Both steps at 229.9 mm

*229.9 mm meets the external step limit but exceeds the internal default, within the exception band.* Tags: heldout, needs-human, exception, exact-limit.

- `steps.external_step_height_mm` → **pass**. 4.2.2.11.2(5): 229.9 ≤ 230.
- `steps.internal_step_height_mm` → **needs human**. 4.2.2.11.2(2): 229.9 exceeds 200 but not 230; allowed only if a reduction of one step is demonstrated, which the spec cannot show.

### h09: Universal toilet door 799.5 mm with two universal toilets

*The count is fine; the door width, stated in a different section (5.3.2.4), misses by 0.5 mm.* Tags: heldout, other-section, exact-limit.

- `toilets.universal` → **pass**. 4.2.2.5(1): 3 toilets fitted, 2 universal.
- `toilets.universal_door_clear_width_mm` → **fail**. 5.3.2.4(3): 799.5 < 800.

### h10: Wheelchair door exactly 1000 mm, design speed not given

*Whether the 1000 mm rule applies is unknown, but the door meets it either way. KNOWN LIMIT: the agent's check treats an unknown condition as needs_human.* Tags: heldout, known-limit, judgment-call, missing-data.

- `exterior_doors.wheelchair_door_clear_width_mm` → **pass**. If the speed is below 250 km/h, 4.2.2.3.2(2) applies and 1000 ≥ 1000; otherwise only (1) applies and 1000 ≥ 800. The outcome does not depend on the missing speed. Expected to be missed: `check` returns needs_human whenever a condition is unknown, even when both branches pass. A person would call it a pass; the tool is more cautious.
