# Evaluation results

Model `gemini:gemini-3.5-flash-lite`, search `local`, 10 golden specs, 18 scored verdicts. Intervals are 95% Wilson; with this few cases one case moves a rate by several points.

| Metric | Value (95% CI), k/n |
|---|---|
| `verdict_accuracy` | 0.94 (0.74-0.99), 17/18 |
| `unsafe_pass_rate` | 0.00 (0.00-0.18), 0/18 |
| `needs_human_recall` | 1.00 (0.34-1.00), 2/2 |
| `needs_human_precision` | 1.00 (0.34-1.00), 2/2 |
| `tool_selection_accuracy` | 1.00 (0.82-1.00), 18/18 |
| `argument_correctness` | 1.00 (0.82-1.00), 18/18 |
| `citation_hit_rate` | 1.00 (0.82-1.00), 18/18 |
| `tool_calls_per_parameter` | 3.39 |
| `errors` | 0 |
| `explanation_quality` (report only) | 1.00 (0.34-1.00), 2/2 |

Per spec: 6.1 tool calls, 7.2 model calls, 121 s mean (48 s median, 425 s p95; model and search time only, rate-limit waits excluded).

### Quality gate: PASSED

| Scope | Metric | Value (95% CI) | n | Required | |
|---|---|---|---|---|---|
| all | `verdict_accuracy` | 0.944 (0.74-0.99) | 18 | ≥ 0.8 | ok |
| all | `unsafe_pass_rate` | 0.000 (0.00-0.18) | 18 | ≤ 0.05 | ok |
| all | `needs_human_recall` | 1.000 (0.34-1.00) | 2 | ≥ 0.5 | ok |
| all | `needs_human_precision` | 1.000 (0.34-1.00) | 2 | ≥ 0.5 | ok |
| all | `tool_selection_accuracy` | 1.000 (0.82-1.00) | 18 | ≥ 0.8 | ok |
| all | `argument_correctness` | 1.000 (0.82-1.00) | 18 | ≥ 0.95 | ok |
| all | `citation_hit_rate` | 1.000 (0.82-1.00) | 18 | ≥ 0.9 | ok |
| all | `tool_calls_per_parameter` | 3.389 | 18 | ≤ 6 | ok |
| all | `errors` | 0.000 | 10 | ≤ 0 | ok |
| tag:category-table | `verdict_accuracy` | 1.000 (0.77-1.00) | 13 | ≥ 0.75 | ok |


### By tag (verdict accuracy)

| Tag | Value, k/n |
|---|---|
| `category-table` | 1.00 (0.77-1.00), 13/13 |
| `conditional` | 0.50 (0.09-0.91), 1/2 |
| `cross-document` | 1.00 (0.34-1.00), 2/2 |
| `exact-limit` | 1.00 (0.57-1.00), 5/5 |
| `missing-data` | 1.00 (0.44-1.00), 3/3 |
| `needs-human` | 1.00 (0.44-1.00), 3/3 |
| `noise` | 0.94 (0.74-0.99), 17/18 |
| `not-applicable` | 0.50 (0.09-0.91), 1/2 |
| `table-boundary` | 1.00 (0.57-1.00), 5/5 |

### Confusion (rows: golden verdict, columns: agent verdict)

| golden \ agent | fail | needs_human | not_applicable | pass |
|---|---|---|---|---|
| fail | 5 | 0 | 0 | 0 |
| needs_human | 0 | 2 | 0 | 0 |
| not_applicable | 1 | 0 | 1 | 0 |
| pass | 0 | 0 | 0 | 9 |

### Every scored verdict

| Case | Parameter | Golden | Agent | Tools ok | Cited gold |
|---|---|---|---|---|---|
| n01 | `noise.stationary_db` | pass | pass (ok) | yes | yes |
| n01 | `noise.pass_by_80_db` | pass | pass (ok) | yes | yes |
| n02 | `noise.stationary_db` | fail | fail (ok) | yes | yes |
| n02 | `noise.pass_by_80_db` | pass | pass (ok) | yes | yes |
| n03 | `noise.stationary_db` | pass | pass (ok) | yes | yes |
| n03 | `noise.pass_by_80_db` | fail | fail (ok) | yes | yes |
| n04 | `noise.pass_by_250_db` | pass | pass (ok) | yes | yes |
| n04 | `noise.cab_standstill_horn_db` | pass | pass (ok) | yes | yes |
| n04 | `noise.cab_max_speed_db` | pass | pass (ok) | yes | yes |
| n05 | `noise.cab_standstill_horn_db` | fail | fail (ok) | yes | yes |
| n05 | `noise.cab_max_speed_db` | fail | fail (ok) | yes | yes |
| n06 | `noise.pass_by_250_db` | not_applicable | fail (**WRONG**) | yes | yes |
| n07 | `noise.cab_standstill_horn_db` | not_applicable | not_applicable (ok) | yes | yes |
| n08 | `noise.stationary_db` | needs_human | needs_human (ok) | yes | yes |
| n08 | `noise.pass_by_80_db` | pass | pass (ok) | yes | yes |
| n09 | `noise.stationary_db` | pass | pass (ok) | yes | yes |
| n09 | `noise.pass_by_80_db` | fail | fail (ok) | yes | yes |
| n10 | `noise.cab_max_speed_db` | needs_human | needs_human (ok) | yes | yes |
