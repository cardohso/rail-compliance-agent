# Evaluation results

Model `gemini:gemini-3.5-flash-lite`, search `local`, 20 golden specs, 43 scored verdicts. Intervals are 95% Wilson; with this few cases one case moves a rate by several points.

| Metric | Value (95% CI), k/n |
|---|---|
| `verdict_accuracy` | 0.93 (0.81-0.98), 40/43 |
| `unsafe_pass_rate` | 0.00 (0.00-0.08), 0/43 |
| `needs_human_recall` | 1.00 (0.57-1.00), 5/5 |
| `needs_human_precision` | 0.62 (0.31-0.86), 5/8 |
| `tool_selection_accuracy` | 0.93 (0.81-0.98), 40/43 |
| `argument_correctness` | 1.00 (0.93-1.00), 55/55 |
| `citation_hit_rate` | 1.00 (0.91-1.00), 40/40 |
| `tool_calls_per_parameter` | 3.86 |
| `errors` | 0 |

Per spec: 8.3 tool calls, 9.2 model calls, 13 s mean (6 s median, 33 s p95; model and search time only, rate-limit waits excluded).

### Quality gate: PASSED

| Scope | Metric | Value (95% CI) | n | Required | |
|---|---|---|---|---|---|
| all | `verdict_accuracy` | 0.930 (0.81-0.98) | 43 | ≥ 0.8 | ok |
| all | `unsafe_pass_rate` | 0.000 (0.00-0.08) | 43 | ≤ 0.05 | ok |
| all | `needs_human_recall` | 1.000 (0.57-1.00) | 5 | ≥ 0.4 | ok |
| all | `needs_human_precision` | 0.625 (0.31-0.86) | 8 | ≥ 0.6 | ok |
| all | `tool_selection_accuracy` | 0.930 (0.81-0.98) | 43 | ≥ 0.8 | ok |
| all | `argument_correctness` | 1.000 (0.93-1.00) | 55 | ≥ 0.95 | ok |
| all | `citation_hit_rate` | 1.000 (0.91-1.00) | 40 | ≥ 0.9 | ok |
| all | `tool_calls_per_parameter` | 3.860 | 43 | ≤ 6 | ok |
| all | `errors` | 0.000 | 20 | ≤ 0 | ok |
| tag:exact-limit | `verdict_accuracy` | 0.950 (0.76-0.99) | 20 | ≥ 0.85 | ok |
| tag:table-boundary | `verdict_accuracy` | 1.000 (0.51-1.00) | 4 | ≥ 0.85 | ok |


### By tag (verdict accuracy)

| Tag | Value, k/n |
|---|---|
| `ambiguous-data` | 1.00 (0.34-1.00), 2/2 |
| `baseline` | 0.86 (0.49-0.97), 6/7 |
| `conditional-rule` | 1.00 (0.61-1.00), 6/6 |
| `exact-limit` | 0.95 (0.76-0.99), 19/20 |
| `exception` | 1.00 (0.34-1.00), 2/2 |
| `high-speed` | 1.00 (0.34-1.00), 2/2 |
| `judgment-call` | 1.00 (0.21-1.00), 1/1 |
| `length-dependent` | 0.92 (0.76-0.98), 24/26 |
| `missing-data` | 1.00 (0.34-1.00), 2/2 |
| `needs-human` | 1.00 (0.57-1.00), 5/5 |
| `not-applicable` | 1.00 (0.21-1.00), 1/1 |
| `other-section` | 0.93 (0.69-0.99), 13/14 |
| `table-boundary` | 1.00 (0.51-1.00), 4/4 |
| `violation` | 0.93 (0.69-0.99), 13/14 |

### Confusion (rows: golden verdict, columns: agent verdict)

| golden \ agent | fail | needs_human | not_applicable | pass |
|---|---|---|---|---|
| fail | 15 | 1 | 0 | 0 |
| needs_human | 0 | 5 | 0 | 0 |
| not_applicable | 0 | 0 | 1 | 0 |
| pass | 0 | 2 | 0 | 19 |

### Every scored verdict

| Case | Parameter | Golden | Agent | Tools ok | Cited gold |
|---|---|---|---|---|---|
| g01 | `wheelchair_spaces` | pass | pass (ok) | yes | yes |
| g01 | `exterior_doors.clear_width_mm` | pass | pass (ok) | yes | yes |
| g01 | `exterior_doors.wheelchair_door_clear_width_mm` | pass | pass (ok) | yes | yes |
| g01 | `steps.external_step_height_mm` | pass | pass (ok) | yes | yes |
| g01 | `steps.internal_step_height_mm` | pass | pass (ok) | yes | yes |
| g01 | `toilets.universal` | pass | needs_human (**WRONG**) | no | - |
| g01 | `toilets.universal_door_clear_width_mm` | pass | pass (ok) | yes | yes |
| g02 | `wheelchair_spaces` | fail | fail (ok) | yes | yes |
| g02 | `exterior_doors.clear_width_mm` | fail | fail (ok) | yes | yes |
| g02 | `exterior_doors.wheelchair_door_clear_width_mm` | fail | fail (ok) | yes | yes |
| g02 | `steps.external_step_height_mm` | fail | fail (ok) | yes | yes |
| g02 | `steps.internal_step_height_mm` | fail | fail (ok) | yes | yes |
| g02 | `toilets.universal` | fail | needs_human (**WRONG**) | no | - |
| g03 | `steps.internal_step_height_mm` | needs_human | needs_human (ok) | yes | yes |
| g04 | `wheelchair_spaces` | fail | fail (ok) | yes | yes |
| g05 | `wheelchair_spaces` | pass | pass (ok) | yes | yes |
| g06 | `wheelchair_spaces` | pass | pass (ok) | yes | yes |
| g07 | `wheelchair_spaces` | fail | fail (ok) | yes | yes |
| g08 | `wheelchair_spaces` | pass | pass (ok) | yes | yes |
| g08 | `exterior_doors.clear_width_mm` | pass | pass (ok) | yes | yes |
| g08 | `exterior_doors.wheelchair_door_clear_width_mm` | pass | pass (ok) | yes | yes |
| g08 | `steps.external_step_height_mm` | pass | pass (ok) | yes | yes |
| g08 | `steps.internal_step_height_mm` | pass | pass (ok) | yes | yes |
| g08 | `toilets.universal` | pass | needs_human (**WRONG**) | no | - |
| g08 | `toilets.universal_door_clear_width_mm` | pass | pass (ok) | yes | yes |
| g09 | `wheelchair_spaces` | fail | fail (ok) | yes | yes |
| g09 | `exterior_doors.clear_width_mm` | fail | fail (ok) | yes | yes |
| g09 | `exterior_doors.wheelchair_door_clear_width_mm` | fail | fail (ok) | yes | yes |
| g09 | `steps.external_step_height_mm` | fail | fail (ok) | yes | yes |
| g09 | `steps.internal_step_height_mm` | fail | fail (ok) | yes | yes |
| g09 | `toilets.universal` | pass | pass (ok) | yes | yes |
| g09 | `toilets.universal_door_clear_width_mm` | fail | fail (ok) | yes | yes |
| g10 | `exterior_doors.wheelchair_door_clear_width_mm` | fail | fail (ok) | yes | yes |
| g11 | `exterior_doors.wheelchair_door_clear_width_mm` | pass | pass (ok) | yes | yes |
| g12 | `exterior_doors.wheelchair_door_clear_width_mm` | pass | pass (ok) | yes | yes |
| g13 | `exterior_doors.wheelchair_door_clear_width_mm` | pass | pass (ok) | yes | yes |
| g14 | `exterior_doors.wheelchair_door_clear_width_mm` | needs_human | needs_human (ok) | yes | yes |
| g15 | `exterior_doors.wheelchair_door_clear_width_mm` | needs_human | needs_human (ok) | yes | yes |
| g16 | `steps.internal_step_height_mm` | needs_human | needs_human (ok) | yes | yes |
| g17 | `toilets.universal` | not_applicable | not_applicable (ok) | yes | yes |
| g18 | `toilets.universal` | fail | fail (ok) | yes | yes |
| g19 | `wheelchair_spaces` | needs_human | needs_human (ok) | yes | yes |
| g20 | `wheelchair_spaces` | pass | pass (ok) | yes | yes |
