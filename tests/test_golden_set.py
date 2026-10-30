import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

from rail_compliance.golden import (
    GOLD_EXEMPTIONS,
    GOLD_RULES,
    GOLDEN_DIR,
    SUITES,
    load_golden,
    load_suite,
    oracle,
)
from rail_compliance.parameters import CHECKED_PARAMETERS
from rail_compliance.spec import TrainSpec

ROOT = Path(__file__).resolve().parents[1]
CORE = load_golden()
CASES = [c for name in SUITES for c in load_suite(name)]
TOOLS = {"search_regulation", "extract_requirement", "check", "needs_human"}


def test_the_core_suite_has_between_15_and_20_cases_and_every_id_is_unique():
    assert 15 <= len(CORE) <= 20
    assert len({c.id for c in CASES}) == len(CASES)


def test_every_suite_loads_and_an_unknown_one_is_an_error():
    assert [len(load_suite(name)) for name in SUITES] == [len(CORE), 12, 10, 10]
    with pytest.raises(ValueError, match="core"):
        load_suite("nope")


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
    on_disk = sum(len(list(GOLDEN_DIR.glob(pattern))) for pattern in SUITES.values())
    assert on_disk == len(built)  # no stale files


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
    for rules in [*GOLD_RULES.values(), *GOLD_EXEMPTIONS.values()]:
        for rule in rules:
            passage = passages.get(rule.citation.passage_id)
            assert passage is not None, f"no passage {rule.citation.passage_id}"
            assert _quote_in(rule.citation.quote, passage.text), (
                f"quote not in {passage.id}: {rule.citation.quote[:60]}"
            )
    for case in CASES:
        for x in case.expected.values():
            assert all(g in passages for g in x.gold_passages)


def test_every_gold_rule_and_exemption_passes_extraction_verification_on_the_real_text():
    """The verifier must accept the right answer, quoted from the real passage."""
    from rail_compliance.models import RequirementCore, RequirementDraft
    from rail_compliance.tools.extract import extract_requirement

    passages = _real_passages()

    class Answer:
        def __init__(self, draft):
            self.draft = draft

        def extract(self, system, user, schema):
            return self.draft

    for parameter in GOLD_RULES:
        for rule in [*GOLD_RULES[parameter], *GOLD_EXEMPTIONS[parameter]]:
            core = RequirementCore(**rule.model_dump(exclude={"citation"}))
            draft = RequirementDraft(found=True, passage_id=rule.citation.passage_id,
                                     quote=rule.citation.quote, rule=core)  # fmt: skip
            source = passages[rule.citation.passage_id]
            result = extract_requirement([source], parameter, Answer(draft))
            assert result.status == "found", f"{parameter}: {result.reason}"


def _real_passages():
    pytest.importorskip("rail_rag")
    import os

    from rail_compliance.config import get_settings

    data = get_settings().rail_rag_data_dir
    if not (data / "processed" / "tsi-prm.jsonl").exists():
        pytest.skip(f"no corpus at {data}")
    os.environ.setdefault("RAIL_RAG_DATA_DIR", str(data))
    from rail_rag.chunking import load_passages

    from rail_compliance.models import Passage

    return {
        p.id: Passage(
            id=p.id, doc_id=p.doc_id, document=p.doc_short, section=p.section, text=p.text
        )
        for p in load_passages(data / "processed")
    }


def test_the_coverage_check_raises_no_false_alarm_on_perfect_extraction_of_the_real_text():
    """With the gold rules as the extractor, no real passage trips the check for any parameter."""
    from rail_compliance.parameters import MEASURES
    from rail_compliance.tools.coverage import find_gaps

    passages = _real_passages()
    for parameter in MEASURES:
        gaps = find_gaps(parameter, passages, GOLD_RULES[parameter])
        assert gaps == [], f"{parameter}: false alarm on {gaps}"


def test_the_coverage_check_fires_on_the_real_text_when_a_gold_rule_is_dropped():
    from rail_compliance.golden import (
        INTERNAL_GENERAL,
        WHEELCHAIR_GENERAL,
        WHEELCHAIR_LEVEL,
    )
    from rail_compliance.tools.coverage import find_gaps

    passages = _real_passages()
    wc = "exterior_doors.wheelchair_door_clear_width_mm"
    only_general = find_gaps(wc, passages, [WHEELCHAIR_GENERAL])
    assert len(only_general) == 1 and "1 000 mm" in only_general[0].sentence
    only_special = find_gaps(wc, passages, [WHEELCHAIR_LEVEL])
    assert len(only_special) == 1 and "800 mm" in only_special[0].sentence
    internal = find_gaps("steps.internal_step_height_mm", passages, [INTERNAL_GENERAL])
    assert len(internal) == 1 and "230 mm" in internal[0].sentence


def test_on_the_real_text_a_table_reduced_to_one_value_is_flagged_and_the_full_table_is_not():
    from rail_compliance.golden import TABLE_5
    from rail_compliance.tools.coverage import find_gaps

    passages = _real_passages()
    assert find_gaps("wheelchair_spaces", passages, [TABLE_5]) == []
    one_row = TABLE_5.model_copy(update={"bands": [], "band_variable": None, "value": 2.0})
    found = find_gaps("wheelchair_spaces", passages, [one_row])
    assert len(found) == 1 and "Table 5" in found[0].sentence
