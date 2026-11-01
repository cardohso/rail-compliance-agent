# Evaluation results

Model `gemini:gemini-3.5-flash-lite`, search `local`, 12 golden specs, 17 scored verdicts. Intervals are 95% Wilson; with this few cases one case moves a rate by several points.

| Metric | Value (95% CI), k/n |
|---|---|
| `verdict_accuracy` | 1.00 (0.82-1.00), 17/17 |
| `unsafe_pass_rate` | 0.00 (0.00-0.18), 0/17 |
| `needs_human_recall` | 1.00 (0.34-1.00), 2/2 |
| `needs_human_precision` | 1.00 (0.34-1.00), 2/2 |
| `tool_selection_accuracy` | 1.00 (0.82-1.00), 17/17 |
| `argument_correctness` | 1.00 (0.85-1.00), 22/22 |
| `citation_hit_rate` | 1.00 (0.82-1.00), 17/17 |
| `tool_calls_per_parameter` | 3.94 |
| `errors` | 0 |
| `explanation_quality` (report only) | 1.00 (0.34-1.00), 2/2 |

Per spec: 5.6 tool calls, 6.3 model calls, 9 s mean (8 s median, 15 s p95; model and search time only, rate-limit waits excluded).

### Quality gate: PASSED

| Scope | Metric | Value (95% CI) | n | Required | |
|---|---|---|---|---|---|
| all | `verdict_accuracy` | 1.000 (0.82-1.00) | 17 | ≥ 0.75 | ok |
| all | `unsafe_pass_rate` | 0.000 (0.00-0.18) | 17 | ≤ 0.05 | ok |
| all | `needs_human_recall` | 1.000 (0.34-1.00) | 2 | ≥ 0.5 | ok |
| all | `needs_human_precision` | 1.000 (0.34-1.00) | 2 | ≥ 0.5 | ok |
| all | `tool_selection_accuracy` | 1.000 (0.82-1.00) | 17 | ≥ 0.8 | ok |
| all | `argument_correctness` | 1.000 (0.85-1.00) | 22 | ≥ 0.95 | ok |
| all | `citation_hit_rate` | 1.000 (0.82-1.00) | 17 | ≥ 0.85 | ok |
| all | `tool_calls_per_parameter` | 3.941 | 17 | ≤ 6 | ok |
| all | `errors` | 0.000 | 12 | ≤ 0 | ok |
| tag:range | `verdict_accuracy` | 1.000 (0.51-1.00) | 4 | ≥ 0.75 | ok |
| tag:relaxation | `verdict_accuracy` | 1.000 (0.51-1.00) | 4 | ≥ 0.7 | ok |


### By tag (verdict accuracy)

| Tag | Value, k/n |
|---|---|
| `category` | 1.00 (0.61-1.00), 6/6 |
| `conditional` | 1.00 (0.44-1.00), 3/3 |
| `exact-limit` | 1.00 (0.68-1.00), 8/8 |
| `missing-data` | 1.00 (0.34-1.00), 2/2 |
| `needs-human` | 1.00 (0.34-1.00), 2/2 |
| `not-applicable` | 1.00 (0.21-1.00), 1/1 |
| `range` | 1.00 (0.51-1.00), 4/4 |
| `relaxation` | 1.00 (0.51-1.00), 4/4 |
| `thousand-separator` | 1.00 (0.34-1.00), 2/2 |

### Confusion (rows: golden verdict, columns: agent verdict)

| golden \ agent | fail | needs_human | not_applicable | pass |
|---|---|---|---|---|
| fail | 7 | 0 | 0 | 0 |
| needs_human | 0 | 2 | 0 | 0 |
| not_applicable | 0 | 0 | 1 | 0 |
| pass | 0 | 0 | 0 | 7 |

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
| p07 | `wheelchair_space_layout.hand_clearance_mm` | needs_human | needs_human (ok) | yes | yes |
| p08 | `wheelchair_space_layout.hand_clearance_mm` | not_applicable | not_applicable (ok) | yes | yes |
| p09 | `stairs.step_height_mm` | pass | pass (ok) | yes | yes |
| p09 | `stairs.step_depth_mm` | fail | fail (ok) | yes | yes |
| p10 | `stairs.step_height_mm` | fail | fail (ok) | yes | yes |
| p10 | `stairs.step_depth_mm` | pass | pass (ok) | yes | yes |
| p11 | `stairs.step_depth_mm` | needs_human | needs_human (ok) | yes | yes |
| p12 | `stairs.step_depth_mm` | fail | fail (ok) | yes | yes |
