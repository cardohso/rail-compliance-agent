# Held-out run (2026-10-24): 10 specs, 19 verdicts, run once

Specs and verdicts committed in `04fea27` at 13:26, **before** the agent was run on them (13:26 to
13:34). Same code as run 02 (`1cedb8f`), same metric floors, no tag slices. The model's sampling is
fixed by the provider, so a fresh run could differ; this is one run.

**Quality gate: PASSED** (the floors are the main set's; with 19 verdicts read them as a measurement).

| Metric | Held-out | Dev set, run 02 | Required |
|---|---|---|---|
| `verdict_accuracy` | **0.947 (18/19)**, CI 0.75-0.99 | 1.000 (43/43) | ≥ 0.80 |
| `unsafe_pass_rate` | 0.000 (0/19) | 0.000 (0/43) | ≤ 0.05 |
| `needs_human_recall` | 1.000 (2/2) | 1.000 (5/5) | ≥ 0.40 |
| `needs_human_precision` | 0.667 (2/3) | 1.000 (5/5) | ≥ 0.60 |
| `tool_selection_accuracy` | 1.000 (19/19) | 1.000 (43/43) | ≥ 0.80 |
| `argument_correctness` | 1.000 (23/23) | 1.000 (56/56) | ≥ 0.95 |
| `citation_hit_rate` | 1.000 (19/19) | 1.000 (43/43) | ≥ 0.90 |
| tool calls per parameter | 3.79 | 3.72 | ≤ 6 |
| per spec, mean (p95) | 35.6 s (85 s) | 30.8 s (117 s) | not gated |

## The one miss, predicted in advance

**h10**: wheelchair door exactly 1000 mm, level access, design speed not given. Golden: `pass` (the
door meets the 1000 mm rule if it applies and the 800 mm rule if it does not, so the missing speed
does not matter). Agent: `needs_human`. This is the mechanism the case was written to expose and
labelled `known-limit` before the run: `check` returns `needs_human` whenever a rule's condition
cannot be decided, even when the value passes on both sides of it. The agent's own reason says exactly
that. Deliberately not fixed: changing the agent now would turn this set into a second dev set.

Every other verdict matched, including the ones built to catch the fixes: the interval cases
(h05 `needs_human`, h06 `pass`), the exception band (h08), and the speed boundary on either side
(h03 `fail` at 249.9 km/h, h04 `pass` at 250.1 km/h).

## What this does and does not show

- **Predictions held in both directions.** I expected one miss (h10) and 18 correct; that is what
  happened. No surprise in either direction is weak evidence of overfitting to the dev set's values.
- **It is not evidence about new rules.** All seven rules were in the dev set and in the prompts'
  design; the corpus has nothing else for the spec's parameters. These specs vary values and
  combinations, not rules.
- **Small.** 19 verdicts, so the 95% interval on accuracy is 0.75-0.99, and 3 expected-or-given
  escalations, so escalation precision and recall mean little. 18/19 and 43/43 are not distinguishable
  from each other at this size.
- **One reviewer**, who also wrote the agent's fixes. Verdicts were fixed before the run, but
  by the same person who knew which weaknesses the dev set had exposed.
- **Cost:** 105 new model calls, 8 minutes.
