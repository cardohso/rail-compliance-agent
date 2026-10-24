# rail-compliance-agent

[![ci](https://github.com/cardohso/rail-compliance-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/cardohso/rail-compliance-agent/actions/workflows/ci.yml)

A tool-using agent that checks a train design spec (JSON) against the EU PRM TSI
(Regulation (EU) No 1300/2014), using
[rail-regulation-rag](https://github.com/cardohso/rail-regulation-rag) as its regulation search
tool, and evaluated on its tool use, not only on its final verdicts.

**Status: work in progress.** The tools, agent, report, evaluation harness, API and MCP server are built and tested offline. The first full evaluation failed its gate, the fixes pass it on the same set (see Evaluation); the Docker image is written but not yet built.

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

**Cost.** A fresh full run makes about 245 model requests (measured as the cache entries a full run leaves;
retries after rate-limit errors may add a few). Gemini's free tier allows 500 requests per day per
Google project for this model and 15 per minute, so about one fresh full run a day fits, and the
CI workflow draws on the same key's quota. Every successful call is cached by its full prompt, so
a run that stops on the quota resumes where it stopped (re-run the same command), and a re-run
of unchanged code costs nothing. This happened during development: see
[`eval/results/run-02-partial`](eval/results/run-02-partial/NOTE.md).

**Results** (Gemini `gemini-3.5-flash-lite`, 20 specs, 43 verdicts; full tables and caveats in
[`eval/results/run-02/RESULT.md`](eval/results/run-02/RESULT.md)):

| | Run 01 (first run) | Run 02 (after fixes) | Required |
|---|---|---|---|
| verdict accuracy | 34/43 = 0.79 | 43/43 = 1.00 | ≥ 0.80 |
| false passes (said pass, golden fail or needs_human) | 0/43 | 0/43 | ≤ 0.05 |
| escalation recall / precision | 3/5 / 3/9 | 5/5 / 5/5 | ≥ 0.40 / ≥ 0.60 |
| tool selection / argument correctness / citation hit | 43/43 / 59/59 / 43/43 | 43/43 / 56/56 / 43/43 | ≥ 0.80 / 0.95 / 0.90 |
| quality gate | **failed** (4 checks) | passed | |

Run 01 failed the gate and its nine misses are diagnosed in
[`eval/results/run-01/DIAGNOSIS.md`](eval/results/run-01/DIAGNOSIS.md). The fixes were designed after
reading those misses on this same set, so run 02 is a **development-set result**, not a measure of how
the agent does on new specs. One run each; the model's sampling cannot be fixed, so a fresh run can
differ.

## API

```bash
uv run uvicorn rail_compliance.api:create_app --factory --port 8000
```

`GET /health` always answers while the process is up; `ready` says whether `/check` can run (it
needs a model key and the rail assistant's index). `POST /check` takes a spec and returns the
report (`?format=markdown` for the Markdown version). It is rate-limited per client (2 a minute,
20 a day by default), because one check can use ~30 of the free tier's 500 daily model requests.
Real responses (the model calls behind the last one were replayed from the cache of an earlier
run, which is why it needed no quota):

```console
$ curl -s localhost:8000/health
{"status":"ok","version":"0.1.0","ready":true,"reason":null,"search_backend":"local","agent_provider":"gemini"}

$ curl -s -X POST localhost:8000/check -H 'content-type: application/json' \
    -d '{"name":"x","unit_length_m":30,"wheelchair_space":1}'      # typo: wheelchair_space
{"detail":[{"type":"extra_forbidden","loc":["body","wheelchair_space"],"msg":"Extra inputs are not permitted","input":1}]}

$ curl -s -X POST 'localhost:8000/check?format=markdown' -H 'content-type: application/json' \
    -d '{"name":"Length exactly 30 m with one wheelchair space","unit_length_m":30.0,"wheelchair_spaces":1}'
# Compliance report: Length exactly 30 m with one wheelchair space
**Summary:** 1 fail, 6 needs human
| `wheelchair_spaces` | 1 | ≥ 2 | **fail** |
| `exterior_doors.clear_width_mm` | not supplied | - | **needs human** |
...
> Table 5 Minimum number of wheelchair spaces per unit length ... Less than 30 m | 1 wheelchair
> space 30 to 205 metres | 2 wheelchair spaces ...
```

## MCP server

The four tools (`search_regulation`, `extract_requirement`, `check`, `needs_human`) and a
`rail://parameters` resource, for any MCP client over stdio. `check` and `needs_human` need nothing;
`search_regulation` needs the rail assistant (`uv sync --group local` and its index, or
`SEARCH_BACKEND=live`); `extract_requirement` needs a model key. Missing pieces come back as a
readable tool error naming the fix, not a crash.

```bash
claude mcp add rail-compliance -- uv run --directory /path/to/rail-compliance-agent python -m rail_compliance.mcp_server
```

Claude Desktop (`claude_desktop_config.json`), same command:

```json
{"mcpServers": {"rail-compliance": {"command": "uv",
  "args": ["run", "--directory", "/path/to/rail-compliance-agent", "python", "-m", "rail_compliance.mcp_server"]}}}
```

What a client sees, from [`examples/mcp_client_demo.py`](examples/mcp_client_demo.py), which starts
the server as a subprocess and talks MCP over stdio (real output). The two registration commands
above are the standard ones for those clients; I tested the server with the Python MCP client only,
not with Claude Desktop or Claude Code themselves:

```console
$ uv run python examples/mcp_client_demo.py
tools: search_regulation, extract_requirement, check, needs_human
check(780 mm): fail, 780 mm violates >= 800 mm
check(800 mm): pass, 800 mm meets >= 800 mm
needs_human: {"parameter": null, "category": "weak_citation", "reason": "The rule points to an external standard."}
rail://parameters: 7 parameters, first: wheelchair_spaces
```

## Docker

```bash
docker build -t rail-compliance-agent .
docker run --rm -p 8000:8000 --env-file .env rail-compliance-agent
```

The image holds the rail assistant's corpus at a pinned commit with its vector index built at
build time (so search needs no network), runs as a non-root user (uid 1000) and has a `HEALTHCHECK`.
The model key is passed at run time, never baked in. **Not yet built or run by me:** there is no
Docker on my development machine. The `docker` workflow builds the image on GitHub and probes it
(non-root, `/health` ready, a spec settled without a model call, a search over the baked-in index,
Docker's own health status); it has not run yet either, so treat this section as unverified until it
has. Static tests in `tests/test_docker_files.py` guard the properties that can be checked without
building (non-root user, healthcheck, no secrets, the same corpus commit in every place it is pinned).

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
