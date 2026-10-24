import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

from rail_compliance.golden import (
    GOLD_RULES,
    GOLDEN_DIR,
    load_golden,
    oracle,
)
from rail_compliance.parameters import CHECKED_PARAMETERS
from rail_compliance.spec import TrainSpec

ROOT = Path(__file__).resolve().parents[1]
CASES = load_golden()
TOOLS = {"search_regulation", "extract_requirement", "check", "needs_human"}


def test_there_are_between_15_and_20_cases_with_unique_ids():
    assert 15 <= len(CASES) <= 20
    assert len({c.id for c in CASES}) == len(CASES)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_expected_verdicts_agree_with_the_gold_rules_applied_by_check(case):
    """Catches arithmetic slips in the hand-written verdicts. Not a test of the agent."""
    want = oracle(case.spec)
    got = {p: x.verdict for p, x in case.expected.items()}
    assert set(got) <= set(CHECKED_PARAMETERS)
    assert got == {p: want[p] for p in got}, f"{case.id}: expected {got}, rules say {want}"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_every_case_is_well_formed(case):
    assert case.expected, "a case with nothing to score"
    assert case.why and case.tags
    for parameter, x in case.expected.items():
        assert x.rationale, f"{case.id}/{parameter} has no rationale"
        assert x.gold_passages, f"{case.id}/{parameter} names no gold passage"
        for sequence in [x.expected_tools, *x.alt_tools]:
            assert set(sequence) <= TOOLS
            assert sequence[0] == "search_regulation"
            assert sequence[-1] in {"check", "needs_human"}


def test_the_traps_the_brief_asks_for_are_all_present():
    tags = Counter(t for c in CASES for t in c.tags)
    needed = [
        "exact-limit", "length-dependent", "conditional-rule", "needs-human", "missing-data",
        "other-section", "table-boundary", "violation", "baseline",
    ]  # fmt: skip
    for tag in needed:
        assert tags[tag] >= 1, f"no case tagged {tag}"


def test_every_verdict_kind_is_expected_somewhere():
    kinds = Counter(x.verdict for c in CASES for x in c.expected.values())
    assert set(kinds) == {"pass", "fail", "needs_human", "not_applicable"}
    assert kinds["needs_human"] >= 4  # enough to say anything about escalation recall


def test_every_table_row_boundary_is_exercised():
    lengths = {c.spec.unit_length_m for c in CASES if "wheelchair_spaces" in c.expected}
    assert {30.0, 205.0, 300.0, 300.1, 205.1} <= lengths


def test_each_checked_parameter_is_scored_in_at_least_two_cases():
    scored = Counter(p for c in CASES for p in c.expected)
    assert all(scored[p] >= 2 for p in CHECKED_PARAMETERS), scored


def test_oracle_on_known_values():
    def verdict(parameter, **spec):
        return oracle(TrainSpec.model_validate({"name": "t", "unit_length_m": 100, **spec}))[
            parameter
        ]

    assert verdict("wheelchair_spaces", unit_length_m=30, wheelchair_spaces=1) == "fail"
    assert verdict("wheelchair_spaces", unit_length_m=29.99, wheelchair_spaces=1) == "pass"
    assert verdict("steps.internal_step_height_mm", steps={"internal_step_height_mm": 215}) == (
        "needs_human"
    )
    assert verdict("steps.internal_step_height_mm", steps={"internal_step_height_mm": 231}) == (
        "fail"
    )


def test_committed_files_match_the_builder():
    path = ROOT / "eval" / "build_golden.py"
    spec = importlib.util.spec_from_file_location("build_golden", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from rail_compliance.golden import GoldenCase

    built = {c["id"]: GoldenCase.model_validate(c) for c in module.CASES}
    committed = {c.id: c for c in CASES}
    assert built.keys() == committed.keys()
    for id_, case in built.items():
        assert json.loads(case.model_dump_json()) == json.loads(committed[id_].model_dump_json()), (
            f"{id_} differs: run `uv run python eval/build_golden.py`"
        )
    assert len(list(GOLDEN_DIR.glob("g*.json"))) == len(built)  # no stale files


# --- needs the corpus: skipped in CI's offline job ----------------------------------------------


def test_gold_quotes_and_passage_ids_exist_in_the_real_corpus():
    pytest.importorskip("rail_rag")
    import os

    from rail_compliance.config import get_settings
    from rail_compliance.tools.extract import _quote_in

    data = get_settings().rail_rag_data_dir
    if not (data / "processed" / "tsi-prm.jsonl").exists():
        pytest.skip(f"no corpus at {data}")
    os.environ.setdefault("RAIL_RAG_DATA_DIR", str(data))  # rail_rag reads this when imported
    from rail_rag.chunking import load_passages

    passages = {p.id: p for p in load_passages(data / "processed")}
    for rules in GOLD_RULES.values():
        for rule in rules:
            passage = passages.get(rule.citation.passage_id)
            assert passage is not None, f"no passage {rule.citation.passage_id}"
            assert _quote_in(rule.citation.quote, passage.text), (
                f"quote not in {passage.id}: {rule.citation.quote[:60]}"
            )
    for case in CASES:
        for x in case.expected.values():
            assert all(g in passages for g in x.gold_passages)
