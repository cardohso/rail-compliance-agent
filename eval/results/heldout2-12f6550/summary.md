# Evaluation results

Model `gemini:gemini-3.5-flash-lite`, search `local`, 13 golden specs, 22 scored verdicts. Intervals are 95% Wilson; with this few cases one case moves a rate by several points.

| Metric | Value (95% CI), k/n |
|---|---|
| `verdict_accuracy` | 0.77 (0.57-0.90), 17/22 |
| `unsafe_pass_rate` | 0.00 (0.00-0.15), 0/22 |
| `needs_human_recall` | 0.67 (0.21-0.94), 2/3 |
| `needs_human_precision` | 0.67 (0.21-0.94), 2/3 |
| `tool_selection_accuracy` | 1.00 (0.85-1.00), 22/22 |
| `argument_correctness` | 1.00 (0.88-1.00), 29/29 |
| `citation_hit_rate` | 0.91 (0.72-0.97), 20/22 |
| `tool_calls_per_parameter` | 3.82 |
| `errors` | 0 |
| `explanation_quality` (report only) | 1.00 (0.21-1.00), 1/1 |

Per spec: 6.5 tool calls, 7.8 model calls, 11 s mean (10 s median, 19 s p95; model and search time only, rate-limit waits excluded).

### Quality gate: PASSED

| Scope | Metric | Value (95% CI) | n | Required | |
|---|---|---|---|---|---|
| all | `verdict_accuracy` | 0.773 (0.57-0.90) | 22 | ≥ 0.7 | ok |
| all | `unsafe_pass_rate` | 0.000 (0.00-0.15) | 22 | ≤ 0.05 | ok |
| all | `needs_human_recall` | 0.667 (0.21-0.94) | 3 | ≥ 0.33 | ok |
| all | `needs_human_precision` | 0.667 (0.21-0.94) | 3 | ≥ 0.5 | ok |
| all | `tool_selection_accuracy` | 1.000 (0.85-1.00) | 22 | ≥ 0.75 | ok |
| all | `argument_correctness` | 1.000 (0.88-1.00) | 29 | ≥ 0.95 | ok |
| all | `citation_hit_rate` | 0.909 (0.72-0.97) | 22 | ≥ 0.8 | ok |
| all | `tool_calls_per_parameter` | 3.818 | 22 | ≤ 8 | ok |
| all | `errors` | 0.000 | 13 | ≤ 0 | ok |


### By tag (verdict accuracy)

| Tag | Value, k/n |
|---|---|
| `category` | 1.00 (0.44-1.00), 3/3 |
| `category-table` | 1.00 (0.51-1.00), 4/4 |
| `conditional` | 1.00 (0.34-1.00), 2/2 |
| `exact-limit` | 1.00 (0.61-1.00), 6/6 |
| `exemption` | 0.33 (0.10-0.70), 2/6 |
| `heldout2` | 0.77 (0.57-0.90), 17/22 |
| `length-dependent` | 0.50 (0.09-0.91), 1/2 |
| `missing-data` | 1.00 (0.34-1.00), 2/2 |
| `needs-human` | 0.67 (0.21-0.94), 2/3 |
| `noise` | 0.86 (0.49-0.97), 6/7 |
| `range` | 1.00 (0.51-1.00), 4/4 |
| `relaxation` | 1.00 (0.44-1.00), 3/3 |
| `renewal` | 0.33 (0.10-0.70), 2/6 |
| `table-boundary` | 0.50 (0.09-0.91), 1/2 |
| `thousand-separator` | 1.00 (0.34-1.00), 2/2 |

### Confusion (rows: golden verdict, columns: agent verdict)

| golden \ agent | fail | needs_human | pass |
|---|---|---|---|
| fail | 5 | 0 | 0 |
| needs_human | 1 | 2 | 0 |
| not_applicable | 3 | 1 | 0 |
| pass | 0 | 0 | 10 |

### Every scored verdict

| Case | Parameter | Golden | Agent | Tools ok | Cited gold |
|---|---|---|---|---|---|
| k01 | `handrails.outside_diameter_mm` | pass | pass (ok) | yes | yes |
| k01 | `priority_seats.cushion_height_mm` | pass | pass (ok) | yes | yes |
| k02 | `handrails.outside_diameter_mm` | fail | fail (ok) | yes | yes |
| k02 | `wheelchair_space_layout.turning_space_diameter_mm` | fail | fail (ok) | yes | yes |
| k03 | `stairs.step_height_mm` | pass | pass (ok) | yes | yes |
| k03 | `stairs.step_depth_mm` | pass | pass (ok) | yes | yes |
| k04 | `wheelchair_space_layout.width_mm` | pass | pass (ok) | yes | yes |
| k04 | `wheelchair_space_layout.hand_clearance_mm` | fail | fail (ok) | yes | yes |
| k05 | `stairs.step_depth_mm` | needs_human | needs_human (ok) | yes | yes |
| k06 | `handrails.outside_diameter_mm` | pass | pass (ok) | yes | yes |
| k06 | `stairs.step_depth_mm` | not_applicable | fail (**WRONG**) | yes | no |
| k07 | `wheelchair_spaces` | pass | pass (ok) | yes | yes |
| k07 | `toilets.universal` | not_applicable | needs_human (**WRONG**) | yes | yes |
| k08 | `wheelchair_space_layout.turning_space_diameter_mm` | not_applicable | fail (**WRONG**) | yes | no |
| k09 | `priority_seats.cushion_height_mm` | needs_human | fail (**WRONG**) | yes | yes |
| k10 | `noise.stationary_db` | fail | fail (ok) | yes | yes |
| k10 | `noise.pass_by_250_db` | pass | pass (ok) | yes | yes |
| k11 | `noise.stationary_db` | pass | pass (ok) | yes | yes |
| k11 | `noise.pass_by_80_db` | fail | fail (ok) | yes | yes |
| k12 | `noise.cab_max_speed_db` | pass | pass (ok) | yes | yes |
| k12 | `noise.pass_by_250_db` | not_applicable | fail (**WRONG**) | yes | yes |
| k13 | `noise.cab_standstill_horn_db` | needs_human | needs_human (ok) | yes | yes |
