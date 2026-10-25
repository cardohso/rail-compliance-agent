# Third full `eval.yml` run on GitHub: the coverage check, on CI run 2's draw (2026-10-25)

Run [`40235005513`](https://github.com/cardohso/rail-compliance-agent/actions/runs/40235005513), manual
dispatch with no `cases` filter, head `77b6312`. **The job passed: every step, both gates.**

## This is a controlled replay, not a fresh sample

The coverage check changes no prompt, so the runner restored CI run 2's saved cache
(`eval-cache-f538fdc…`) and every model and search call was a cache hit. Checked, not assumed: for all
**20 of 20 specs the full tool-call trace (tool names and arguments) is identical to CI run 2**. So
run 3 is run 2's model draw with the coverage check switched on, which isolates exactly what the
check does. It is **not** a new measurement of run-to-run variance, and it cost almost no quota.

| Metric | CI run 2 | CI run 3 | Required |
|---|---|---|---|
| `verdict_accuracy` | 0.977 (42/43) | 1.000 (43/43) | ≥ 0.80 |
| `unsafe_pass_rate` | 0.023 (1/43) | **0.000 (0/43)** | ≤ 0.05 |
| `needs_human_recall` | 0.800 (4/5) | 1.000 (5/5) | ≥ 0.40 |
| `needs_human_precision` | 1.000 (4/4) | 1.000 (5/5) | ≥ 0.60 |
| `tool_selection_accuracy` | 1.000 (43/43) | 1.000 (43/43) | ≥ 0.80 |
| `argument_correctness` | 1.000 (57/57) | 1.000 (57/57) | ≥ 0.95 |
| `citation_hit_rate` | 1.000 (43/43) | 1.000 (43/43) | ≥ 0.90 |

**The only verdict that changed is g14: `pass` → `needs_human`** (golden: `needs_human`). The reason the
report gives names the sentence that was missed: "(2) On trains with a design speed lower than 250 km/h,
wheelchair access doors ... 1 000 mm ...", which no extracted rule covers.

## What this does and does not show

- It shows the check does what it was built to do on the case that motivated it, in CI, end to end,
  and that it changes nothing else in this draw (42 of 43 verdicts unchanged, no false alarm).
- It does not show the check works on **new** draws. The check was designed after seeing g14 and
  refined after seeing four false alarms in these same saved reports (replaying 148 saved real
  verdicts: 1 catch, 0 false alarms after the refinement). That 0 is a fit to dev data.
- A fresh-cache run (about 235 model requests) would give new extractions and a first look at how the
  check behaves on draws it has not been tuned on.
- The check is narrow: five millimetre parameters, cited passages only, sentences that name a subject.
