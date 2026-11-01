# Evaluation results

Model `gemini:gemini-3.5-flash-lite`, search `local`, 10 golden specs, 18 scored verdicts. Intervals are 95% Wilson; with this few cases one case moves a rate by several points.

| Metric | Value (95% CI), k/n |
|---|---|
| `verdict_accuracy` | 0.78 (0.55-0.91), 14/18 |
| `unsafe_pass_rate` | 0.00 (0.00-0.18), 0/18 |
| `needs_human_recall` | 1.00 (0.34-1.00), 2/2 |
| `needs_human_precision` | 0.50 (0.15-0.85), 2/4 |
| `tool_selection_accuracy` | 0.83 (0.61-0.94), 15/18 |
| `argument_correctness` | 1.00 (0.78-1.00), 14/14 |
| `citation_hit_rate` | 1.00 (0.78-1.00), 14/14 |
| `tool_calls_per_parameter` | 3.00 |
| `errors` | 0 |
| `explanation_quality` (report only) | 1.00 (0.51-1.00), 4/4 |

Per spec: 5.4 tool calls, 6.8 model calls, 21 s mean (10 s median, 63 s p95; model and search time only, rate-limit waits excluded).

### Quality gate: FAILED

| Scope | Metric | Value (95% CI) | n | Required | |
|---|---|---|---|---|---|
| all | `verdict_accuracy` | 0.778 (0.55-0.91) | 18 | ≥ 0.8 | **0.778 < 0.8** |
| all | `unsafe_pass_rate` | 0.000 (0.00-0.18) | 18 | ≤ 0.05 | ok |
| all | `needs_human_recall` | 1.000 (0.34-1.00) | 2 | ≥ 0.5 | ok |
| all | `needs_human_precision` | 0.500 (0.15-0.85) | 4 | ≥ 0.5 | ok |
| all | `tool_selection_accuracy` | 0.833 (0.61-0.94) | 18 | ≥ 0.8 | ok |
| all | `argument_correctness` | 1.000 (0.78-1.00) | 14 | ≥ 0.95 | ok |
| all | `citation_hit_rate` | 1.000 (0.78-1.00) | 14 | ≥ 0.9 | ok |
| all | `tool_calls_per_parameter` | 3.000 | 18 | ≤ 6 | ok |
| all | `errors` | 0.000 | 10 | ≤ 0 | ok |
| tag:category-table | `verdict_accuracy` | 0.846 (0.58-0.96) | 13 | ≥ 0.75 | ok |


### By tag (verdict accuracy)

| Tag | Value, k/n |
|---|---|
| `category-table` | 0.85 (0.58-0.96), 11/13 |
| `conditional` | 0.00 (0.00-0.66), 0/2 |
| `cross-document` | 1.00 (0.34-1.00), 2/2 |
| `exact-limit` | 0.80 (0.38-0.96), 4/5 |
| `missing-data` | 0.67 (0.21-0.94), 2/3 |
| `needs-human` | 0.67 (0.21-0.94), 2/3 |
| `noise` | 0.78 (0.55-0.91), 14/18 |
| `not-applicable` | 0.00 (0.00-0.66), 0/2 |
| `table-boundary` | 0.80 (0.38-0.96), 4/5 |

### Confusion (rows: golden verdict, columns: agent verdict)

| golden \ agent | fail | needs_human | pass |
|---|---|---|---|
| fail | 5 | 0 | 0 |
| needs_human | 0 | 2 | 0 |
| not_applicable | 2 | 0 | 0 |
| pass | 0 | 2 | 7 |

### Every scored verdict

| Case | Parameter | Golden | Agent | Tools ok | Cited gold |
|---|---|---|---|---|---|
| n01 | `noise.stationary_db` | pass | pass (ok) | yes | yes |
| n01 | `noise.pass_by_80_db` | pass | pass (ok) | yes | yes |
| n02 | `noise.stationary_db` | fail | fail (ok) | yes | yes |
| n02 | `noise.pass_by_80_db` | pass | pass (ok) | yes | yes |
| n03 | `noise.stationary_db` | pass | pass (ok) | yes | yes |
| n03 | `noise.pass_by_80_db` | fail | fail (ok) | yes | yes |
| n04 | `noise.pass_by_250_db` | pass | needs_human (**WRONG**) | no | - |
| n04 | `noise.cab_standstill_horn_db` | pass | pass (ok) | yes | yes |
| n04 | `noise.cab_max_speed_db` | pass | pass (ok) | yes | yes |
| n05 | `noise.cab_standstill_horn_db` | fail | fail (ok) | yes | yes |
| n05 | `noise.cab_max_speed_db` | fail | fail (ok) | yes | yes |
| n06 | `noise.pass_by_250_db` | not_applicable | fail (**WRONG**) | yes | yes |
| n07 | `noise.cab_standstill_horn_db` | not_applicable | fail (**WRONG**) | yes | yes |
| n08 | `noise.stationary_db` | needs_human | needs_human (ok) | yes | - |
| n08 | `noise.pass_by_80_db` | pass | needs_human (**WRONG**) | no | - |
| n09 | `noise.stationary_db` | pass | pass (ok) | yes | yes |
| n09 | `noise.pass_by_80_db` | fail | fail (ok) | yes | yes |
| n10 | `noise.cab_max_speed_db` | needs_human | needs_human (ok) | no | - |
