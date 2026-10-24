"""Feed goldpass (github.com/cardohso/goldpass) with what the agent retrieved and cited.

One goldpass item per scored parameter. goldpass then scores retrieval (was the passage holding
the rule among those the agent retrieved?) and grounding (does every cited document belong to
the PRM TSI?), and renders its report and gate. Escalation is NOT mapped onto goldpass's
"refuse": goldpass requires refuse items to have no gold passages, and a needs_human case still
has a rule to find. So every item is `answer` here and refusals are not reported.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from rail_compliance.golden import GoldenCase
from rail_compliance.report import Report

SOURCE_DOCS = ["tsi-prm"]


def item_id(case: str, parameter: str) -> str:
    return f"{case}:{parameter}"


def _doc(passage_id: str) -> str:
    return passage_id.split(":", 1)[0]  # ids are "<doc_id>:<section>#<n>"


def golden_jsonl(cases: Sequence[GoldenCase]) -> str:
    lines = []
    for case in cases:
        for parameter, expected in case.expected.items():
            lines.append(
                json.dumps(
                    {
                        "id": item_id(case.id, parameter),
                        "question": f"Is {parameter} compliant in '{case.spec.name}'?",
                        "expected": "answer",
                        "gold_passage_ids": expected.gold_passages,
                        "source_doc_ids": SOURCE_DOCS,
                        "tags": case.tags,
                    },
                    ensure_ascii=False,
                )
            )
    return "\n".join(lines) + "\n"


def records(
    cases: Sequence[GoldenCase],
    reports: Mapping[str, Report | None],
    errors: Mapping[str, str],
    system: str,
) -> dict:
    rows = []
    for case in cases:
        report = reports.get(case.id)
        for parameter in case.expected:
            rid = item_id(case.id, parameter)
            if report is None:
                rows.append({"id": rid, "error": errors.get(case.id, "the run crashed")})
                continue
            result = report.result_for(parameter)
            rows.append(
                {
                    "id": rid,
                    "answer": result.reason,
                    "contexts": [{"id": p, "doc_id": _doc(p)} for p in result.consulted],
                    "citations": [
                        {"passage_id": c.passage_id, "doc_id": c.doc_id} for c in result.citations
                    ],
                }
            )
    return {"system": system, "records": rows}
