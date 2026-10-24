# Run 02: PARTIAL (g01-g07 only), 2026-10-24

> Superseded: the full run 02 finished after the quota reset; see `../run-02/RESULT.md`.

The full run 02 stopped after 7 of 20 specs: Gemini's free tier allows 500 requests per day for
this model, and the daily limit was reached ("retry in 4h59m"). Nothing was scored by the run
itself. These numbers come from replaying g01-g07 from the cache (the calls were made during that
run; no new model calls), so they are real model output for those 7 specs and say nothing about
g08-g20.

Code under test: commit `3376cae` (fixes for causes A-D). Thresholds unchanged.

On g01-g07 (18 verdicts): run 01 had 3 wrong (g03, g04, g05); this run has 0 wrong.

| Case | Run 01 | Run 02 | Cause |
|---|---|---|---|
| g03 internal step 230 mm | fail (wrong) | needs_human | A: exception kept its contingency |
| g04 length 30 m, 1 space | needs_human (wrong) | fail | B: no condition on the power-head flag |
| g05 length 205 m, 2 spaces | needs_human (wrong) | pass | B |

NOT yet tested on the real model: the fixes for C (g11-g13) and D (g08), and g16 (A) and g20 (B,
the interval case). The `summary.md` here shows a quality gate computed on 7 specs; ignore it.
The full result will be `eval/results/run-02/` once g08-g20 have run.
