# rail-compliance-agent

[![ci](https://github.com/cardohso/rail-compliance-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/cardohso/rail-compliance-agent/actions/workflows/ci.yml)

A tool-using agent that checks a train design spec (JSON) against the EU PRM TSI
(Regulation (EU) No 1300/2014), using
[rail-regulation-rag](https://github.com/cardohso/rail-regulation-rag) as its regulation search
tool, and evaluated on its tool use, not only on its final verdicts.

**Status: work in progress.** Nothing here is usable yet.

> Not legal advice. Reports are an engineering aid; conformity is assessed by a notified body.

## The input: a train spec

A JSON file, validated by [`rail_compliance.spec`](src/rail_compliance/spec.py) (Pydantic; the
JSON Schema is committed at [`schema/train-spec.schema.json`](schema/train-spec.schema.json)).
Scope is the PRM TSI rolling-stock rules (point 4.2.2):

| Field | Unit | Rule it feeds |
|---|---|---|
| `unit_length_m` (required) | m, excluding any power head | wheelchair spaces per unit length (Table 5) |
| `length_includes_power_head` | bool | if true, the length is not on the TSI's basis |
| `design_speed_kmh` | km/h | wheelchair door width (below 250 km/h) |
| `wheelchair_spaces` | count | 4.2.2.2 |
| `exterior_doors.clear_width_mm`, `.wheelchair_door_clear_width_mm`, `.wheelchair_door_level_access` | mm, bool | 4.2.2.3.2 |
| `steps.external_step_height_mm`, `.internal_step_height_mm` | mm | 4.2.2.11.2 |
| `toilets.fitted`, `.universal`, `.universal_door_clear_width_mm` | count, mm | 4.2.2.5, 5.3.2.4 |

Everything except `name` and `unit_length_m` is optional. A missing parameter is not a failure:
the agent cannot check it and reports `needs_human`. Unknown fields are rejected, so a typo cannot
silently drop a parameter. [`examples/`](examples) has three specs: one compliant, one with
several violations, one with missing and ambiguous data.

```bash
uv run python -m rail_compliance.spec validate examples/*.json
```

## Development

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv run pytest
```

## Licence

MIT
