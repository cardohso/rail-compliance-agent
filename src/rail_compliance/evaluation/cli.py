"""Command line.

uv run python -m rail_compliance.evaluation run                 # all golden specs
uv run python -m rail_compliance.evaluation run --cases g04,g05 # a few
uv run python -m rail_compliance.evaluation gate eval/results/local
uv run python -m rail_compliance.evaluation goldpass-golden     # rewrite goldpass/golden.jsonl
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path

from rail_compliance.config import REPO_ROOT, get_settings
from rail_compliance.evaluation.gate import (
    ThresholdError,
    check_thresholds,
    gate_markdown,
    load_thresholds,
    passed,
)
from rail_compliance.evaluation.goldpass_export import golden_jsonl, records
from rail_compliance.evaluation.metrics import Metrics
from rail_compliance.evaluation.runner import run_cases, save_run
from rail_compliance.factory import build_agent
from rail_compliance.golden import load_golden
from rail_compliance.llm import ConfigError
from rail_compliance.report import Report
from rail_compliance.retry import LLMUnavailable
from rail_compliance.tools.search import SearchError

EVAL = REPO_ROOT / "eval"


def _select(cases, wanted: str | None):
    if not wanted:
        return cases
    ids = {w.strip() for w in wanted.split(",")}
    chosen = [c for c in cases if c.id in ids]
    unknown = ids - {c.id for c in chosen}
    if unknown:
        raise ValueError(f"unknown case ids: {sorted(unknown)}")
    return chosen


def _gate(out: Path, thresholds: Path) -> int:
    payload = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    metrics = Metrics.model_validate(payload["metrics"])
    checks = check_thresholds(metrics, load_thresholds(thresholds))
    print(gate_markdown(checks))
    return 0 if passed(checks) else 1


def main(argv: list[str] | None = None, build: Callable = build_agent) -> int:
    ap = argparse.ArgumentParser(prog="rail_compliance.evaluation", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="run the agent on the golden set and score it")
    run.add_argument("--cases", help="comma-separated case ids (default: all)")
    run.add_argument("--out", type=Path, default=EVAL / "results" / "local")
    run.add_argument("--no-cache", action="store_true", help="ignore and do not write caches")
    run.add_argument("--thresholds", type=Path, default=EVAL / "thresholds.yaml")
    run.add_argument("--gate", action="store_true", help="exit 1 if a threshold fails")
    gate = sub.add_parser("gate", help="check saved results against the thresholds")
    gate.add_argument("results", type=Path)
    gate.add_argument("--thresholds", type=Path, default=EVAL / "thresholds.yaml")
    sub.add_parser("goldpass-golden", help="rewrite eval/goldpass/golden.jsonl from the cases")
    args = ap.parse_args(argv)

    try:
        cases = load_golden()
        if args.cmd == "goldpass-golden":
            (EVAL / "goldpass" / "golden.jsonl").write_text(golden_jsonl(cases), encoding="utf-8")
            print(f"wrote {EVAL / 'goldpass' / 'golden.jsonl'}")
            return 0
        if args.cmd == "gate":
            return _gate(args.results, args.thresholds)

        cases = _select(cases, args.cases)
        agent = build(get_settings(), use_cache=not args.no_cache)
        result = run_cases(cases, agent, progress=print)
        first: Report | None = next((r for r in result.reports.values() if r), None)
        meta = {
            "model": first.stats.agent_model if first else None,
            "search": first.stats.search_backend if first else None,
            "cases": [c.id for c in cases],
        }
        _, _, checks = save_run(args.out, cases, result, meta, load_thresholds(args.thresholds))
        system = f"{meta['model']} via rail_compliance ({meta['search']} search)"
        gp = args.out / "goldpass"
        gp.mkdir(parents=True, exist_ok=True)
        (gp / "records.json").write_text(
            json.dumps(records(cases, result.reports, result.errors, system), indent=1), "utf-8"
        )
        print((args.out / "summary.md").read_text(encoding="utf-8"))
        return 0 if (passed(checks) or not args.gate) else 1
    except LLMUnavailable as exc:
        print(f"error: {exc}")
        print(
            "The provider is out of quota or unavailable. Nothing was scored. Every call that did "
            "succeed is cached, so run the same command again later (or with another API key) and "
            "it resumes where it stopped without repeating them."
        )
        return 2
    except (ValueError, ThresholdError, ConfigError, SearchError) as exc:
        print(f"error: {exc}")
        return 2
