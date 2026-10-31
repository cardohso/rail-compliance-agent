# Evaluation results

Model `gemini:gemini-3.5-flash-lite`, search `local`, 12 golden specs, 17 scored verdicts. Intervals are 95% Wilson; with this few cases one case moves a rate by several points.

| Metric | Value (95% CI), k/n |
|---|---|
| `verdict_accuracy` | 0.82 (0.59-0.94), 14/17 |
| `unsafe_pass_rate` | 0.06 (0.01-0.27), 1/17 |
| `needs_human_recall` | 0.50 (0.09-0.91), 1/2 |
| `needs_human_precision` | 1.00 (0.21-1.00), 1/1 |
| `tool_selection_accuracy` | 1.00 (0.82-1.00), 17/17 |
| `argument_correctness` | 1.00 (0.85-1.00), 21/21 |
| `citation_hit_rate` | 1.00 (0.82-1.00), 17/17 |
| `tool_calls_per_parameter` | 3.71 |
| `errors` | 0 |
| `explanation_quality` (report only) | 1.00 (0.21-1.00), 1/1 |

Per spec: 5.2 tool calls, 6.2 model calls, 9 s mean (7 s median, 16 s p95; model and search time only, rate-limit waits excluded).

### Quality gate: FAILED

| Scope | Metric | Value (95% CI) | n | Required | |
|---|---|---|---|---|---|
| all | `verdict_accuracy` | 0.824 (0.59-0.94) | 17 | ≥ 0.75 | ok |
| all | `unsafe_pass_rate` | 0.059 (0.01-0.27) | 17 | ≤ 0.05 | **0.059 > 0.05** |
| all | `needs_human_recall` | 0.500 (0.09-0.91) | 2 | ≥ 0.5 | ok |
| all | `needs_human_precision` | 1.000 (0.21-1.00) | 1 | ≥ 0.5 | ok |
| all | `tool_selection_accuracy` | 1.000 (0.82-1.00) | 17 | ≥ 0.8 | ok |
| all | `argument_correctness` | 1.000 (0.85-1.00) | 21 | ≥ 0.95 | ok |
| all | `citation_hit_rate` | 1.000 (0.82-1.00) | 17 | ≥ 0.85 | ok |
| all | `tool_calls_per_parameter` | 3.706 | 17 | ≤ 6 | ok |
| all | `errors` | 0.000 | 12 | ≤ 0 | ok |
| tag:range | `verdict_accuracy` | 1.000 (0.51-1.00) | 4 | ≥ 0.75 | ok |
| tag:relaxation | `verdict_accuracy` | 0.750 (0.30-0.95) | 4 | ≥ 0.7 | ok |


### By tag (verdict accuracy)

| Tag | Value, k/n |
|---|---|
| `category` | 0.83 (0.44-0.97), 5/6 |
| `conditional` | 0.33 (0.06-0.79), 1/3 |
| `exact-limit` | 1.00 (0.68-1.00), 8/8 |
| `missing-data` | 0.50 (0.09-0.91), 1/2 |
| `needs-human` | 0.50 (0.09-0.91), 1/2 |
| `not-applicable` | 0.00 (0.00-0.79), 0/1 |
| `range` | 1.00 (0.51-1.00), 4/4 |
| `relaxation` | 0.75 (0.30-0.95), 3/4 |
| `thousand-separator` | 1.00 (0.34-1.00), 2/2 |

### Confusion (rows: golden verdict, columns: agent verdict)

| golden \ agent | fail | needs_human | pass |
|---|---|---|---|
| fail | 6 | 0 | 1 |
| needs_human | 1 | 1 | 0 |
| not_applicable | 1 | 0 | 0 |
| pass | 0 | 0 | 7 |

### Every scored verdict

| Case | Parameter | Golden | Agent | Tools ok | Cited gold |
|---|---|---|---|---|---|
| p01 | `handrails.outside_diameter_mm` | pass | pass (ok) | yes | yes |
| p02 | `handrails.outside_diameter_mm` | fail | fail (ok) | yes | yes |
| p02 | `priority_seats.cushion_height_mm` | pass | pass (ok) | yes | yes |
| p03 | `priority_seats.cushion_height_mm` | fail | fail (ok) | yes | yes |
| p04 | `wheelchair_space_layout.width_mm` | pass | pass (ok) | yes | yes |
| p04 | `wheelchair_space_layout.turning_space_diameter_mm` | pass | pass (ok) | yes | yes |
| p05 | `wheelchair_space_layout.width_mm` | fail | fail (ok) | yes | yes |
| p05 | `wheelchair_space_layout.turning_space_diameter_mm` | fail | fail (ok) | yes | yes |
| p06 | `wheelchair_space_layout.hand_clearance_mm` | pass | pass (ok) | yes | yes |
| p07 | `wheelchair_space_layout.hand_clearance_mm` | needs_human | fail (**WRONG**) | yes | yes |
| p08 | `wheelchair_space_layout.hand_clearance_mm` | not_applicable | fail (**WRONG**) | yes | yes |
| p09 | `stairs.step_height_mm` | pass | pass (ok) | yes | yes |
| p09 | `stairs.step_depth_mm` | fail | fail (ok) | yes | yes |
| p10 | `stairs.step_height_mm` | fail | pass (**WRONG**) | yes | yes |
| p10 | `stairs.step_depth_mm` | pass | pass (ok) | yes | yes |
| p11 | `stairs.step_depth_mm` | needs_human | needs_human (ok) | yes | yes |
| p12 | `stairs.step_depth_mm` | fail | fail (ok) | yes | yes |
