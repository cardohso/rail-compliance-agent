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

## Third round (commit a959557: the extractor sees its rejection and revises once)

Runs on 2026-11-01, thresholds unchanged. Folders: `v02-core-a959557`, `v02-prm-extended-a959557`,
`v02-renewal-first-run`, `v02-noise-first-run`.

| Suite | Verdicts | Accuracy | Unsafe passes | Gate |
|---|---|---|---|---|
| core | 42/43 (0.98) | 0/43 | passed; goldpass grounding passed (0.98) | **passed** |
| prm-extended | 17/17 | 0/17 | | **passed** |
| renewal (first run) | 4/11 (0.36) | 0/11 | accuracy, escalation recall and precision below floor | **failed** |
| noise (first run) | 14/18 (0.78) | 0/18 | accuracy 0.78 < 0.80, everything else passed | **failed** |

**Read the first two with care.** core and prm-extended were the suites whose misses I used to
design the fixes, so 42/43 and 17/17 show the fixes work on the cases that motivated them, not
that the agent would score that on new specs. Core's remaining miss is g08 (golden pass,
agent needs_human): the model's second extraction of the exception was rejected again and the
agent escalated without checking the rule it already had (200 mm meets 200 mm). Safe direction.

### Renewal, 4/11: seven causes (none an unsafe pass)
- r03, r10 (and r05's external step): the agent never searched Appendix F although the task said
  to. r03 and r10 were fails where the goldens are needs_human.
- r04: the exemption could not be decided and the agent escalated a value that passes either way.
- r06, r08: the exemption was encoded as a limit and rejected with messages that did not say what
  an exemption is.
- r07: only the first of the two exemption sentences was extracted; the doorway one was not.

### Noise, 14/18: four causes
- n04: "Noise TSI is outside the PRM TSI scope handled by this tool set" (the agent prompt named only
  the PRM TSI).
- n08: the agent escalated for a missing category before the check, which would have settled it.
- n07: the cab limit was extracted without the cab condition, because "fitted with a cab" is in
  the sentence before the table, not in the row quoted.
- n06: **debatable, not a clear error.** The 250 km/h pass-by limit applies "if applicable"; I read
  that as design speed >= 250 km/h. The model checked a 200 km/h unit's 250 km/h figure against 95 dB.

### Fixes after this round (commits dc2b35f and later; not yet run on a model)
The runtime now fetches Appendix F for renewed units (two searches, chosen by checking offline that
they retrieve the gold exemption passage for all 14 parameters, so **fitted to the dev suite**);
exemption rejection messages say what an exemption is; an undecidable exemption is no verdict on
its own; the agent prompt names both regulations, defers missing-data escalation to the check, and
the extraction prompt asks for the sentence that introduces a table. n06 is left as it is.
