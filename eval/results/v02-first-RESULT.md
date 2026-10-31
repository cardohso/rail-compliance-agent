# First runs of the v0.2 suites (commit a7d7362)

Run on 2026-10-30/31 with `gemini-3.5-flash-lite`, thresholds committed before the runs
(`eval/thresholds.yaml`, `eval/thresholds/prm-extended.yaml`). Recorded as they came out: the
code was fixed afterwards (commit e492d83), so these are **not** the numbers for the current code.

| Suite | Verdicts | Accuracy | Unsafe passes | Tool-use gate | Other gate |
|---|---|---|---|---|---|
| core (20 specs) | 41/43 (0.95) | 0/43 | passed | goldpass grounding **failed** (0.91 < 0.95) |
| prm-extended (12 specs) | 14/17 (0.82) | 1/17 (0.059 > 0.05) | **failed** (unsafe_pass_rate) | goldpass not run (core only) |

## Why the misses happened (all in extraction; `check` and the verifier behaved as designed)

1. **core g08, g09 and the grounding gate.** The Phase 3 prompt taught `relaxes` for "it is permitted
   to reduce this value". On the internal-step rule the model also marked the demonstration
   exception ("if it can be demonstrated ...") as a relaxation, with no conditions. The rule failed
   validation, so no exception was extracted and the agent escalated: g08 (golden pass) and g09
   (golden fail) were wrong, g03 and g16 were right by luck, and none of the four cited anything.
   A regression I introduced; the earlier runs had 43/43.
2. **prm-extended p10, the one false pass.** "For double deck trains it is permitted to reduce this
   value to 270 mm" is about the minimum depth. The model extracted it as a new maximum for the
   step height, so 210 mm passed. The quote contains 270, "double deck" and "permitted", so every
   check passed. Fixed by requiring a relaxation's verb to agree with its limit (reducing a maximum
   is stricter, not a relaxation).
3. **p07, p08.** The "additional 50 mm on each side adjacent to an obstacle" rule was extracted with
   no condition, so 40 mm and 20 mm failed where the golden verdicts are needs_human and
   not_applicable. Not an unsafe pass. The fix is prompt-only (ask for a condition when a listed
   spec parameter describes the case) and is **unverified until a model run**.

Thresholds were not changed. The renewal, noise and held-out-2 suites had not been run at this
point.

## Second core run (commit a5901a1: the verb-direction check, the clearer rejection message and the
## prompt changes), saved in `v02-second-core/`

Core again 41/43 (0.95), 0 unsafe passes, tool-use gate passed; goldpass grounding failed again
(0.93 < 0.95, three items). g16 was fixed (it now extracts and cites the exception), but g08 and
g09 were still wrong and g03 still cited nothing.

Cause: the rejection message reached the agent, not the model that wrote the rule. The extraction
model is deterministic, so asking again with another focus (g03 asked twice, g08 and g09 once)
produced the same rule. Fixed in b3b09f9: the rejection reason is appended to the extraction
request and the model revises once. Not yet run on a model.

The prm-extended run on a5901a1 stopped on the daily Gemini quota (p09 of 12) and was not scored.
