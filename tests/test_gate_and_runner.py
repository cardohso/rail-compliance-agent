import json
from pathlib import Path

import pytest
import yaml

from rail_compliance.evaluation import cli
from rail_compliance.evaluation.gate import (
    ThresholdError,
    check_thresholds,
    gate_markdown,
    load_thresholds,
    passed,
)
from rail_compliance.evaluation.goldpass_export import golden_jsonl, item_id, records
from rail_compliance.evaluation.metrics import compute_metrics
from rail_compliance.evaluation.runner import run_cases
from rail_compliance.golden import load_golden
from rail_compliance.retry import LLMUnavailable
from tests.eval_helpers import CASES, perfect, report_for

ROOT = Path(__file__).resolve().parents[1]
SPACES = "wheelchair_spaces"


def perfect_metrics(ids=("g04", "g05", "g16", "g17")):
    return compute_metrics([CASES[i] for i in ids], perfect(ids))


def test_the_committed_thresholds_only_name_real_metrics_and_a_perfect_run_passes_them():
    thresholds = load_thresholds(ROOT / "eval" / "thresholds.yaml")
    metrics = compute_metrics(list(CASES.values()), perfect(CASES))
    checks = check_thresholds(metrics, thresholds)
    assert checks and passed(checks), gate_markdown(checks)


def test_a_threshold_is_enforced_in_both_directions():
    m = perfect_metrics()
    assert passed(check_thresholds(m, {"metrics": {"verdict_accuracy": {"min": 1.0}}}))
    assert not passed(check_thresholds(m, {"metrics": {"verdict_accuracy": {"min": 1.01}}}))
    assert passed(check_thresholds(m, {"metrics": {"unsafe_pass_rate": {"max": 0.0}}}))
    bad = compute_metrics([CASES["g04"]], {"g04": report_for("g04", verdicts={SPACES: "pass"})})
    assert not passed(check_thresholds(bad, {"metrics": {"unsafe_pass_rate": {"max": 0.5}}}))


def test_equality_with_the_limit_passes():
    m = perfect_metrics()
    assert passed(check_thresholds(m, {"metrics": {"verdict_accuracy": {"min": 1.0}}}))
    assert passed(check_thresholds(m, {"metrics": {"unsafe_pass_rate": {"max": 0.0}}}))


def test_a_metric_with_no_value_fails_instead_of_passing_silently():
    m = compute_metrics([CASES["g04"]], perfect(["g04"]))  # nobody expected or gave needs_human
    checks = check_thresholds(m, {"metrics": {"needs_human_precision": {"min": 0.1}}})
    assert not passed(checks)
    assert "no value" in checks[0].message


def test_tag_slices_are_gated():
    ids = ["g04", "g05"]
    reports = perfect(ids)
    reports["g04"] = report_for("g04", verdicts={SPACES: "pass"})
    m = compute_metrics([CASES[i] for i in ids], reports)
    checks = check_thresholds(m, {"tags": {"table-boundary": {"verdict_accuracy": {"min": 0.9}}}})
    assert not passed(checks) and checks[0].scope == "tag:table-boundary"
    missing = check_thresholds(m, {"tags": {"no-such-tag": {"verdict_accuracy": {"min": 0.1}}}})
    assert not passed(missing)


def test_errors_and_tool_calls_thresholds():
    m = compute_metrics([CASES["g04"], CASES["g05"]], {"g04": report_for("g04"), "g05": None})
    assert not passed(check_thresholds(m, {"metrics": {"errors": {"max": 0}}}))
    assert passed(check_thresholds(m, {"metrics": {"tool_calls_per_parameter": {"max": 3.0}}}))


@pytest.mark.parametrize(
    "bad",
    [
        {"metrics": {"vibes": {"min": 1}}},
        {"metrics": {"verdict_accuracy": {"minimum": 1}}},
        {"metrics": {"verdict_accuracy": {}}},
        {"tags": {"exact-limit": {"tool_calls_per_parameter": {"max": 3}}}},
    ],
)
def test_malformed_thresholds_are_rejected_with_a_message(bad):
    with pytest.raises(ThresholdError):
        check_thresholds(perfect_metrics(), bad)


def test_unknown_top_level_key_is_rejected(tmp_path):
    path = tmp_path / "t.yaml"
    path.write_text(yaml.safe_dump({"metric": {}}), encoding="utf-8")
    with pytest.raises(ThresholdError, match="metric"):
        load_thresholds(path)


def test_gate_markdown_names_the_failure():
    checks = check_thresholds(perfect_metrics(), {"metrics": {"verdict_accuracy": {"min": 1.01}}})
    text = gate_markdown(checks)
    assert "FAILED" in text and "1.000 < 1.01" in text


# --- goldpass export ----------------------------------------------------------------------------


def test_goldpass_golden_has_one_valid_item_per_scored_parameter():
    cases = load_golden()
    rows = [json.loads(line) for line in golden_jsonl(cases).splitlines()]
    assert len(rows) == sum(len(c.expected) for c in cases)
    assert len({r["id"] for r in rows}) == len(rows)
    for r in rows:
        assert set(r) == {
            "id",
            "question",
            "expected",
            "gold_passage_ids",
            "source_doc_ids",
            "tags",
        }
        assert r["expected"] == "answer" and r["gold_passage_ids"] and " " not in r["id"]


def test_committed_goldpass_golden_is_up_to_date():
    path = ROOT / "eval" / "goldpass" / "golden.jsonl"
    assert path.read_text(encoding="utf-8") == golden_jsonl(load_golden()), (
        "run `uv run python -m rail_compliance.evaluation goldpass-golden`"
    )


def test_goldpass_records_carry_consulted_and_cited_passages_and_crashes():
    ids = ["g04", "g05"]
    reports = {"g04": report_for("g04"), "g05": None}
    data = records([CASES[i] for i in ids], reports, {"g05": "boom"}, "scripted")
    ok, crashed = data["records"]
    gold = CASES["g04"].expected[SPACES].gold_passages[0]
    assert ok["id"] == item_id("g04", SPACES)
    assert ok["contexts"][0] == {"id": gold, "doc_id": "tsi-prm"}
    assert ok["citations"][0] == {"passage_id": gold, "doc_id": "tsi-prm"}
    assert crashed == {"id": item_id("g05", SPACES), "error": "boom"}


def test_goldpass_can_read_what_we_write(tmp_path):
    pytest.importorskip("goldpass")
    from goldpass.golden import validate_golden

    path = tmp_path / "golden.jsonl"
    path.write_text(golden_jsonl(load_golden()), encoding="utf-8")
    report = validate_golden(path)
    assert report.ok, [str(i) for i in report.issues]


# --- runner and CLI -----------------------------------------------------------------------------


class CannedAgent:
    """Stands in for ComplianceAgent: golden verdicts, or a crash or outage on demand."""

    def __init__(self, crash=(), outage=()):
        self.crash, self.outage = set(crash), set(outage)

    def run(self, spec):
        case = next(c for c in CASES.values() if c.spec == spec)
        if case.id in self.outage:
            raise LLMUnavailable("quota spent")
        if case.id in self.crash:
            raise RuntimeError("kaboom")
        return report_for(case.id)


def test_run_cases_records_a_crash_and_carries_on():
    cases = [CASES["g04"], CASES["g05"]]
    seen = []
    run = run_cases(cases, CannedAgent(crash=["g04"]), progress=seen.append)
    assert run.reports["g04"] is None and "kaboom" in run.errors["g04"]
    assert run.reports["g05"] is not None
    assert len(seen) == 2 and "ERROR" in seen[0]


def test_a_provider_outage_stops_the_run():
    with pytest.raises(LLMUnavailable):
        run_cases([CASES["g04"], CASES["g05"]], CannedAgent(outage=["g04"]))


def test_cli_run_writes_results_and_gates(tmp_path, capsys):
    out = tmp_path / "run"
    code = cli.main(
        ["run", "--cases", "g04,g05,g16", "--out", str(out), "--gate"],
        build=lambda settings, **kw: CannedAgent(),
    )
    text = capsys.readouterr().out
    assert (out / "metrics.json").exists() and (out / "summary.md").exists()
    assert (out / "reports" / "g04.json").exists() and (out / "reports" / "g04.md").exists()
    assert (out / "goldpass" / "records.json").exists()
    assert "Evaluation results" in text and "Quality gate" in text
    payload = json.loads((out / "metrics.json").read_text("utf-8"))
    assert payload["metrics"]["n_cases"] == 3 and payload["metrics"]["errors"] == 0
    assert code in (0, 1)  # three cases cannot meet every slice threshold; the gate ran


def test_cli_gate_exit_codes(tmp_path):
    out = tmp_path / "run"
    cli.main(["run", "--cases", "g04,g05", "--out", str(out)], build=lambda s, **k: CannedAgent())
    lenient = tmp_path / "lenient.yaml"
    lenient.write_text("metrics:\n  verdict_accuracy: {min: 0.5}\n", encoding="utf-8")
    strict = tmp_path / "strict.yaml"
    strict.write_text("metrics:\n  verdict_accuracy: {min: 1.01}\n", encoding="utf-8")
    assert cli.main(["gate", str(out), "--thresholds", str(lenient)]) == 0
    assert cli.main(["gate", str(out), "--thresholds", str(strict)]) == 1


def test_cli_rejects_unknown_case_ids(capsys):
    code = cli.main(["run", "--cases", "g99"], build=lambda s, **k: CannedAgent())
    assert code == 2 and "g99" in capsys.readouterr().out


def test_cli_records_a_crashed_case_as_an_error_in_the_results(tmp_path):
    out = tmp_path / "run"
    cli.main(
        ["run", "--cases", "g04,g05", "--out", str(out)],
        build=lambda s, **k: CannedAgent(crash=["g04"]),
    )
    payload = json.loads((out / "metrics.json").read_text("utf-8"))
    assert payload["metrics"]["errors"] == 1 and "kaboom" in payload["errors"]["g04"]
