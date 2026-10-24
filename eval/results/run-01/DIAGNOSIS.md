# Run 01: first full evaluation (2026-10-24)

Model `gemini:gemini-3.5-flash-lite`, local search, empty cache, 20 specs, 43 scored verdicts,
22 minutes. Thresholds as committed in `1c8ac7a`, before this run, **unchanged**.

**Quality gate: FAILED** (4 of 15 checks). goldpass gate (retrieval, citations, grounding): passed.

| Check | Result | Required |
|---|---|---|
| `verdict_accuracy` | 0.791 (34/43) | ≥ 0.80: **one verdict short** (35/43 passes) |
| `needs_human_precision` | 0.333 (3/9) | ≥ 0.60: **failed** |
| `verdict_accuracy`, tag `exact-limit` | 0.750 (15/20) | ≥ 0.85: **failed** |
| `verdict_accuracy`, tag `table-boundary` | 0.500 (2/4) | ≥ 0.85: **failed** |
| `unsafe_pass_rate` | 0.000 (0/43) | ≤ 0.05 |
| `needs_human_recall` | 0.600 (3/5) | ≥ 0.40 |
| `tool_selection_accuracy` | 1.000 (43/43) | ≥ 0.80 |
| `argument_correctness` | 1.000 (59/59) | ≥ 0.95 |
| `citation_hit_rate` | 1.000 (43/43) | ≥ 0.90 |
| `tool_calls_per_parameter` | 4.40 | ≤ 6 |
| `errors` | 0 | ≤ 0 |

Reading the numbers: the agent never said `pass` where the answer was `fail` or `needs_human`
(0 of 43), always found the right passage, and called the right tools with the right arguments.
Every one of the 9 misses is a wrong *verdict* reached through a correct-looking process. Tool
selection, argument correctness and citation hit rate are at 100% and so say nothing about the
misses: they do not separate this agent from a better one on this set.

## The nine misses, by cause (each checked in the trace)

**A. Exception rules extracted as unconditional (g03, g16; expected `needs_human`, got `fail`).**
The 230 mm internal-step exception ("may be increased ... if it can be demonstrated ...") was
extracted as an unconditional `≤ 230 mm` rule. In g16 the agent then *did* call `needs_human`
("complies with the conditional exception"), but `settle` ranks a failed check above an
escalation, so the escalation was discarded. A design flaw in the aggregation, not only the model.

**B. A condition invented on an optional flag (g04, g05, g20).** From "excluding the locomotive or
power head" the extraction added the condition `length_includes_power_head == 0`. Specs that omit
that optional flag then got `needs_human` ("not supplied"), although `unit_length_m` is defined
as already excluding a power head. g20 (flag true, 3 spaces, which is enough at any length) is the
hard case it was built to be; g04 and g05 are not. Extraction varied between specs: g06 and g07
did not add the condition.

**C. Will not apply the general rule once the special rule does not apply (g11, g12, g13).** For
the wheelchair-door parameter the extractor kept returning the 1000 mm special-case rule even
when asked for "all exterior passenger doorways", so after `not_applicable` there was nothing left
and the agent escalated. g10 (same trap) passed, so this is inconsistent, not absent. In g12 the
model also called a tool `needs_home`; the runtime rejected it and the run recovered.

**D. A real rule attributed to the wrong parameter (g08; expected `pass`, got `fail`).** For
`clear_width_mm` (narrowest exterior doorway) the model also extracted the wheelchair-door rule
(1000 mm, conditions met) and `check` applied it to an 800 mm door. The quote and number were
real, so the verification passed: no deterministic check can catch a verified but misapplied rule.

## Against what was expected beforehand

`thresholds.yaml` predicted g10, g19, and probably g03/g16 would be missed. g10 and g19 were
right; g03/g16 were missed; seven further misses (B, C, D) were not anticipated.

## Caveats on these numbers

- One run. The model's sampling is fixed by the provider (no temperature control), so a fresh run
  with an empty cache can differ; this run is pinned only by the cache. Run-to-run variance has
  not been measured.
- 43 verdicts, one reviewer, and a set that is harder than a random one for this agent (see
  `eval/GOLDEN_SET_REVIEW.md`). The tags `table-boundary` (n=4) and `exception` (n=2) rest on a
  handful of cases.
- Any change made after reading this file is tuned on the golden set that produced it, so later
  numbers on the same set are optimistic.
