# Golden set: review draft

Written by hand from the text of the PRM TSI (Regulation (EU) No 1300/2014, point 4.2.2 and 5.3.2) by one reviewer (the author, with Claude drafting). **Not yet reviewed by anyone else, and not yet used by any evaluation.**

**20 specs, 43 scored parameter verdicts:** 16 fail, 5 needs human, 1 not applicable, 21 pass.

## Assumptions to confirm

1. **Every unit is new** (placed on the market after 28 Sept 2023, point 7.1.2). Appendix F exempts parts of several rules at renewal or upgrade (for example 'Compliance with the requirements of points 4.2.2.11 [steps] ... is not mandatory at renewal or upgrade'). The spec has no field for new vs renewed, so that is out of scope; it is listed as a limitation.
2. **No 'different document' case.** The other six documents in the corpus (Directive, CCS, ENE, SRT, NOI, OPE) contain no passage about these parameters (0 matches for wheelchair, door width, step height, universal toilet). The nearest real traps are a rule in a *different section* (universal toilet door width is in 5.3.2.4, while 4.2.2.5 only points to it: tag `other-section`) and near-identical passages in the PRM TSI itself (Appendix F, national specific cases). If you want a true cross-document trap, a document that states one of these rules differently would have to be added to the corpus.
3. **Only the listed parameters are scored per spec.** The report always has 7 parameters; those a spec does not supply are `needs_human` (missing data) by construction, decided in code without a model call, and are not scored here.
4. **Exemptions that need data the spec lacks are not applied.** 4.2.2.11.2(8) lets some rolling stock for platforms below 380 mm skip the step rules (2) and (5); the spec has no platform height, so a step above the limit is a `fail`, not `needs_human`.

## Judgment calls: please decide

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
| `conditional-rule` | g10, g11, g12, g13, g14, g15 |
| `exact-limit` | g03, g04, g05, g06, g07, g08, g09, g13 |
| `exception` | g03, g16 |
| `high-speed` | g10, g11 |
| `judgment-call` | g13 |
| `length-dependent` | g02, g04, g05, g06, g07, g08, g09, g19, g20 |
| `missing-data` | g14, g15 |
| `needs-human` | g03, g14, g15, g16, g19 |
| `not-applicable` | g17 |
| `other-section` | g08, g09 |
| `table-boundary` | g04, g05, g06, g07 |
| `violation` | g02, g09, g18 |

## Cases

| Id | Title | Spec (supplied values) | Expected |
|---|---|---|---|
| g01 | Compliant regional EMU | len 105, head 0, speed 160, wheelchair_spaces 2, clear_width_mm 850, wheelchair_door 1100, level 1, external_step 200, internal_step 180, fitted 2, universal 1, universal_door 900 | `wheelchair_spaces`: **pass**<br>`clear_width_mm`: **pass**<br>`wheelchair_door_clear_width_mm`: **pass**<br>`external_step_height_mm`: **pass**<br>`internal_step_height_mm`: **pass**<br>`universal`: **pass**<br>`universal_door_clear_width_mm`: **pass** |
| g02 | Regional train violating six rules | len 150, head 0, speed 160, wheelchair_spaces 1, clear_width_mm 760, wheelchair_door 950, level 1, external_step 260, internal_step 240, fitted 3, universal 0 | `wheelchair_spaces`: **fail**<br>`clear_width_mm`: **fail**<br>`wheelchair_door_clear_width_mm`: **fail**<br>`external_step_height_mm`: **fail**<br>`internal_step_height_mm`: **fail**<br>`universal`: **fail** |
| g03 | Internal step exactly at the exception limit | len 100, internal_step 230 | `internal_step_height_mm`: **needs human** |
| g04 | Length exactly 30 m with one wheelchair space | len 30, wheelchair_spaces 1 | `wheelchair_spaces`: **fail** |
| g05 | Length exactly 205 m with two wheelchair spaces | len 205, wheelchair_spaces 2 | `wheelchair_spaces`: **pass** |
| g06 | Length exactly 300 m with three wheelchair spaces | len 300, wheelchair_spaces 3 | `wheelchair_spaces`: **pass** |
| g07 | Length 300.1 m with three wheelchair spaces | len 300.1, wheelchair_spaces 3 | `wheelchair_spaces`: **fail** |
| g08 | Every value exactly at its limit | len 30, head 0, speed 160, wheelchair_spaces 2, clear_width_mm 800, wheelchair_door 1000, level 1, external_step 230, internal_step 200, fitted 1, universal 1, universal_door 800 | `wheelchair_spaces`: **pass**<br>`clear_width_mm`: **pass**<br>`wheelchair_door_clear_width_mm`: **pass**<br>`external_step_height_mm`: **pass**<br>`internal_step_height_mm`: **pass**<br>`universal`: **pass**<br>`universal_door_clear_width_mm`: **pass** |
| g09 | Every value just past its limit | len 205.1, head 0, speed 160, wheelchair_spaces 2, clear_width_mm 799.9, wheelchair_door 999.9, level 1, external_step 230.1, internal_step 230.1, fitted 1, universal 1, universal_door 799.9 | `wheelchair_spaces`: **fail**<br>`clear_width_mm`: **fail**<br>`wheelchair_door_clear_width_mm`: **fail**<br>`external_step_height_mm`: **fail**<br>`internal_step_height_mm`: **fail**<br>`universal`: **pass**<br>`universal_door_clear_width_mm`: **fail** |
| g10 | 300 km/h train, wheelchair door 780 mm | len 200, speed 300, wheelchair_door 780, level 1 | `wheelchair_door_clear_width_mm`: **fail** |
| g11 | 300 km/h train, wheelchair door 900 mm | len 200, speed 300, wheelchair_door 900, level 1 | `wheelchair_door_clear_width_mm`: **pass** |
| g12 | 160 km/h train, wheelchair door 900 mm without level access | len 100, speed 160, wheelchair_door 900, level 0 | `wheelchair_door_clear_width_mm`: **pass** |
| g13 | Design speed exactly 250 km/h | len 100, speed 250, wheelchair_door 900, level 1 | `wheelchair_door_clear_width_mm`: **pass** |
| g14 | Wheelchair door rule needs a design speed the spec omits | len 100, wheelchair_door 900, level 1 | `wheelchair_door_clear_width_mm`: **needs human** |
| g15 | Wheelchair door rule needs level-access data the spec omits | len 100, speed 160, wheelchair_door 900 | `wheelchair_door_clear_width_mm`: **needs human** |
| g16 | Internal step of 215 mm | len 100, internal_step 215 | `internal_step_height_mm`: **needs human** |
| g17 | Train with no toilets | len 100, fitted 0, universal 0 | `universal`: **not applicable** |
| g18 | Toilets fitted but none universal | len 100, fitted 2, universal 0 | `universal`: **fail** |
| g19 | Length includes a power head, two wheelchair spaces | len 210, head 1, wheelchair_spaces 2 | `wheelchair_spaces`: **needs human** |
| g20 | Length includes a power head, three wheelchair spaces | len 210, head 1, wheelchair_spaces 3 | `wheelchair_spaces`: **pass** |

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
