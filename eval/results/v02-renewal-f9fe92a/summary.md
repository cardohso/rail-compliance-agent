# Evaluation results

Model `gemini:gemini-3.5-flash-lite`, search `local`, 10 golden specs, 11 scored verdicts. Intervals are 95% Wilson; with this few cases one case moves a rate by several points.

| Metric | Value (95% CI), k/n |
|---|---|
| `verdict_accuracy` | 0.73 (0.43-0.90), 8/11 |
| `unsafe_pass_rate` | 0.00 (0.00-0.26), 0/11 |
| `needs_human_recall` | 0.67 (0.21-0.94), 2/3 |
| `needs_human_precision` | 0.67 (0.21-0.94), 2/3 |
| `tool_selection_accuracy` | 1.00 (0.74-1.00), 11/11 |
| `argument_correctness` | 1.00 (0.83-1.00), 19/19 |
| `citation_hit_rate` | 0.82 (0.52-0.95), 9/11 |
| `tool_calls_per_parameter` | 5.00 |
| `errors` | 0 |
| `explanation_quality` (report only) | 1.00 (0.44-1.00), 3/3 |

Per spec: 6.1 tool calls, 6.5 model calls, 10 s mean (8 s median, 18 s p95; model and search time only, rate-limit waits excluded).

### Quality gate: PASSED

| Scope | Metric | Value (95% CI) | n | Required | |
|---|---|---|---|---|---|
| all | `verdict_accuracy` | 0.727 (0.43-0.90) | 11 | ≥ 0.65 | ok |
| all | `unsafe_pass_rate` | 0.000 (0.00-0.26) | 11 | ≤ 0.05 | ok |
| all | `needs_human_recall` | 0.667 (0.21-0.94) | 3 | ≥ 0.33 | ok |
| all | `needs_human_precision` | 0.667 (0.21-0.94) | 3 | ≥ 0.5 | ok |
| all | `tool_selection_accuracy` | 1.000 (0.74-1.00) | 11 | ≥ 0.75 | ok |
| all | `argument_correctness` | 1.000 (0.83-1.00) | 19 | ≥ 0.95 | ok |
| all | `citation_hit_rate` | 0.818 (0.52-0.95) | 11 | ≥ 0.75 | ok |
| all | `tool_calls_per_parameter` | 5.000 | 11 | ≤ 9 | ok |
| all | `errors` | 0.000 | 10 | ≤ 0 | ok |


### By tag (verdict accuracy)

| Tag | Value, k/n |
|---|---|
| `exemption` | 0.73 (0.43-0.90), 8/11 |
| `length-dependent` | 1.00 (0.21-1.00), 1/1 |
| `missing-data` | 1.00 (0.34-1.00), 2/2 |
| `needs-human` | 0.67 (0.21-0.94), 2/3 |
| `renewal` | 0.73 (0.43-0.90), 8/11 |

### Confusion (rows: golden verdict, columns: agent verdict)

| golden \ agent | fail | needs_human | not_applicable | pass |
|---|---|---|---|---|
| fail | 2 | 0 | 0 | 0 |
| needs_human | 1 | 2 | 0 | 0 |
| not_applicable | 1 | 1 | 3 | 0 |
| pass | 0 | 0 | 0 | 1 |

### Every scored verdict

| Case | Parameter | Golden | Agent | Tools ok | Cited gold |
|---|---|---|---|---|---|
| r01 | `handrails.outside_diameter_mm` | not_applicable | not_applicable (ok) | yes | yes |
| r02 | `handrails.outside_diameter_mm` | fail | fail (ok) | yes | yes |
| r03 | `handrails.outside_diameter_mm` | needs_human | needs_human (ok) | yes | yes |
| r04 | `handrails.outside_diameter_mm` | pass | pass (ok) | yes | yes |
| r05 | `stairs.step_height_mm` | not_applicable | needs_human (**WRONG**) | yes | no |
| r05 | `steps.external_step_height_mm` | not_applicable | not_applicable (ok) | yes | yes |
| r06 | `wheelchair_spaces` | not_applicable | not_applicable (ok) | yes | yes |
| r07 | `wheelchair_spaces` | needs_human | fail (**WRONG**) | yes | yes |
| r08 | `toilets.universal` | not_applicable | fail (**WRONG**) | yes | no |
| r09 | `wheelchair_space_layout.turning_space_diameter_mm` | fail | fail (ok) | yes | yes |
| r10 | `exterior_doors.clear_width_mm` | needs_human | needs_human (ok) | yes | yes |
