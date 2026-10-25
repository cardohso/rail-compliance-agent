## goldpass: FAILED ❌

System `gemini:gemini-3.5-flash-lite via rail_compliance (local search) (replayed from records.json)` · no LLM judge · 43 golden items · k=8 · commit `4004338` · 2026-10-25T08:20:35Z

| Metric | Value | 95% CI | n | Threshold | Status |
|---|---|---|---|---|---|
| Precision@k | 0.12 | 0.06–0.26 | 43 | — |  |
| Recall@k | 1.00 | 0.92–1.00 | 43 | ≥ 0.85 | ✅ |
| Context precision | 0.95 | 0.85–0.99 | 43 | — |  |
| MRR | 0.95 | 0.85–0.99 | 43 | — |  |
| Hit@k | 1.00 | 0.92–1.00 | 43 | ≥ 0.9 | ✅ |
| Grounding | 0.93 | 0.81–0.98 | 43 | ≥ 0.95, n ≥ 10 | ❌ |
| Errors | 0 |  |  | ≤ 0 | ✅ |

_95% CI: Wilson score interval over n questions (conservative for scores that are not yes/no). With few questions it is wide: one question moves a rate by 1/n._

### What failed

- **Grounding**: 0.930 < 0.95 (needs ≥ 0.95, n ≥ 10; 1 question from passing)
  - failing questions: `g01:toilets.universal`, `g02:toilets.universal`, `g08:toilets.universal`

### By tag

| Tag | Answered rate | Grounding | Recall@k | Faithfulness (judge) |
|---|---|---|---|---|
| `ambiguous-data` | — | 1.00 (n=2) | 1.00 (n=2) | — |
| `baseline` | — | 0.86 (n=7) | 1.00 (n=7) | — |
| `conditional-rule` | — | 1.00 (n=6) | 1.00 (n=6) | — |
| `exact-limit` | — | 0.95 (n=20) | 1.00 (n=20) | — |
| `exception` | — | 1.00 (n=2) | 1.00 (n=2) | — |
| `high-speed` | — | 1.00 (n=2) | 1.00 (n=2) | — |
| `judgment-call` | — | 1.00 (n=1) | 1.00 (n=1) | — |
| `length-dependent` | — | 0.92 (n=26) | 1.00 (n=26) | — |
| `missing-data` | — | 1.00 (n=2) | 1.00 (n=2) | — |
| `needs-human` | — | 1.00 (n=5) | 1.00 (n=5) | — |
| `not-applicable` | — | 1.00 (n=1) | 1.00 (n=1) | — |
| `other-section` | — | 0.93 (n=14) | 1.00 (n=14) | — |
| `table-boundary` | — | 1.00 (n=4) | 1.00 (n=4) | — |
| `violation` | — | 0.93 (n=14) | 1.00 (n=14) | — |

### Grounding per source document

| Document | Questions | Answered | Grounding | Also cited |
|---|---|---|---|---|
| `tsi-prm` | 43 | 43 | 0.93 | — |

<details><summary>Metrics skipped on some items</summary>

- 43 × refusals not reported: answered_rate skipped

</details>

<details><summary>Per-item scores</summary>

| Item | Expected | Refused | Recall@k | Grounding | Faithfulness (judge) | Answer relevancy (judge) | Note |
|---|---|---|---|---|---|---|---|
| `g01:wheelchair_spaces` | answer | — | 1.00 | yes | — | — |  |
| `g01:exterior_doors.clear_width_mm` | answer | — | 1.00 | yes | — | — |  |
| `g01:exterior_doors.wheelchair_door_clear_width_mm` | answer | — | 1.00 | yes | — | — |  |
| `g01:steps.external_step_height_mm` | answer | — | 1.00 | yes | — | — |  |
| `g01:steps.internal_step_height_mm` | answer | — | 1.00 | yes | — | — |  |
| `g01:toilets.universal` | answer | — | 1.00 | no | — | — |  |
| `g01:toilets.universal_door_clear_width_mm` | answer | — | 1.00 | yes | — | — |  |
| `g02:wheelchair_spaces` | answer | — | 1.00 | yes | — | — |  |
| `g02:exterior_doors.clear_width_mm` | answer | — | 1.00 | yes | — | — |  |
| `g02:exterior_doors.wheelchair_door_clear_width_mm` | answer | — | 1.00 | yes | — | — |  |
| `g02:steps.external_step_height_mm` | answer | — | 1.00 | yes | — | — |  |
| `g02:steps.internal_step_height_mm` | answer | — | 1.00 | yes | — | — |  |
| `g02:toilets.universal` | answer | — | 1.00 | no | — | — |  |
| `g03:steps.internal_step_height_mm` | answer | — | 1.00 | yes | — | — |  |
| `g04:wheelchair_spaces` | answer | — | 1.00 | yes | — | — |  |
| `g05:wheelchair_spaces` | answer | — | 1.00 | yes | — | — |  |
| `g06:wheelchair_spaces` | answer | — | 1.00 | yes | — | — |  |
| `g07:wheelchair_spaces` | answer | — | 1.00 | yes | — | — |  |
| `g08:wheelchair_spaces` | answer | — | 1.00 | yes | — | — |  |
| `g08:exterior_doors.clear_width_mm` | answer | — | 1.00 | yes | — | — |  |
| `g08:exterior_doors.wheelchair_door_clear_width_mm` | answer | — | 1.00 | yes | — | — |  |
| `g08:steps.external_step_height_mm` | answer | — | 1.00 | yes | — | — |  |
| `g08:steps.internal_step_height_mm` | answer | — | 1.00 | yes | — | — |  |
| `g08:toilets.universal` | answer | — | 1.00 | no | — | — |  |
| `g08:toilets.universal_door_clear_width_mm` | answer | — | 1.00 | yes | — | — |  |
| `g09:wheelchair_spaces` | answer | — | 1.00 | yes | — | — |  |
| `g09:exterior_doors.clear_width_mm` | answer | — | 1.00 | yes | — | — |  |
| `g09:exterior_doors.wheelchair_door_clear_width_mm` | answer | — | 1.00 | yes | — | — |  |
| `g09:steps.external_step_height_mm` | answer | — | 1.00 | yes | — | — |  |
| `g09:steps.internal_step_height_mm` | answer | — | 1.00 | yes | — | — |  |
| `g09:toilets.universal` | answer | — | 1.00 | yes | — | — |  |
| `g09:toilets.universal_door_clear_width_mm` | answer | — | 1.00 | yes | — | — |  |
| `g10:exterior_doors.wheelchair_door_clear_width_mm` | answer | — | 1.00 | yes | — | — |  |
| `g11:exterior_doors.wheelchair_door_clear_width_mm` | answer | — | 1.00 | yes | — | — |  |
| `g12:exterior_doors.wheelchair_door_clear_width_mm` | answer | — | 1.00 | yes | — | — |  |
| `g13:exterior_doors.wheelchair_door_clear_width_mm` | answer | — | 1.00 | yes | — | — |  |
| `g14:exterior_doors.wheelchair_door_clear_width_mm` | answer | — | 1.00 | yes | — | — |  |
| `g15:exterior_doors.wheelchair_door_clear_width_mm` | answer | — | 1.00 | yes | — | — |  |
| `g16:steps.internal_step_height_mm` | answer | — | 1.00 | yes | — | — |  |
| `g17:toilets.universal` | answer | — | 1.00 | yes | — | — |  |
| `g18:toilets.universal` | answer | — | 1.00 | yes | — | — |  |
| `g19:wheelchair_spaces` | answer | — | 1.00 | yes | — | — |  |
| `g20:wheelchair_spaces` | answer | — | 1.00 | yes | — | — |  |

</details>
