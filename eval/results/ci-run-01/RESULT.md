# First full `eval.yml` run on GitHub (2026-10-25)

Run [`40175097116`](https://github.com/cardohso/rail-compliance-agent/actions/runs/40175097116), manual
dispatch with no `cases` filter, head `4004338`, started 08:02, finished about 08:20 local time.
Same code and model (`gemini-3.5-flash-lite`) as local run 02; the only differences are a different
machine, a runner cache that held only g04 and g05, and the model's own sampling. Thresholds
unchanged. **The job failed: the goldpass gate failed on grounding.** Every other step succeeded
(checkout, corpus, `uv sync`, index build, model run, cache save, my own gate, artifact upload).

| Metric | CI run | Local run 02 | Required |
|---|---|---|---|
| `verdict_accuracy` | **0.930 (40/43)** | 1.000 (43/43) | ≥ 0.80 |
| `unsafe_pass_rate` | 0.000 (0/43) | 0.000 (0/43) | ≤ 0.05 |
| `needs_human_recall` | 1.000 (5/5) | 1.000 (5/5) | ≥ 0.40 |
| `needs_human_precision` | 0.625 (5/8) | 1.000 (5/5) | ≥ 0.60 |
| `tool_selection_accuracy` | 0.930 (40/43) | 1.000 (43/43) | ≥ 0.80 |
| `argument_correctness` | 1.000 (55/55) | 1.000 (56/56) | ≥ 0.95 |
| `citation_hit_rate` | 1.000 (40/40) | 1.000 (43/43) | ≥ 0.90 |
| goldpass `grounding` | **0.930 (40/43)** | 1.000 (43/43) | ≥ 0.95 |
| goldpass `recall@k` / `hit@k` | 1.000 / 1.000 | 1.000 / 1.000 | ≥ 0.85 / 0.90 |

My own quality gate **passed** (it just clears the escalation-precision floor: 0.625 against 0.60);
the goldpass gate **failed** on grounding: 0.930 against 0.95.

## The three differences, and why

All three are the same parameter, `toilets.universal`, in the three specs that also supply toilet
data alongside many other parameters: g01 (golden `pass`), g02 (`fail`), g08 (`pass`). In each the
agent answered `needs_human` after one extraction and no `check`:

- It called `extract_requirement` **with no `focus`**, and the extraction model replied "found:
  false: the passages state that a universal toilet shall be provided when toilets are fitted, but do
  not specify a numeric requirement". It did not read "a universal toilet shall be provided" as a rule
  meaning "at least one".
- In g09 and g18 the agent did pass the rule's sentence as `focus`, and extraction found it.
- That wording is handled in the **verifier** (an "a/an ... shall be provided" quote counts as at
  least one) but **not in the extraction prompt**, so whether it works depends on how the agent
  happens to phrase the call. A real prompt gap, exposed by sampling.

Those three items have no citation, which is why goldpass counts them as ungrounded: a verdict of
`needs_human` reached without any checked rule cites nothing. Whether an escalation without a check
should count against grounding is a metric-design question I have not decided.

## What this changes in how to read the other results

- **Run-to-run variance is now measured, once:** same code, same model, 43/43 locally and 40/43 here,
  with every difference traced to one extraction outcome. The local 43/43 and the held-out 18/19 are
  each a single draw and were, at least in part, a favourable one.
- Not fixed yet, on purpose: the fix (tell the extractor that "shall be provided" states a minimum of
  one) would change every extraction prompt and so invalidate the caches behind the earlier runs.
