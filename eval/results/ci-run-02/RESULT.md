# Second full `eval.yml` run on GitHub, after the extraction-prompt fix (2026-10-25)

Run [`40230125813`](https://github.com/cardohso/rail-compliance-agent/actions/runs/40230125813), manual
dispatch with no `cases` filter, head `f538fdc` (the previous CI run, `40175097116`, was `4004338`). The
only code change between them is one instruction in the extraction prompt: "X shall be provided /
fitted / installed" states a minimum of one. Thresholds unchanged. **The job passed: every step
succeeded, and both gates (enforced on a full run) passed.** `docker` also passed.

| Metric | CI run 1 (before fix) | CI run 2 (after fix) | Required |
|---|---|---|---|
| `verdict_accuracy` | 0.930 (40/43) | **0.977 (42/43)** | ≥ 0.80 |
| `unsafe_pass_rate` | 0.000 (0/43) | **0.023 (1/43)** | ≤ 0.05 |
| `needs_human_recall` | 1.000 (5/5) | 0.800 (4/5) | ≥ 0.40 |
| `needs_human_precision` | 0.625 (5/8) | 1.000 (4/4) | ≥ 0.60 |
| `tool_selection_accuracy` | 0.930 (40/43) | 1.000 (43/43) | ≥ 0.80 |
| `argument_correctness` | 1.000 (55/55) | 1.000 (57/57) | ≥ 0.95 |
| `citation_hit_rate` | 1.000 (40/40) | 1.000 (43/43) | ≥ 0.90 |
| goldpass `grounding` | 0.930 (**failed**) | 1.000 | ≥ 0.95 |
| goldpass `recall@k` / `hit@k` | 1.000 / 1.000 | 1.000 / 1.000 | ≥ 0.85 / 0.90 |

## What changed

- **The fix worked where it was aimed:** `toilets.universal` in g01, g02 and g08 now extract the rule
  and check it (`needs_human` -> `pass`, `fail`, `pass`), so the missing citations, the grounding
  failure and the escalation-precision problem are gone.
- **One new miss, and it is the dangerous kind: g14, golden `needs_human`, agent `pass`.** It is the
  first false pass in any full run (local run 01, run 02, the held-out run and CI run 1 all had 0), on
  a case that was correct every earlier time. 1/43 = 0.023 is inside the 0.05 floor, which is why the
  gate passed, but it should not be read as noise.

## Why g14 went wrong: a false pass by omission

g14 has a wheelchair door of 900 mm, level access, and no design speed. The right outcome is
`needs_human`: the 1000 mm rule applies below 250 km/h and the speed is unknown. This time the agent
extracted the general 800 mm rule **twice** (its focus "wheelchair doors width" returned the general
rule again) and never extracted the conditional 1000 mm rule. `check` was then correct about what it
was given (900 >= 800, pass) and nothing flagged the rule that was missing.

That is a structural limit, not only a sampling accident: **the verdict is computed from the rules the
agent happened to extract, and code cannot know a rule is missing.** The "no false passes" results in
the earlier runs rested partly on the model extracting every applicable rule each time.

## Variance, now measured twice on the same code family

Two fresh-cache CI runs differ in four verdicts between them (three toilet items fixed by the prompt
change, one door item newly wrong). Across all full runs the dev-set accuracy has been 34/43 (before
the fixes), 43/43, 40/43 and 42/43. The agent's behaviour on identical specs is not fixed by anything
except the cache.
