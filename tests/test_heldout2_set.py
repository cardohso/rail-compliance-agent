import importlib.util
import json
from pathlib import Path

import pytest

from rail_compliance.evaluation.gate import load_thresholds
from rail_compliance.golden import SUITES, GoldenCase, load_golden, load_suite, oracle
from rail_compliance.spec import spec_values

ROOT = Path(__file__).resolve().parents[1]
HELDOUT2 = ROOT / "eval" / "heldout2"
CASES = load_golden(HELDOUT2, "k*.json")
DEV = [c for name in SUITES for c in load_suite(name)] + load_golden(
    ROOT / "eval" / "heldout", "h*.json"
)


def test_held_out_set_2_has_its_own_ids_and_tag():
    assert 10 <= len(CASES) <= 15
    assert {c.id for c in CASES}.isdisjoint({c.id for c in DEV})
    assert all(c.id.startswith("k") and "heldout2" in c.tags for c in CASES)


def test_it_covers_every_area_added_after_v0_1_0():
    tags = {t for c in CASES for t in c.tags}
    assert {"range", "relaxation", "renewal", "exemption", "noise", "category-table"} <= tags
    verdicts = {x.verdict for c in CASES for x in c.expected.values()}
    assert verdicts == {"pass", "fail", "needs_human", "not_applicable"}


def test_no_held_out_spec_repeats_a_dev_spec_on_the_values_that_are_scored():
    def signature(case):
        values = spec_values(case.spec)
        return frozenset((p, values[p]) for p in case.expected)

    dev = {signature(c) for c in DEV}
    for case in CASES:
        assert signature(case) not in dev, f"{case.id} duplicates a dev spec"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_the_hand_written_verdicts_agree_with_the_gold_rules(case):
    want = oracle(case.spec)
    for parameter, x in case.expected.items():
        assert want[parameter] == x.verdict, f"{case.id} {parameter}"


def test_its_thresholds_were_set_before_any_run():
    path = HELDOUT2 / "thresholds.yaml"
    load_thresholds(path)
    assert "BEFORE THE AGENT WAS RUN ON IT" in path.read_text("utf-8")


def test_the_committed_files_match_the_builder():
    spec = importlib.util.spec_from_file_location("b2", ROOT / "eval" / "build_heldout2.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    built = {c["id"]: GoldenCase.model_validate(c) for c in module.CASES}
    committed = {c.id: c for c in CASES}
    assert built.keys() == committed.keys()
    for id_, case in built.items():
        assert json.loads(case.model_dump_json()) == json.loads(committed[id_].model_dump_json())
