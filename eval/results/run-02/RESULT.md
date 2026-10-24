# Run 02: after the fixes for run 01's four causes (2026-10-24)

Model `gemini:gemini-3.5-flash-lite`, local search, 20 golden specs, 43 scored verdicts. Code:
`3376cae` plus later commits that do not touch the agent's behaviour. Thresholds unchanged since
`1c8ac7a`. The run was interrupted by the free tier's daily quota and resumed from the cache after
the reset; every call is real model output, none was replayed from a different prompt.

**Quality gate: PASSED.** goldpass gate (retrieval, citations, grounding): PASSED.

| Metric | Run 01 | Run 02 | Required |
|---|---|---|---|
| `verdict_accuracy` | 0.791 (34/43) | **1.000 (43/43)** | ≥ 0.80 |
| `unsafe_pass_rate` | 0.000 (0/43) | 0.000 (0/43) | ≤ 0.05 |
| `needs_human_recall` | 0.600 (3/5) | 1.000 (5/5) | ≥ 0.40 |
| `needs_human_precision` | 0.333 (3/9) | 1.000 (5/5) | ≥ 0.60 |
| `tool_selection_accuracy` | 1.000 (43/43) | 1.000 (43/43) | ≥ 0.80 |
| `argument_correctness` | 1.000 (59/59) | 1.000 (56/56) | ≥ 0.95 |
| `citation_hit_rate` | 1.000 (43/43) | 1.000 (43/43) | ≥ 0.90 |
| tool calls per parameter | 4.40 | 3.72 | ≤ 6 |
| tag `exact-limit` accuracy | 0.750 (15/20) | 1.000 (20/20) | ≥ 0.85 |
| tag `table-boundary` accuracy | 0.500 (2/4) | 1.000 (4/4) | ≥ 0.85 |
| per spec, mean (p95) | 42.9 s (168 s) | 30.8 s (117 s) | not gated |

All nine run-01 misses are fixed (g03, g04, g05, g08, g11, g12, g13, g16, g20); nothing regressed.
Zero of 257 tool calls were rejected by the runtime.

## How to read this: it is a development-set result

- **The fixes were designed after reading run 01's misses on this same golden set**, so 43/43 says
  the fixes work on the cases that motivated them. It does not say the agent would score 43/43 on
  new specs. The honest generalisation test is a set written before the agent sees it.
- **One run each.** The provider fixes the model's sampling (no temperature control), so a fresh
  run with an empty cache can differ. Run-to-run variance has not been measured.
- **43 verdicts, one reviewer**, and only 5 expected escalations. A perfect score on 5 has a 95%
  interval of roughly 0.57-1.00.
- **Right verdict, poor explanation.** In g19 the verdict is correct (decided by the interval
  check), but the model's own written reason rambles and contradicts itself ("...but wait..."). The
  metrics do not score explanations.
- **Tool selection, argument and citation metrics were already at 100% in run 01** and so did not
  separate the two runs: they measure that the process is orderly, not that the verdict is right.

## What the spot checks show (mechanism, not luck)

g03 reached `needs_human` through the contingency logic alone (no model escalation). g20 passed
through the interval check ("3 meets >= 1, 2, 3 for every length between 0 and 210"). g11 and g13
passed by applying the general 800 mm rule, which is stated for all exterior doorways, to wheelchair
doorways. g16 was both escalated by the model and flagged by the contingency.

## Cost

The full run is 245 distinct model calls (the cache holds one entry per call), against Gemini's
500 a day: one fresh full run fits in a day, two do not.
