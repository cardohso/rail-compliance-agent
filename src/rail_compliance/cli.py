"""Command line: check a spec file and write the JSON and Markdown report.

uv run python -m rail_compliance check examples/02_noncompliant_regional.json
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from rail_compliance.config import get_settings
from rail_compliance.factory import build_agent
from rail_compliance.llm import ConfigError
from rail_compliance.report import to_markdown
from rail_compliance.retry import LLMUnavailable
from rail_compliance.spec import load_spec
from rail_compliance.tools.search import SearchError


def main(argv: list[str] | None = None, build: Callable = build_agent) -> int:
    ap = argparse.ArgumentParser(prog="rail_compliance", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    chk = sub.add_parser("check", help="check a train spec against the PRM TSI")
    chk.add_argument("spec", type=Path)
    chk.add_argument("--out", type=Path, default=Path("reports"), help="report folder")
    chk.add_argument(
        "--backend", choices=["local", "live", "replay"], help="override SEARCH_BACKEND"
    )
    chk.add_argument("--replay", type=Path, help="recorded results file, for --backend replay")
    chk.add_argument("--no-cache", action="store_true", help="ignore and do not write the caches")
    args = ap.parse_args(argv)

    try:
        spec = load_spec(args.spec)
        settings = get_settings()
        if args.backend:
            settings = settings.model_copy(update={"search_backend": args.backend})
        agent = build(settings, use_cache=not args.no_cache, replay_file=args.replay)
        report = agent.run(spec)
    except (ValueError, ConfigError, SearchError, LLMUnavailable) as exc:
        print(f"error: {exc}")
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f"{args.spec.stem}.json").write_text(report.model_dump_json(indent=2), "utf-8")
    (args.out / f"{args.spec.stem}.md").write_text(to_markdown(report), "utf-8")
    for r in report.results:
        print(f"{r.verdict:<14} {r.parameter:<48} {r.requirement or ''}")
    s = report.stats
    print(f"{s.tool_calls} tool calls, {s.llm_calls} model calls, {s.seconds:.1f} s")
    print(f"report: {args.out / (args.spec.stem + '.md')}")
    return 0
