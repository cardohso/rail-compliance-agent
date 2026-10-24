# rail-compliance-agent

[![ci](https://github.com/cardohso/rail-compliance-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/cardohso/rail-compliance-agent/actions/workflows/ci.yml)

A tool-using agent that checks a train design spec (JSON) against the EU PRM TSI
(Regulation (EU) No 1300/2014), using
[rail-regulation-rag](https://github.com/cardohso/rail-regulation-rag) as its regulation search
tool, and evaluated on its tool use, not only on its final verdicts.

**Status: work in progress.** The tools, agent and report are built and tested offline; the evaluation, API and MCP server are not built yet.

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

## The tools

Four plain functions with typed inputs and outputs, in [`src/rail_compliance/tools/`](src/rail_compliance/tools):

| Tool | What it does | LLM? |
|---|---|---|
| `search_regulation(question)` | passages of EU rail law that answer the question, with EUR-Lex links | no (local) / the assistant's own (live) |
| `extract_requirement(passages, parameter)` | the numeric rule as a typed `Requirement` (value or table, unit, conditions) | yes, then verified without it |
| `check(spec_value, requirement)` | `pass` / `fail` / `needs_human` / `not_applicable`, exact comparison | no |
| `needs_human(reason)` | records an escalation (ambiguous law, missing data, weak citation) | no |

**Extraction is checked, not trusted.** The model must quote the rule word for word; the tool then
confirms the quote is in the cited passage and that every number in the rule (limit, table bounds,
condition thresholds) appears in the quote. A rule that fails is returned as `unverified`, so an
invented number cannot reach `check`.

**`check` settles boundaries exactly** (a table row "30 to 205 metres" includes both ends; "more
than 205" excludes 205; metres convert to millimetres without float error) and never guesses:
missing data, an unconvertible unit, or a table with a gap or overlap is `needs_human`.

**`search_regulation` has three backends** behind one interface:

- `local` (default, used for evaluation): the rail assistant's own retrieval run in-process
  (hybrid BM25 + vector search over the same index), no LLM and no network, so evaluation does not
  spend the live demo's quota. `rail-regulation-rag` is a pinned git dependency (`local` group).
- `live`: the deployed `POST /ask`, with retry and backoff for its rate limit.
- `replay`: recorded results from a file, for offline tests.

A disk cache wraps any backend.

## The agent

A LangGraph loop in [`agent.py`](src/rail_compliance/agent.py). For each parameter the spec
supplies, the model chooses among the four tools; a parameter the spec omits is `needs_human`
without a search. Three rules keep the model away from numbers it could get wrong:

- It passes passage **ids** and a **requirement id**, not text. The runtime resolves them.
- A `check` call whose `spec_value` differs from the spec is **rejected** (and recorded, so the
  evaluation can score argument correctness). The verdict never uses a wrong value.
- The parameter's verdict is **computed by code** from the checks that ran, never written by the
  model: if the model escalated with `needs_human`, that stands (its doubt is not overruled; failed
  checks stay in the report); otherwise `fail` beats a check that needed a person, which beats
  `pass`. A tool-call budget per parameter stops loops, and ending with no check or escalation is
  itself `needs_human`.
- Every extracted rule is labelled with the **subject** it is stated for (for example "all exterior
  doorways" or "wheelchair doorways"). A parameter is governed by rules for its own subject and for
  broader ones, never narrower ones, and the extraction tool rejects the rest.
- A rule that holds only "if it can be demonstrated ..." is recorded with a **contingency**: an
  exception that would allow a value the general rule rejects makes the parameter `needs_human`.
- A **qualifier** such as `length_includes_power_head` is not a rule condition: it makes the unit
  length an interval (at most the stated value), and `check` decides tables and conditions over
  that whole interval.

The report ([`report.py`](src/rail_compliance/report.py)) has, per parameter, the verdict, the
requirement, the spec value and citations (document, section, EUR-Lex link, the exact quote), as
JSON and Markdown, plus the tool-call trace the evaluation scores. Verdicts are `pass`, `fail`,
`needs_human`, and `not_applicable` for a rule whose conditions are false for this spec (for
example a toilet rule on a train with no toilets).

Setup and run (needs a free Gemini API key; `.env` is git-ignored):

```bash
cp .env.example .env            # then put your GEMINI_API_KEY in .env yourself
uv sync --group local           # the rail assistant's retrieval, used by the local backend
uv run python -m rail_compliance check examples/02_noncompliant_regional.json
```

Model replies and search results are cached on disk (`eval/.cache/`), so a re-run costs no quota.

## Evaluation

The point of the project: the agent is scored on **how it used its tools**, not only on its final
text. The golden set is 20 specs and 43 scored verdicts written from the TSI text
([review notes and limits](eval/GOLDEN_SET_REVIEW.md)). Metrics, all deterministic (no model
judges anything), each with its numerator, denominator and a 95% Wilson interval:

| Metric | Meaning |
|---|---|
| `verdict_accuracy` | agent verdict equals the golden verdict |
| `unsafe_pass_rate` | agent says `pass` where the golden verdict is `fail` or `needs_human` |
| `needs_human_recall` / `_precision` | share of expected escalations it made / share of its escalations that were expected |
| `tool_selection_accuracy` | the expected tools were called, in order (search, extract, then check or needs_human) |
| `argument_correctness` | `check` was called with the right parameter and the spec's own value |
| `citation_hit_rate` | a cited passage is the gold passage that holds the rule |
| `tool_calls_per_parameter`, latency | cost; latency excludes the rate-limit waits and replays cached calls' original time |

Retrieval, citation and grounding are also run through [goldpass](https://github.com/cardohso/goldpass)
(recall@k, hit rate, grounding, its report and gate). The tool-use metrics live in this repo because
goldpass has no notion of tool calls.

[`eval/thresholds.yaml`](eval/thresholds.yaml) was written **before the first full run** and is not
tuned to it; its history is the record. `eval.yml` runs the set on pull requests and by hand and fails
the build below those numbers.

```bash
uv sync --group local --group eval
uv run python -m rail_compliance.evaluation run                  # all 20; ~20 min the first time
uv run python -m rail_compliance.evaluation run --cases g04,g05  # a few
uv run python -m rail_compliance.evaluation gate eval/results/local
uv run goldpass run --config eval/goldpass/goldpass.yaml
```

**Results:** none yet. They go here from a real run, with nothing rounded up.

## Development

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv run pytest
```

Tests are offline. One integration test runs the real local retrieval; it is skipped unless the
`local` group is installed and `RAIL_RAG_DATA_DIR` points at a rail-regulation-rag `data/` folder
with a built index:

```bash
uv sync --group local
uv run pytest tests/test_local_integration.py
```

## Licence

MIT
