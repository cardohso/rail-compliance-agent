# Held-out set 2 (k01-k13), run once on 12f6550

Run once, after all fixes, with the thresholds in `eval/heldout2/thresholds.yaml` written
before the run. No prompt or code change was made in response to this result.

| Metric | Result | Threshold |
|---|---|---|
| verdict accuracy | 17/22 = 0.77 (Wilson 0.57-0.90) | >= 0.70, passed |
| unsafe pass rate | 0/22 (0.00-0.15) | <= 0.05, passed |
| tool selection | 22/22 | >= 0.75, passed |
| argument correctness | 29/29 | >= 0.95, passed |
| citation hit rate | 0.91 | >= 0.80, passed |
| needs_human precision / recall | 2/3 / 2/3 | >= 0.5 / >= 0.33, passed |

Gate passed. The interval is wide (22 verdicts): the lower bound 0.57 is below the threshold.

## The five wrong verdicts
Four are renewed units where an Appendix F exemption was missed or not extracted, the same
family as the dev-suite misses r05, r07 and r08:
- k06 stairs.step_depth_mm: expected not_applicable, got fail (250 mm vs 280 mm).
- k08 turning_space_diameter_mm: expected not_applicable, got fail (1200 mm vs 1500 mm).
- k07 toilets.universal: expected not_applicable, got needs_human (exemption conditional on
  "without structural alteration", which the spec cannot show). Safe direction.
- k09 priority_seats.cushion_height_mm: expected needs_human, got fail (520 mm outside
  430-500 mm) on a renewed unit.
One is a noise case:
- k12 noise.pass_by_250_db: 249 km/h unit, expected not_applicable (the 250 km/h limit
  applies from 250 km/h up), got fail (99 dB vs 95 dB): the speed condition was dropped.

None is an unsafe pass. Two (k06, k08) are false fails, which cost a person a needless
review; they are not missed violations.
