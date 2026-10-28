import importlib.util
import json
from pathlib import Path

import pytest

from rail_compliance.evaluation.gate import check_thresholds, load_thresholds
from rail_compliance.evaluation.metrics import compute_metrics
from rail_compliance.golden import GOLDEN_DIR, GoldenCase, load_golden, oracle
from rail_compliance.parameters import CHECKED_PARAMETERS
from rail_compliance.spec import spec_values

ROOT = Path(__file__).resolve().parents[1]
HELDOUT = ROOT / "eval" / "heldout"
CASES = load_golden(HELDOUT, "h*.json")
DEV = load_golden(GOLDEN_DIR)
# h10 was written as a deliberate known limit (a person says pass, the tool said needs_human). The
# limit was then fixed (check decides both branches of an unknown condition), so the oracle now
# agrees with every held-out verdict. That fix makes this set a development set from then on.
KNOWN_ORACLE_DISAGREEMENTS: set[tuple[str, str]] = set()


def test_the_held_out_set_has_8_to_10_cases_with_ids_that_do_not_collide_with_the_dev_set():
    assert 8 <= len(CASES) <= 10
    assert {c.id for c in CASES}.isdisjoint({c.id for c in DEV})
    assert all(c.id.startswith("h") and "heldout" in c.tags for c in CASES)


def test_no_held_out_spec_repeats_a_dev_spec_on_the_values_that_are_scored():
    def signature(case):
        values = spec_values(case.spec)
        return frozenset((p, values[p]) for p in case.expected) | frozenset(
            (k, v) for k, v in values.items() if k in ("unit_length_m", "design_speed_kmh")
        )

    dev = {signature(c) for c in DEV}
    for case in CASES:
        assert signature(case) not in dev, f"{case.id} duplicates a dev spec"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_each_verdict_agrees_with_the_gold_rules_applied_by_check(case):
    want = oracle(case.spec)
    for parameter, expected in case.expected.items():
        if (case.id, parameter) in KNOWN_ORACLE_DISAGREEMENTS:
            assert expected.verdict == "pass" and want[parameter] == "needs_human"
            continue
        assert expected.verdict == want[parameter], f"{case.id}/{parameter}: oracle says {want}"
        assert set(case.expected) <= set(CHECKED_PARAMETERS)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_every_held_out_case_is_well_formed(case):
    assert case.expected and case.why
    for expected in case.expected.values():
        assert expected.rationale and expected.gold_passages


def test_the_case_written_as_a_known_limit_is_now_handled_and_its_record_is_unchanged():
    h10 = next(c for c in CASES if c.id == "h10")
    assert "known-limit" in h10.tags and "KNOWN LIMIT" in h10.why  # the record as written
    wc = "exterior_doors.wheelchair_door_clear_width_mm"
    assert oracle(h10.spec)[wc] == h10.expected[wc].verdict == "pass"


def test_committed_files_match_the_builder():
    path = ROOT / "eval" / "build_heldout.py"
    spec = importlib.util.spec_from_file_location("build_heldout", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    built = {c["id"]: GoldenCase.model_validate(c) for c in module.CASES}
    committed = {c.id: c for c in CASES}
    assert built.keys() == committed.keys()
    for id_, case in built.items():
        assert json.loads(case.model_dump_json()) == json.loads(committed[id_].model_dump_json())


def test_the_held_out_thresholds_load_and_a_perfect_run_meets_them():
    thresholds = load_thresholds(HELDOUT / "thresholds.yaml")
    assert "tags" not in thresholds
    metrics = compute_metrics(CASES, perfect_for(CASES))
    assert all(c.ok for c in check_thresholds(metrics, thresholds))


def perfect_for(cases):

    return {c.id: report_for_case(c) for c in cases}


def report_for_case(case):
    from rail_compliance.report import ParameterResult, Report, Stats
    from tests.eval_helpers import citation, good_calls

    results, trace = [], []
    for parameter, expected in case.expected.items():
        trace += good_calls(case, parameter)
        results.append(
            ParameterResult(
                parameter=parameter, verdict=expected.verdict, reason="r",
                citations=[citation(p) for p in expected.gold_passages],
                consulted=list(expected.gold_passages),
            )
        )  # fmt: skip
    stats = Stats(tool_calls=len(trace), llm_calls=len(trace), seconds=1.0,
                  agent_model="scripted", search_backend="fake")  # fmt: skip
    return Report(spec_name=case.spec.name, spec={}, results=results, trace=trace, stats=stats)


def test_the_evaluation_cli_can_score_another_folder(tmp_path, capsys):
    from rail_compliance.evaluation import cli
    from tests.test_gate_and_runner import CannedAgent

    class HeldoutAgent(CannedAgent):
        def run(self, spec):
            case = next(c for c in CASES if c.spec == spec)
            return report_for_case(case)

    out = tmp_path / "run"
    code = cli.main(
        ["run", "--golden-dir", str(HELDOUT), "--thresholds", str(HELDOUT / "thresholds.yaml"),
         "--out", str(out), "--gate"],
        build=lambda s, **k: HeldoutAgent(),
    )  # fmt: skip
    metrics = json.loads((out / "metrics.json").read_text("utf-8"))["metrics"]
    assert code == 0 and metrics["n_cases"] == len(CASES)
