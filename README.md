# rail-compliance-agent

[![ci](https://github.com/cardohso/rail-compliance-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/cardohso/rail-compliance-agent/actions/workflows/ci.yml)

A tool-using agent that checks a train design spec (JSON) against the EU PRM TSI
(Regulation (EU) No 1300/2014), using
[rail-regulation-rag](https://github.com/cardohso/rail-regulation-rag) as its regulation search
tool, and evaluated on its tool use, not only on its final verdicts.

**Status: work in progress.** Nothing here is usable yet.

> Not legal advice. Reports are an engineering aid; conformity is assessed by a notified body.

## Development

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv run pytest
```

## Licence

MIT
