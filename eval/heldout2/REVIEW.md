# Held-out set 2: verdicts written before any run

Written on 2026-10-30 for the parameters, renewal rules and noise limits added after v0.1.0, **before the agent was run on these specs or on the suites they mirror**. 13 specs, 22 scored verdicts.

| Case | Title | Parameter | Expected | Rule |
|---|---|---|---|---|
| k01 | Handrail and priority seat at the other ends of their ranges | `handrails.outside_diameter_mm` | pass | 30–40 mm |
| k01 | Handrail and priority seat at the other ends of their ranges | `priority_seats.cushion_height_mm` | pass | 430–500 mm |
| k02 | Thin handrail and a turning space just short | `handrails.outside_diameter_mm` | fail | 30–40 mm |
| k02 | Thin handrail and a turning space just short | `wheelchair_space_layout.turning_space_diameter_mm` | fail | ≥ 1500 mm |
| k03 | Double-deck stairs exactly at the relaxed depth | `stairs.step_height_mm` | pass | ≤ 200 mm |
| k03 | Double-deck stairs exactly at the relaxed depth | `stairs.step_depth_mm` | pass | ≥ 270 mm (double deck) |
| k04 | Wheelchair space between two walls | `wheelchair_space_layout.width_mm` | pass | ≥ 700 mm |
| k04 | Wheelchair space between two walls | `wheelchair_space_layout.hand_clearance_mm` | fail | ≥ 50 mm (sides next to an obstacle) |
| k05 | Stair depth 279 mm, deck layout not stated | `stairs.step_depth_mm` | needs_human | ≥ 280 mm, or ≥ 270 mm if double deck |
| k06 | Renewal with new handrails and old stairs | `handrails.outside_diameter_mm` | pass | 30–40 mm |
| k06 | Renewal with new handrails and old stairs | `stairs.step_depth_mm` | not_applicable | — |
| k07 | Renewal that re-lays the whole train but keeps its toilet | `wheelchair_spaces` | pass | ≥ 3 (205 to 300 m row) |
| k07 | Renewal that re-lays the whole train but keeps its toilet | `toilets.universal` | not_applicable | — |
| k08 | Renewal that leaves every vehicle's layout alone | `wheelchair_space_layout.turning_space_diameter_mm` | not_applicable | — |
| k09 | Renewal that re-lays the train with high priority seats | `priority_seats.cushion_height_mm` | needs_human | 430–500 mm, unless it would reduce capacity |
| k10 | DMU at 250 km/h | `noise.stationary_db` | fail | ≤ 72 dB (DMUs) |
| k10 | DMU at 250 km/h | `noise.pass_by_250_db` | pass | ≤ 96 dB (DMUs, 250 km/h) |
| k11 | Diesel locomotive | `noise.stationary_db` | pass | ≤ 71 dB (diesel locomotives) |
| k11 | Diesel locomotive | `noise.pass_by_80_db` | fail | ≤ 85 dB (diesel locomotives) |
| k12 | EMU just below 250 km/h | `noise.cab_max_speed_db` | pass | ≤ 78 dB (vmax < 250 km/h) |
| k12 | EMU just below 250 km/h | `noise.pass_by_250_db` | not_applicable | — |
| k13 | Loud horn, cab not stated | `noise.cab_standstill_horn_db` | needs_human | ≤ 95 dB, for a unit fitted with a cab |
