# Evaluation results

Model `gemini:gemini-3.5-flash-lite`, search `local`, 10 golden specs, 11 scored verdicts. Intervals are 95% Wilson; with this few cases one case moves a rate by several points.

| Metric | Value (95% CI), k/n |
|---|---|
| `verdict_accuracy` | 0.36 (0.15-0.65), 4/11 |
| `unsafe_pass_rate` | 0.00 (0.00-0.26), 0/11 |
| `needs_human_recall` | 0.00 (0.00-0.56), 0/3 |
| `needs_human_precision` | 0.00 (0.00-0.49), 0/4 |
| `tool_selection_accuracy` | 0.91 (0.62-0.98), 10/11 |
| `argument_correctness` | 1.00 (0.80-1.00), 15/15 |
| `citation_hit_rate` | 0.80 (0.49-0.94), 8/10 |
| `tool_calls_per_parameter` | 5.09 |
| `errors` | 0 |
| `explanation_quality` (report only) | 1.00 (0.51-1.00), 4/4 |

Per spec: 6.1 tool calls, 6.2 model calls, 9 s mean (9 s median, 16 s p95; model and search time only, rate-limit waits excluded).

### Quality gate: FAILED

| Scope | Metric | Value (95% CI) | n | Required | |
|---|---|---|---|---|---|
| all | `verdict_accuracy` | 0.364 (0.15-0.65) | 11 | ≥ 0.65 | **0.364 < 0.65** |
| all | `unsafe_pass_rate` | 0.000 (0.00-0.26) | 11 | ≤ 0.05 | ok |
| all | `needs_human_recall` | 0.000 (0.00-0.56) | 3 | ≥ 0.33 | **0.000 < 0.33** |
| all | `needs_human_precision` | 0.000 (0.00-0.49) | 4 | ≥ 0.5 | **0.000 < 0.5** |
| all | `tool_selection_accuracy` | 0.909 (0.62-0.98) | 11 | ≥ 0.75 | ok |
| all | `argument_correctness` | 1.000 (0.80-1.00) | 15 | ≥ 0.95 | ok |
| all | `citation_hit_rate` | 0.800 (0.49-0.94) | 10 | ≥ 0.75 | ok |
| all | `tool_calls_per_parameter` | 5.091 | 11 | ≤ 9 | ok |
| all | `errors` | 0.000 | 10 | ≤ 0 | ok |


### By tag (verdict accuracy)

| Tag | Value, k/n |
|---|---|
| `exemption` | 0.36 (0.15-0.65), 4/11 |
| `length-dependent` | 0.00 (0.00-0.79), 0/1 |
| `missing-data` | 0.00 (0.00-0.66), 0/2 |
| `needs-human` | 0.00 (0.00-0.56), 0/3 |
| `renewal` | 0.36 (0.15-0.65), 4/11 |

### Confusion (rows: golden verdict, columns: agent verdict)

| golden \ agent | fail | needs_human | not_applicable |
|---|---|---|---|
| fail | 2 | 0 | 0 |
| needs_human | 3 | 0 | 0 |
| not_applicable | 0 | 3 | 2 |
| pass | 0 | 1 | 0 |

### Every scored verdict

| Case | Parameter | Golden | Agent | Tools ok | Cited gold |
|---|---|---|---|---|---|
| r01 | `handrails.outside_diameter_mm` | not_applicable | not_applicable (ok) | yes | yes |
| r02 | `handrails.outside_diameter_mm` | fail | fail (ok) | yes | yes |
| r03 | `handrails.outside_diameter_mm` | needs_human | fail (**WRONG**) | yes | yes |
| r04 | `handrails.outside_diameter_mm` | pass | needs_human (**WRONG**) | yes | yes |
| r05 | `stairs.step_height_mm` | not_applicable | not_applicable (ok) | yes | yes |
| r05 | `steps.external_step_height_mm` | not_applicable | needs_human (**WRONG**) | yes | no |
| r06 | `wheelchair_spaces` | not_applicable | needs_human (**WRONG**) | yes | no |
| r07 | `wheelchair_spaces` | needs_human | fail (**WRONG**) | yes | yes |
| r08 | `toilets.universal` | not_applicable | needs_human (**WRONG**) | no | - |
| r09 | `wheelchair_space_layout.turning_space_diameter_mm` | fail | fail (ok) | yes | yes |
| r10 | `exterior_doors.clear_width_mm` | needs_human | fail (**WRONG**) | yes | yes |
