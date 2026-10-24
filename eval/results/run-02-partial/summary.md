# Evaluation results

Model `gemini:gemini-3.5-flash-lite`, search `local`, 7 golden specs, 18 scored verdicts. Intervals are 95% Wilson; with this few cases one case moves a rate by several points.

| Metric | Value (95% CI), k/n |
|---|---|
| `verdict_accuracy` | 1.00 (0.82-1.00), 18/18 |
| `unsafe_pass_rate` | 0.00 (0.00-0.18), 0/18 |
| `needs_human_recall` | 1.00 (0.21-1.00), 1/1 |
| `needs_human_precision` | 1.00 (0.21-1.00), 1/1 |
| `tool_selection_accuracy` | 1.00 (0.82-1.00), 18/18 |
| `argument_correctness` | 1.00 (0.85-1.00), 22/22 |
| `citation_hit_rate` | 1.00 (0.82-1.00), 18/18 |
| `tool_calls_per_parameter` | 3.44 |
| `errors` | 0 |

Per spec: 8.9 tool calls, 10.9 model calls, 19 s mean (9 s median, 45 s p95; model and search time only, rate-limit waits excluded).

### Quality gate: PASSED

| Scope | Metric | Value (95% CI) | n | Required | |
|---|---|---|---|---|---|
| all | `verdict_accuracy` | 1.000 (0.82-1.00) | 18 | ≥ 0.8 | ok |
| all | `unsafe_pass_rate` | 0.000 (0.00-0.18) | 18 | ≤ 0.05 | ok |
| all | `needs_human_recall` | 1.000 (0.21-1.00) | 1 | ≥ 0.4 | ok |
| all | `needs_human_precision` | 1.000 (0.21-1.00) | 1 | ≥ 0.6 | ok |
| all | `tool_selection_accuracy` | 1.000 (0.82-1.00) | 18 | ≥ 0.8 | ok |
| all | `argument_correctness` | 1.000 (0.85-1.00) | 22 | ≥ 0.95 | ok |
| all | `citation_hit_rate` | 1.000 (0.82-1.00) | 18 | ≥ 0.9 | ok |
| all | `tool_calls_per_parameter` | 3.444 | 18 | ≤ 6 | ok |
| all | `errors` | 0.000 | 7 | ≤ 0 | ok |
| tag:exact-limit | `verdict_accuracy` | 1.000 (0.57-1.00) | 5 | ≥ 0.85 | ok |
| tag:table-boundary | `verdict_accuracy` | 1.000 (0.51-1.00) | 4 | ≥ 0.85 | ok |


### By tag (verdict accuracy)

| Tag | Value, k/n |
|---|---|
| `baseline` | 1.00 (0.65-1.00), 7/7 |
| `exact-limit` | 1.00 (0.57-1.00), 5/5 |
| `exception` | 1.00 (0.21-1.00), 1/1 |
| `length-dependent` | 1.00 (0.72-1.00), 10/10 |
| `needs-human` | 1.00 (0.21-1.00), 1/1 |
| `table-boundary` | 1.00 (0.51-1.00), 4/4 |
| `violation` | 1.00 (0.61-1.00), 6/6 |

### Confusion (rows: golden verdict, columns: agent verdict)

| golden \ agent | fail | needs_human | pass |
|---|---|---|---|
| fail | 8 | 0 | 0 |
| needs_human | 0 | 1 | 0 |
| pass | 0 | 0 | 9 |

### Every scored verdict

| Case | Parameter | Golden | Agent | Tools ok | Cited gold |
|---|---|---|---|---|---|
| g01 | `wheelchair_spaces` | pass | pass (ok) | yes | yes |
| g01 | `exterior_doors.clear_width_mm` | pass | pass (ok) | yes | yes |
| g01 | `exterior_doors.wheelchair_door_clear_width_mm` | pass | pass (ok) | yes | yes |
| g01 | `steps.external_step_height_mm` | pass | pass (ok) | yes | yes |
| g01 | `steps.internal_step_height_mm` | pass | pass (ok) | yes | yes |
| g01 | `toilets.universal` | pass | pass (ok) | yes | yes |
| g01 | `toilets.universal_door_clear_width_mm` | pass | pass (ok) | yes | yes |
| g02 | `wheelchair_spaces` | fail | fail (ok) | yes | yes |
| g02 | `exterior_doors.clear_width_mm` | fail | fail (ok) | yes | yes |
| g02 | `exterior_doors.wheelchair_door_clear_width_mm` | fail | fail (ok) | yes | yes |
| g02 | `steps.external_step_height_mm` | fail | fail (ok) | yes | yes |
| g02 | `steps.internal_step_height_mm` | fail | fail (ok) | yes | yes |
| g02 | `toilets.universal` | fail | fail (ok) | yes | yes |
| g03 | `steps.internal_step_height_mm` | needs_human | needs_human (ok) | yes | yes |
| g04 | `wheelchair_spaces` | fail | fail (ok) | yes | yes |
| g05 | `wheelchair_spaces` | pass | pass (ok) | yes | yes |
| g06 | `wheelchair_spaces` | pass | pass (ok) | yes | yes |
| g07 | `wheelchair_spaces` | fail | fail (ok) | yes | yes |
