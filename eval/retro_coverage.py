"""What would the coverage check have done to verdicts already produced? No model calls.

For every saved report it rebuilds, from the trace, which rule values the agent extracted (the
`extract_requirement` results) and from which passages (the report's citations), applies the check
against the real corpus text, and compares the verdict it would have given with the golden one.
Approximation: a rule the agent extracted but never checked still appears in the trace, but only
its first 300 characters of summary are kept.

    uv run python eval/retro_coverage.py eval/results/local/reports ...   (with the `local` group)
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

from rail_compliance.config import get_settings
from rail_compliance.golden import load_golden
from rail_compliance.models import Passage
from rail_compliance.tools.coverage import find_gaps

VALUE = re.compile(r"spec value ([≥≤=<>]+) ([\d.]+) mm")
SYMBOL = {"≥": ">=", "≤": "<="}


def corpus() -> dict[str, Passage]:
    data = get_settings().rail_rag_data_dir
    os.environ.setdefault("RAIL_RAG_DATA_DIR", str(data))
    from rail_rag.chunking import load_passages

    return {
        p.id: Passage(
            id=p.id, doc_id=p.doc_id, document=p.doc_short, section=p.section, text=p.text
        )
        for p in load_passages(data / "processed")
    }


def replay(reports_dir: Path, cases, passages) -> list[dict]:
    rows = []
    by_id = {c.id: c for c in cases}
    for path in sorted(reports_dir.glob("*.json")):
        case = by_id.get(path.stem)
        if case is None:
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        for parameter, expected in case.expected.items():
            result = next(r for r in report["results"] if r["parameter"] == parameter)
            found = [
                (SYMBOL.get(m.group(1), m.group(1)), float(m.group(2)))
                for t in report["trace"]
                if t["parameter"] == parameter and t["name"] == "extract_requirement"
                for m in [VALUE.search(t["summary"])]
                if m
            ]
            cited = {c["passage_id"] for c in result["citations"]}
            rules = [
                SimpleNamespace(
                    value=v, bands=[], comparator=cmp, citation=SimpleNamespace(passage_id=pid)
                )
                for cmp, v in found
                for pid in cited
            ]
            spec_value = result["spec_value"]
            gaps = find_gaps(parameter, passages, rules, spec_value=spec_value) if rules else []
            old = result["verdict"]
            explicit = any(r["category"] != "other" for r in result["reviews"])
            new = (
                "needs_human"
                if gaps and old in ("pass", "not_applicable") and not explicit
                else old
            )
            rows.append(
                dict(case=case.id, parameter=parameter, golden=expected.verdict, old=old,
                     new=new, gaps=[g.sentence[:70] for g in gaps])
            )  # fmt: skip
    return rows


def main(dirs: list[str]) -> None:
    cases = load_golden() + load_golden(Path(__file__).parent / "heldout", "h*.json")
    passages = corpus()
    total = flips = caught = hurt = 0
    for d in dirs:
        rows = replay(Path(d), cases, passages)
        n_flip = [r for r in rows if r["new"] != r["old"]]
        print(f"\n{d}: {len(rows)} verdicts, {len(n_flip)} would change")
        for r in n_flip:
            good = r["golden"] == "needs_human"
            tag = "CATCH (was a wrong pass)" if good else "FALSE ALARM (golden " + r["golden"] + ")"
            print(
                f"   {r['case']} {r['parameter'].split('.')[-1]}: {r['old']} -> {r['new']}  {tag}"
            )
            print(f"      gap: {r['gaps'][0]}")
        total += len(rows)
        flips += len(n_flip)
        caught += sum(r["golden"] == "needs_human" for r in n_flip)
        hurt += sum(r["golden"] != "needs_human" for r in n_flip)
    print(
        f"\nTOTAL {total} verdicts: {flips} change; {caught} catch a wrong pass; "
        f"{hurt} are false alarms"
    )


if __name__ == "__main__":
    main(sys.argv[1:])
