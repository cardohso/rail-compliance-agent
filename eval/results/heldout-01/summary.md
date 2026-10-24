# Evaluation results

Model `gemini:gemini-3.5-flash-lite`, search `local`, 10 golden specs, 19 scored verdicts. Intervals are 95% Wilson; with this few cases one case moves a rate by several points.

| Metric | Value (95% CI), k/n |
|---|---|
| `verdict_accuracy` | 0.95 (0.75-0.99), 18/19 |
| `unsafe_pass_rate` | 0.00 (0.00-0.17), 0/19 |
| `needs_human_recall` | 1.00 (0.34-1.00), 2/2 |
| `needs_human_precision` | 0.67 (0.21-0.94), 2/3 |
| `tool_selection_accuracy` | 1.00 (0.83-1.00), 19/19 |
| `argument_correctness` | 1.00 (0.86-1.00), 23/23 |
| `citation_hit_rate` | 1.00 (0.83-1.00), 19/19 |
| `tool_calls_per_parameter` | 3.79 |
| `errors` | 0 |

Per spec: 7.2 tool calls, 8.1 model calls, 36 s mean (28 s median, 85 s p95; model and search time only, rate-limit waits excluded).

### Quality gate: PASSED

| Scope | Metric | Value (95% CI) | n | Required | |
|---|---|---|---|---|---|
| all | `verdict_accuracy` | 0.947 (0.75-0.99) | 19 | ≥ 0.8 | ok |
| all | `unsafe_pass_rate` | 0.000 (0.00-0.17) | 19 | ≤ 0.05 | ok |
| all | `needs_human_recall` | 1.000 (0.34-1.00) | 2 | ≥ 0.4 | ok |
| all | `needs_human_precision` | 0.667 (0.21-0.94) | 3 | ≥ 0.6 | ok |
| all | `tool_selection_accuracy` | 1.000 (0.83-1.00) | 19 | ≥ 0.8 | ok |
| all | `argument_correctness` | 1.000 (0.86-1.00) | 23 | ≥ 0.95 | ok |
| all | `citation_hit_rate` | 1.000 (0.83-1.00) | 19 | ≥ 0.9 | ok |
| all | `tool_calls_per_parameter` | 3.789 | 19 | ≤ 6 | ok |
| all | `errors` | 0.000 | 10 | ≤ 0 | ok |


### By tag (verdict accuracy)

| Tag | Value, k/n |
|---|---|
| `ambiguous-data` | 1.00 (0.34-1.00), 2/2 |
| `baseline` | 1.00 (0.65-1.00), 7/7 |
| `conditional-rule` | 1.00 (0.34-1.00), 2/2 |
| `exact-limit` | 1.00 (0.61-1.00), 6/6 |
| `exception` | 1.00 (0.34-1.00), 2/2 |
| `heldout` | 0.95 (0.75-0.99), 18/19 |
| `high-speed` | 1.00 (0.65-1.00), 7/7 |
| `judgment-call` | 0.00 (0.00-0.79), 0/1 |
| `known-limit` | 0.00 (0.00-0.79), 0/1 |
| `length-dependent` | 1.00 (0.76-1.00), 12/12 |
| `missing-data` | 0.00 (0.00-0.79), 0/1 |
| `needs-human` | 1.00 (0.44-1.00), 3/3 |
| `other-section` | 1.00 (0.34-1.00), 2/2 |
| `violation` | 1.00 (0.44-1.00), 3/3 |

### Confusion (rows: golden verdict, columns: agent verdict)

| golden \ agent | fail | needs_human | pass |
|---|---|---|---|
| fail | 5 | 0 | 0 |
| needs_human | 0 | 2 | 0 |
| pass | 0 | 1 | 11 |

### Every scored verdict

| Case | Parameter | Golden | Agent | Tools ok | Cited gold |
|---|---|---|---|---|---|
| h01 | `wheelchair_spaces` | pass | pass (ok) | yes | yes |
| h01 | `exterior_doors.clear_width_mm` | pass | pass (ok) | yes | yes |
| h01 | `exterior_doors.wheelchair_door_clear_width_mm` | pass | pass (ok) | yes | yes |
| h01 | `steps.external_step_height_mm` | pass | pass (ok) | yes | yes |
| h01 | `steps.internal_step_height_mm` | pass | pass (ok) | yes | yes |
| h01 | `toilets.universal` | pass | pass (ok) | yes | yes |
| h01 | `toilets.universal_door_clear_width_mm` | pass | pass (ok) | yes | yes |
| h02 | `wheelchair_spaces` | fail | fail (ok) | yes | yes |
| h02 | `toilets.universal` | fail | fail (ok) | yes | yes |
| h03 | `exterior_doors.wheelchair_door_clear_width_mm` | fail | fail (ok) | yes | yes |
| h04 | `exterior_doors.wheelchair_door_clear_width_mm` | pass | pass (ok) | yes | yes |
| h05 | `wheelchair_spaces` | needs_human | needs_human (ok) | yes | yes |
| h06 | `wheelchair_spaces` | pass | pass (ok) | yes | yes |
| h07 | `wheelchair_spaces` | fail | fail (ok) | yes | yes |
| h08 | `steps.external_step_height_mm` | pass | pass (ok) | yes | yes |
| h08 | `steps.internal_step_height_mm` | needs_human | needs_human (ok) | yes | yes |
| h09 | `toilets.universal` | pass | pass (ok) | yes | yes |
| h09 | `toilets.universal_door_clear_width_mm` | fail | fail (ok) | yes | yes |
| h10 | `exterior_doors.wheelchair_door_clear_width_mm` | pass | needs_human (**WRONG**) | yes | yes |
