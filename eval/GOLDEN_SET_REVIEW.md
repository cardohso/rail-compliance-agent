# Golden set: review draft

Written by hand from the text of the PRM TSI (Regulation (EU) No 1300/2014, point 4.2.2 and 5.3.2): drafted with Claude, reviewed by the repository owner, who confirmed the four judgment calls below on 2026-10-24. One reviewer only.

**42 specs, 71 scored parameter verdicts:** 25 fail, 10 needs human, 7 not applicable, 29 pass.

## Assumptions to confirm

1. **Every unit is new** (placed on the market after 28 Sept 2023, point 7.1.2). Appendix F exempts parts of several rules at renewal or upgrade (for example 'Compliance with the requirements of points 4.2.2.11 [steps] ... is not mandatory at renewal or upgrade'). The spec has no field for new vs renewed, so that is out of scope; it is listed as a limitation.
2. **No 'different document' case.** The other six documents in the corpus (Directive, CCS, ENE, SRT, NOI, OPE) contain no passage about these parameters (0 matches for wheelchair, door width, step height, universal toilet). The nearest real traps are a rule in a *different section* (universal toilet door width is in 5.3.2.4, while 4.2.2.5 only points to it: tag `other-section`) and near-identical passages in the PRM TSI itself (Appendix F, national specific cases). If you want a true cross-document trap, a document that states one of these rules differently would have to be added to the corpus.
3. **Only the listed parameters are scored per spec.** The report always has 7 parameters; those a spec does not supply are `needs_human` (missing data) by construction, decided in code without a model call, and are not scored here.
4. **Exemptions that need data the spec lacks are not applied.** 4.2.2.11.2(8) lets some rolling stock for platforms below 380 mm skip the step rules (2) and (5); the spec has no platform height, so a step above the limit is a `fail`, not `needs_human`.

## Judgment calls (confirmed as drafted)

- **g13** design speed exactly 250 km/h: I expect `pass` (literal reading of 'lower than 250 km/h'). Alternative: `needs_human` because the boundary may be unintended.
- **g03 / g16** internal step in (200, 230] mm: I expect `needs_human` (the exception needs a demonstration). Alternative: `fail` against the 200 mm default.
- **g19** length including a power head, 2 spaces: I expect `needs_human`. This is a case the current agent has no special logic for, so it may well fail; it is here on purpose.
- **g10** 300 km/h, wheelchair door 780 mm: I expect `fail` (the general 800 mm rule). In a first probe the agent said `needs_human` instead; I have not changed the expectation to fit.

## Limits of this set

- **Small:** 20 specs, 43 scored verdicts; only 5 expect `needs_human` and 1 `not_applicable`, so precision and recall for escalation rest on a handful of cases and carry wide error bars.
- **Not independent:** g08 and g09 carry 14 of the 43 verdicts; the verdicts for one parameter across cases share one rule.
- **One reviewer.** The verdicts are my reading of the regulation, not a notified body's.
- **Selection bias:** g10 and g11 (and the wish for g19) came from weaknesses seen in a first real run of the agent on three examples, so the set is harder for this agent than a random set would be. The expectations were not changed to fit what the agent did.
- **Consistency is checked, correctness is not.** A test confirms the typed verdicts agree with the rules applied by the deterministic `check`, and that every gold quote and passage id exists in the corpus. It cannot confirm that I read the law right: that is this review.

## Coverage

| Trap | Cases |
|---|---|
| `ambiguous-data` | g19, g20 |
| `baseline` | g01 |
| `category` | p09, p10, p11, p12 |
| `conditional` | p06, p07, p08 |
| `conditional-rule` | g10, g11, g12, g13, g14, g15 |
| `exact-limit` | g03, g04, g05, g06, g07, g08, g09, g13, p01, p02, p04, p06, p09 |
| `exception` | g03, g16 |
| `exemption` | r01, r02, r03, r04, r05, r06, r07, r08, r09, r10 |
| `high-speed` | g10, g11 |
| `judgment-call` | g13 |
| `length-dependent` | g02, g04, g05, g06, g07, g08, g09, g19, g20, r06 |
| `missing-data` | g14, g15, p07, p11, r03, r04 |
| `needs-human` | g03, g14, g15, g16, g19, p07, p11, r03, r07, r10 |
| `not-applicable` | g17, p08 |
| `other-section` | g08, g09 |
| `range` | p01, p02, p03 |
| `relaxation` | p10, p11, p12 |
| `renewal` | r01, r02, r03, r04, r05, r06, r07, r08, r09, r10 |
| `table-boundary` | g04, g05, g06, g07 |
| `thousand-separator` | p05 |
| `violation` | g02, g09, g18 |

## Cases

| Id | Title | Spec (supplied values) | Expected |
|---|---|---|---|
| g01 | Compliant regional EMU | len 105, head 0, speed 160, wheelchair_spaces 2, clear_width_mm 850, wheelchair_door 1100, level 1, external_step 200, internal_step 180, fitted 2, universal 1, universal_door 900, new | `wheelchair_spaces`: **pass**<br>`clear_width_mm`: **pass**<br>`wheelchair_door_clear_width_mm`: **pass**<br>`external_step_height_mm`: **pass**<br>`internal_step_height_mm`: **pass**<br>`universal`: **pass**<br>`universal_door_clear_width_mm`: **pass** |
| g02 | Regional train violating six rules | len 150, head 0, speed 160, wheelchair_spaces 1, clear_width_mm 760, wheelchair_door 950, level 1, external_step 260, internal_step 240, fitted 3, universal 0, new | `wheelchair_spaces`: **fail**<br>`clear_width_mm`: **fail**<br>`wheelchair_door_clear_width_mm`: **fail**<br>`external_step_height_mm`: **fail**<br>`internal_step_height_mm`: **fail**<br>`universal`: **fail** |
| g03 | Internal step exactly at the exception limit | len 100, internal_step 230, new | `internal_step_height_mm`: **needs human** |
| g04 | Length exactly 30 m with one wheelchair space | len 30, wheelchair_spaces 1, new | `wheelchair_spaces`: **fail** |
| g05 | Length exactly 205 m with two wheelchair spaces | len 205, wheelchair_spaces 2, new | `wheelchair_spaces`: **pass** |
| g06 | Length exactly 300 m with three wheelchair spaces | len 300, wheelchair_spaces 3, new | `wheelchair_spaces`: **pass** |
| g07 | Length 300.1 m with three wheelchair spaces | len 300.1, wheelchair_spaces 3, new | `wheelchair_spaces`: **fail** |
| g08 | Every value exactly at its limit | len 30, head 0, speed 160, wheelchair_spaces 2, clear_width_mm 800, wheelchair_door 1000, level 1, external_step 230, internal_step 200, fitted 1, universal 1, universal_door 800, new | `wheelchair_spaces`: **pass**<br>`clear_width_mm`: **pass**<br>`wheelchair_door_clear_width_mm`: **pass**<br>`external_step_height_mm`: **pass**<br>`internal_step_height_mm`: **pass**<br>`universal`: **pass**<br>`universal_door_clear_width_mm`: **pass** |
| g09 | Every value just past its limit | len 205.1, head 0, speed 160, wheelchair_spaces 2, clear_width_mm 799.9, wheelchair_door 999.9, level 1, external_step 230.1, internal_step 230.1, fitted 1, universal 1, universal_door 799.9, new | `wheelchair_spaces`: **fail**<br>`clear_width_mm`: **fail**<br>`wheelchair_door_clear_width_mm`: **fail**<br>`external_step_height_mm`: **fail**<br>`internal_step_height_mm`: **fail**<br>`universal`: **pass**<br>`universal_door_clear_width_mm`: **fail** |
| g10 | 300 km/h train, wheelchair door 780 mm | len 200, speed 300, wheelchair_door 780, level 1, new | `wheelchair_door_clear_width_mm`: **fail** |
| g11 | 300 km/h train, wheelchair door 900 mm | len 200, speed 300, wheelchair_door 900, level 1, new | `wheelchair_door_clear_width_mm`: **pass** |
| g12 | 160 km/h train, wheelchair door 900 mm without level access | len 100, speed 160, wheelchair_door 900, level 0, new | `wheelchair_door_clear_width_mm`: **pass** |
| g13 | Design speed exactly 250 km/h | len 100, speed 250, wheelchair_door 900, level 1, new | `wheelchair_door_clear_width_mm`: **pass** |
| g14 | Wheelchair door rule needs a design speed the spec omits | len 100, wheelchair_door 900, level 1, new | `wheelchair_door_clear_width_mm`: **needs human** |
| g15 | Wheelchair door rule needs level-access data the spec omits | len 100, speed 160, wheelchair_door 900, new | `wheelchair_door_clear_width_mm`: **needs human** |
| g16 | Internal step of 215 mm | len 100, internal_step 215, new | `internal_step_height_mm`: **needs human** |
| g17 | Train with no toilets | len 100, fitted 0, universal 0, new | `universal`: **not applicable** |
| g18 | Toilets fitted but none universal | len 100, fitted 2, universal 0, new | `universal`: **fail** |
| g19 | Length includes a power head, two wheelchair spaces | len 210, head 1, wheelchair_spaces 2, new | `wheelchair_spaces`: **needs human** |
| g20 | Length includes a power head, three wheelchair spaces | len 210, head 1, wheelchair_spaces 3, new | `wheelchair_spaces`: **pass** |
| p01 | Handrail diameter at the bottom of the range | len 100, outside_diameter_mm 30, new | `outside_diameter_mm`: **pass** |
| p02 | Handrail too thick, priority seat at the top of the range | len 100, outside_diameter_mm 41, cushion 500, new | `outside_diameter_mm`: **fail**<br>`cushion_height_mm`: **pass** |
| p03 | Priority seat too low | len 100, cushion 425, new | `cushion_height_mm`: **fail** |
| p04 | Wheelchair space and turning space exactly at the minimum | len 100, width_mm 700, turning_space_diameter_mm 1500, new | `width_mm`: **pass**<br>`turning_space_diameter_mm`: **pass** |
| p05 | Wheelchair space and turning space too small | len 100, width_mm 690, turning_space_diameter_mm 1450, new | `width_mm`: **fail**<br>`turning_space_diameter_mm`: **fail** |
| p06 | Hand clearance on a side next to a wall | len 100, sides_next_to_obstacle 1, hand_clearance_mm 50, new | `hand_clearance_mm`: **pass** |
| p07 | Too little hand clearance, sides not stated | len 100, hand_clearance_mm 40, new | `hand_clearance_mm`: **needs human** |
| p08 | Wheelchair space open on both sides | len 100, sides_next_to_obstacle 0, hand_clearance_mm 20, new | `hand_clearance_mm`: **not applicable** |
| p09 | Single-deck stairs: height at the limit, depth too short | len 100, step 200, step_depth_mm 275, single_deck, new | `step_height_mm`: **pass**<br>`step_depth_mm`: **fail** |
| p10 | Double-deck stairs with the relaxed depth | len 100, step 210, step_depth_mm 275, double_deck, new | `step_height_mm`: **fail**<br>`step_depth_mm`: **pass** |
| p11 | Stair depth between the two limits, deck layout not stated | len 100, step_depth_mm 275, new | `step_depth_mm`: **needs human** |
| p12 | Double-deck stairs below even the relaxed depth | len 100, step_depth_mm 265, double_deck, new | `step_depth_mm`: **fail** |
| r01 | Renewal keeps the old handrails | len 100, handrails_renewed 0, outside_diameter_mm 45, renewed | `outside_diameter_mm`: **not applicable** |
| r02 | Renewal replaces the handrails with thick ones | len 100, handrails_renewed 1, outside_diameter_mm 45, renewed | `outside_diameter_mm`: **fail** |
| r03 | Renewal that does not say what happened to the handrails | len 100, outside_diameter_mm 45, renewed | `outside_diameter_mm`: **needs human** |
| r04 | Renewal that complies anyway | len 100, outside_diameter_mm 35, renewed | `outside_diameter_mm`: **pass** |
| r05 | Renewal with steep stairs and a high external step | len 100, external_step 260, step 220, renewed | `step_height_mm`: **not applicable**<br>`external_step_height_mm`: **not applicable** |
| r06 | Renewal that keeps the seating layout, no wheelchair space | len 100, seating_layout_altered_in_entire_train 0, wheelchair_spaces 0, renewed | `wheelchair_spaces`: **not applicable** |
| r07 | Renewal that alters the whole layout but adds one wheelchair space | len 100, seating_layout_altered_in_entire_train 1, wheelchair_spaces 1, renewed | `wheelchair_spaces`: **needs human** |
| r08 | Renewal that keeps the old toilets | len 100, toilets_completely_renewed 0, fitted 2, universal 0, renewed | `universal`: **not applicable** |
| r09 | Renewal that alters a vehicle's layout with a small turning space | len 100, seating_layout_altered_in_entire_vehicle 1, wheelchair_spaces 2, turning_space_diameter_mm 1400, renewed | `turning_space_diameter_mm`: **fail** |
| r10 | Renewal with a narrow exterior door | len 100, clear_width_mm 750, renewed | `clear_width_mm`: **needs human** |

## Reasoning per case

### g01: Compliant regional EMU

*Every supplied value is comfortably inside its limit: no trap, a sanity floor.* Tags: baseline.

- `wheelchair_spaces` → **pass**. Table 5 of point 4.2.2.2(1): 105 m is in the '30 to 205 metres' row, 2 spaces; 2 ≥ 2.
- `exterior_doors.clear_width_mm` → **pass**. 4.2.2.3.2(1): 850 ≥ 800.
- `exterior_doors.wheelchair_door_clear_width_mm` → **pass**. 4.2.2.3.2(2) applies (160 < 250 km/h, level access): 1100 ≥ 1000, and ≥ 800.
- `steps.external_step_height_mm` → **pass**. 4.2.2.11.2(5): 200 ≤ 230.
- `steps.internal_step_height_mm` → **pass**. 4.2.2.11.2(2): 180 ≤ 200.
- `toilets.universal` → **pass**. 4.2.2.5(1): toilets are fitted (2) and 1 is universal.
- `toilets.universal_door_clear_width_mm` → **pass**. 5.3.2.4(3): 900 ≥ 800. The rule sits in 5.3.2.4, not in 4.2.2.5, which only points to it.

### g02: Regional train violating six rules

*Every supplied rule is broken, including the internal step beyond even the 230 mm exception.* Tags: violation, length-dependent.

- `wheelchair_spaces` → **fail**. Table 5 of point 4.2.2.2(1): 150 m needs 2 spaces; 1 < 2.
- `exterior_doors.clear_width_mm` → **fail**. 4.2.2.3.2(1): 760 < 800.
- `exterior_doors.wheelchair_door_clear_width_mm` → **fail**. 4.2.2.3.2(2) applies (160 < 250 km/h, level access): 950 < 1000.
- `steps.external_step_height_mm` → **fail**. 4.2.2.11.2(5): 260 > 230.
- `steps.internal_step_height_mm` → **fail**. 4.2.2.11.2(2): 240 exceeds 200 and also exceeds the 230 mm the exception allows.
- `toilets.universal` → **fail**. 4.2.2.5(1): 3 toilets are fitted, 0 are universal.

### g03: Internal step exactly at the exception limit

*230 mm is allowed only if the step count is reduced, which the spec cannot show.* Tags: needs-human, exception, exact-limit.

- `steps.internal_step_height_mm` → **needs human**. 4.2.2.11.2(2): 230 exceeds 200; the 230 mm maximum is allowed only 'if it can be demonstrated that this achieves a reduction of one in the total number of steps'. The spec has no such data: a person must decide.

### g04: Length exactly 30 m with one wheelchair space

*'Less than 30 m' excludes 30: a 30 m unit is in the 2-space row.* Tags: table-boundary, length-dependent, exact-limit.

- `wheelchair_spaces` → **fail**. Table 5 of point 4.2.2.2(1): 'Less than 30 m' is 1 space, '30 to 205 metres' is 2. 30 is in the second row, so 1 < 2.

### g05: Length exactly 205 m with two wheelchair spaces

*'30 to 205 metres' includes 205: still the 2-space row.* Tags: table-boundary, length-dependent, exact-limit.

- `wheelchair_spaces` → **pass**. Table 5 of point 4.2.2.2(1): 205 is the top of '30 to 205 metres' (2 spaces); 2 ≥ 2.

### g06: Length exactly 300 m with three wheelchair spaces

*'More than 205 to 300 metres' includes 300: still the 3-space row.* Tags: table-boundary, length-dependent, exact-limit.

- `wheelchair_spaces` → **pass**. Table 5 of point 4.2.2.2(1): 300 is the top of 'More than 205 to 300 metres' (3 spaces); 3 ≥ 3.

### g07: Length 300.1 m with three wheelchair spaces

*'More than 300 metres' starts just above 300: the 4-space row.* Tags: table-boundary, length-dependent, exact-limit.

- `wheelchair_spaces` → **fail**. Table 5 of point 4.2.2.2(1): 300.1 is 'More than 300 metres' (4 spaces); 3 < 4.

### g08: Every value exactly at its limit

*Each limit is met with equality, so every rule must read as a pass (30 m is also a table boundary).* Tags: exact-limit, other-section, length-dependent.

- `wheelchair_spaces` → **pass**. Table 5 of point 4.2.2.2(1): 30 m is in the 2-space row; 2 ≥ 2.
- `exterior_doors.clear_width_mm` → **pass**. 4.2.2.3.2(1): 800 ≥ 800 ('minimum' includes the value).
- `exterior_doors.wheelchair_door_clear_width_mm` → **pass**. 4.2.2.3.2(2) applies (160 km/h, level access): 1000 ≥ 1000.
- `steps.external_step_height_mm` → **pass**. 4.2.2.11.2(5): 230 ≤ 230 ('maximum' includes the value).
- `steps.internal_step_height_mm` → **pass**. 4.2.2.11.2(2): 200 ≤ 200.
- `toilets.universal` → **pass**. 4.2.2.5(1): 1 toilet fitted, 1 universal.
- `toilets.universal_door_clear_width_mm` → **pass**. 5.3.2.4(3): 800 ≥ 800.

### g09: Every value just past its limit

*Each limit is missed by the smallest step (0.1 mm, one table row): no rule may pass.* Tags: exact-limit, other-section, violation, length-dependent.

- `wheelchair_spaces` → **fail**. Table 5 of point 4.2.2.2(1): 205.1 is 'More than 205 to 300 metres' (3 spaces); 2 < 3.
- `exterior_doors.clear_width_mm` → **fail**. 4.2.2.3.2(1): 799.9 < 800.
- `exterior_doors.wheelchair_door_clear_width_mm` → **fail**. 4.2.2.3.2(2) applies (160 km/h, level access): 999.9 < 1000.
- `steps.external_step_height_mm` → **fail**. 4.2.2.11.2(5): 230.1 > 230.
- `steps.internal_step_height_mm` → **fail**. 4.2.2.11.2(2): 230.1 exceeds even the 230 mm the exception allows, so no demonstration could save it.
- `toilets.universal` → **pass**. 4.2.2.5(1): 1 toilet fitted, 1 universal.
- `toilets.universal_door_clear_width_mm` → **fail**. 5.3.2.4(3): 799.9 < 800.

### g10: 300 km/h train, wheelchair door 780 mm

*The 1000 mm rule needs a speed below 250 km/h, but the general 800 mm rule still applies to the wheelchair door.* Tags: conditional-rule, high-speed.

- `exterior_doors.wheelchair_door_clear_width_mm` → **fail**. 4.2.2.3.2(2) is for 'a design speed lower than 250 km/h': not met. 4.2.2.3.2(1) covers 'all exterior passenger doorways': 780 < 800.

### g11: 300 km/h train, wheelchair door 900 mm

*Above 250 km/h only the 800 mm rule applies, so 900 mm passes; a 1000 mm rule wrongly applied would fail it.* Tags: conditional-rule, high-speed.

- `exterior_doors.wheelchair_door_clear_width_mm` → **pass**. 4.2.2.3.2(2) does not apply at 300 km/h; 4.2.2.3.2(1): 900 ≥ 800.

### g12: 160 km/h train, wheelchair door 900 mm without level access

*The 1000 mm rule is only for doors 'offering a level access': without it only 800 mm applies.* Tags: conditional-rule.

- `exterior_doors.wheelchair_door_clear_width_mm` → **pass**. 4.2.2.3.2(2) is limited to doors 'offering a level access': this door does not. 4.2.2.3.2(1): 900 ≥ 800.

### g13: Design speed exactly 250 km/h

*The text says 'lower than 250 km/h'; 250 is not lower. JUDGMENT CALL for your review.* Tags: conditional-rule, exact-limit, judgment-call.

- `exterior_doors.wheelchair_door_clear_width_mm` → **pass**. 4.2.2.3.2(2) says 'lower than 250 km/h', so it does not apply at exactly 250; 4.2.2.3.2(1): 900 ≥ 800. A cautious engineer might still ask whether the boundary was intended; this case expects the literal reading.

### g14: Wheelchair door rule needs a design speed the spec omits

*Whether the 1000 mm rule applies depends on design speed, which is not supplied.* Tags: missing-data, needs-human, conditional-rule.

- `exterior_doors.wheelchair_door_clear_width_mm` → **needs human**. 900 passes 800 but fails 1000, and whether 4.2.2.3.2(2) applies depends on the design speed, which the spec does not give.

### g15: Wheelchair door rule needs level-access data the spec omits

*Whether the 1000 mm rule applies depends on level access, which is not supplied.* Tags: missing-data, needs-human, conditional-rule.

- `exterior_doors.wheelchair_door_clear_width_mm` → **needs human**. At 160 km/h, 4.2.2.3.2(2) applies if the door offers level access; the spec does not say. 900 passes 800 but fails 1000.

### g16: Internal step of 215 mm

*Above the 200 mm default but within the 230 mm exception, which needs a demonstration the spec cannot give.* Tags: needs-human, exception.

- `steps.internal_step_height_mm` → **needs human**. 4.2.2.11.2(2): 215 exceeds 200 but not 230; it is allowed only 'if it can be demonstrated' that it reduces the total number of steps by one. A person must decide.

### g17: Train with no toilets

*'When toilets are fitted' is false, so no universal toilet is required: not a pass, not a fail.* Tags: not-applicable.

- `toilets.universal` → **not applicable**. 4.2.2.5(1) applies 'when toilets are fitted in a train'; none are fitted.

### g18: Toilets fitted but none universal

*Toilets are fitted, so a universal toilet is required.* Tags: violation.

- `toilets.universal` → **fail**. 4.2.2.5(1): 2 toilets are fitted and 0 are universal.

### g19: Length includes a power head, two wheelchair spaces

*Table 5 uses the unit length 'excluding the locomotive or power head'. At 210 m 3 spaces are needed, at 205 m or less 2: the true length is unknown.* Tags: needs-human, length-dependent, ambiguous-data.

- `wheelchair_spaces` → **needs human**. 4.2.2.2(1) counts the length 'excluding the locomotive or power head'. The stated 210 m includes it, so the true length is ≤ 210 m: it needs 3 spaces if above 205 m and 2 if not. The spec cannot settle it.

### g20: Length includes a power head, three wheelchair spaces

*Same length basis problem, but 3 spaces meet the largest possible requirement (3 up to 300 m), so the answer is safe.* Tags: length-dependent, ambiguous-data.

- `wheelchair_spaces` → **pass**. Table 5 of point 4.2.2.2(1): whatever the power head's length, the true length is ≤ 210 m, which needs at most 3 spaces; 3 ≥ 3.

### p01: Handrail diameter at the bottom of the range

*'30 mm to 40 mm' includes 30.* Tags: range, exact-limit.

- `handrails.outside_diameter_mm` → **pass**. 4.2.2.9(1): 'outside diameter of 30 mm to 40 mm'; 30 is the lower bound, included.

### p02: Handrail too thick, priority seat at the top of the range

*A range fails above its upper bound; 'between 430 and 500 mm' includes 500.* Tags: range, exact-limit.

- `handrails.outside_diameter_mm` → **fail**. 4.2.2.9(1): 41 mm is above the 40 mm upper bound.
- `priority_seats.cushion_height_mm` → **pass**. 4.2.2.1.2.1(9): 'between 430 and 500 mm above floor level'; 500 is the upper bound, included.

### p03: Priority seat too low

*A range fails below its lower bound.* Tags: range.

- `priority_seats.cushion_height_mm` → **fail**. 4.2.2.1.2.1(9): 425 mm is below the 430 mm lower bound.

### p04: Wheelchair space and turning space exactly at the minimum

*Both minimums are inclusive.* Tags: exact-limit.

- `wheelchair_space_layout.width_mm` → **pass**. 4.2.2.2(3): 'the width shall be 700 mm', read as a minimum; 700 ≥ 700.
- `wheelchair_space_layout.turning_space_diameter_mm` → **pass**. 4.2.2.6(3): 'a minimum diameter of 1 500 mm'; 1500 ≥ 1500.

### p05: Wheelchair space and turning space too small

*Just below both minimums; the regulation writes 1 500 with a space.* Tags: thousand-separator.

- `wheelchair_space_layout.width_mm` → **fail**. 4.2.2.2(3): 690 < 700.
- `wheelchair_space_layout.turning_space_diameter_mm` → **fail**. 4.2.2.6(3): 1450 < 1500.

### p06: Hand clearance on a side next to a wall

*The extra 50 mm applies on each side next to an obstacle; one side is.* Tags: conditional, exact-limit.

- `wheelchair_space_layout.hand_clearance_mm` → **pass**. 4.2.2.2(3): 'an additional 50 mm width ... on each side that is adjacent to any obstacle'; 50 ≥ 50.

### p07: Too little hand clearance, sides not stated

*40 mm fails the rule if any side is next to an obstacle, and the spec does not say: a person decides.* Tags: conditional, missing-data, needs-human.

- `wheelchair_space_layout.hand_clearance_mm` → **needs human**. 4.2.2.2(3): the 50 mm applies only to sides next to an obstacle; sides_next_to_obstacle is not supplied and 40 < 50, so the answer depends on it.

### p08: Wheelchair space open on both sides

*No side is next to an obstacle, so the extra-width rule does not apply.* Tags: conditional, not-applicable.

- `wheelchair_space_layout.hand_clearance_mm` → **not applicable**. 4.2.2.2(3): 'if one side of the wheelchair is adjacent to the aisle there is no additional 50 mm requirement for that side'; with no side next to an obstacle the rule has nothing to apply to.

### p09: Single-deck stairs: height at the limit, depth too short

*The 270 mm depth is permitted only on double deck trains.* Tags: category, exact-limit.

- `stairs.step_height_mm` → **pass**. 4.2.2.8(1): 'maximum height of 200 mm and a minimum depth of 280 mm ... For double deck trains it is permitted to reduce this value to 270 mm': 200 ≤ 200.
- `stairs.step_depth_mm` → **fail**. 4.2.2.8(1): 'maximum height of 200 mm and a minimum depth of 280 mm ... For double deck trains it is permitted to reduce this value to 270 mm': the unit is single deck, so 280 mm applies; 275 < 280.

### p10: Double-deck stairs with the relaxed depth

*On a double deck train 275 mm meets the permitted 270 mm, though not the general 280 mm.* Tags: category, relaxation.

- `stairs.step_height_mm` → **fail**. 4.2.2.8(1): 'maximum height of 200 mm and a minimum depth of 280 mm ... For double deck trains it is permitted to reduce this value to 270 mm': the relaxation is for the depth only; 210 > 200.
- `stairs.step_depth_mm` → **pass**. 4.2.2.8(1): 'maximum height of 200 mm and a minimum depth of 280 mm ... For double deck trains it is permitted to reduce this value to 270 mm': double deck, so 270 mm is permitted; 275 ≥ 270.

### p11: Stair depth between the two limits, deck layout not stated

*275 mm passes only if the train is double deck, which the spec does not say.* Tags: category, relaxation, missing-data, needs-human.

- `stairs.step_depth_mm` → **needs human**. 4.2.2.8(1): 'maximum height of 200 mm and a minimum depth of 280 mm ... For double deck trains it is permitted to reduce this value to 270 mm': 275 fails 280 and meets 270; deck_layout is not supplied.

### p12: Double-deck stairs below even the relaxed depth

*The relaxation does not save a value below 270 mm.* Tags: category, relaxation.

- `stairs.step_depth_mm` → **fail**. 4.2.2.8(1): 'maximum height of 200 mm and a minimum depth of 280 mm ... For double deck trains it is permitted to reduce this value to 270 mm': 265 < 270.

### r01: Renewal keeps the old handrails

*4.2.2.9 is only mandatory where existing handrails are renewed: these were not.* Tags: renewal, exemption.

- `handrails.outside_diameter_mm` → **not applicable**. Appendix F, Handrails: 'only mandatory where existing handrails are being renewed or upgraded'; handrails_renewed is false, so 45 mm need not meet 30–40 mm.

### r02: Renewal replaces the handrails with thick ones

*Renewed handrails must comply.* Tags: renewal, exemption.

- `handrails.outside_diameter_mm` → **fail**. Appendix F, Handrails: the handrails are renewed, so 4.2.2.9(1) applies; 45 > 40.

### r03: Renewal that does not say what happened to the handrails

*45 mm fails unless the handrails were kept, and the spec does not say.* Tags: renewal, exemption, missing-data, needs-human.

- `handrails.outside_diameter_mm` → **needs human**. 4.2.2.9(1) fails (45 > 40); Appendix F exempts handrails that are not renewed, and handrails_renewed is not supplied.

### r04: Renewal that complies anyway

*35 mm meets 30–40 mm, so whether the exemption holds does not matter.* Tags: renewal, exemption, missing-data.

- `handrails.outside_diameter_mm` → **pass**. 4.2.2.9(1): 35 is within 30–40 mm; the Appendix F exemption could only remove the rule.

### r05: Renewal with steep stairs and a high external step

*4.2.2.8 and 4.2.2.11 are not mandatory at renewal or upgrade.* Tags: renewal, exemption.

- `stairs.step_height_mm` → **not applicable**. Appendix F, Height Changes: 'Compliance with the requirements of point 4.2.2.8 is not mandatory at renewal or upgrade.'
- `steps.external_step_height_mm` → **not applicable**. Appendix F, Step positions: 'Compliance with the requirements of points 4.2.2.11 and 4.2.2.12 is not mandatory at renewal or upgrade.'

### r06: Renewal that keeps the seating layout, no wheelchair space

*Wheelchair spaces are only required when the layout is altered within a complete train.* Tags: renewal, exemption, length-dependent.

- `wheelchair_spaces` → **not applicable**. Appendix F, Wheelchair spaces: 'only required when the seating layout is altered within a complete train formation'; it was not.

### r07: Renewal that alters the whole layout but adds one wheelchair space

*Table 5 needs 2 at 100 m; Appendix F waives spaces only if the doorways cannot be modified, which the spec cannot show.* Tags: renewal, exemption, needs-human.

- `wheelchair_spaces` → **needs human**. Table 5: 1 < 2 at 100 m. Appendix F: 'if the entrance doorway, or clearways, cannot be modified to enable wheelchair access, a wheelchair space does not need to be provided'. A person must judge the doorways.

### r08: Renewal that keeps the old toilets

*A universal toilet is only mandatory when the toilets are completely renewed.* Tags: renewal, exemption.

- `toilets.universal` → **not applicable**. Appendix F, Toilets: 'only mandatory when existing toilets are being completely renewed or upgraded'; they are not.

### r09: Renewal that alters a vehicle's layout with a small turning space

*4.2.2.6 is mandatory when a vehicle's layout is altered and a wheelchair space is provided: both hold.* Tags: renewal, exemption.

- `wheelchair_space_layout.turning_space_diameter_mm` → **fail**. Appendix F, Clearways: the layout is altered within an entire vehicle and 2 wheelchair spaces are provided, so 4.2.2.6(3) applies; 1400 < 1500.

### r10: Renewal with a narrow exterior door

*800 mm is required, but widening a door portal is a structural alteration, which Appendix F does not require.* Tags: renewal, exemption, needs-human.

- `exterior_doors.clear_width_mm` → **needs human**. 4.2.2.3.2(1): 750 < 800. Appendix F, Structures: 'Compliance is not mandatory if the work would require structural alterations to door portals'. A person must judge the work.
