import pytest

from rail_compliance.evaluation.metrics import (
    compute_metrics,
    is_subsequence,
    percentile,
    rate,
    score_items,
    wilson,
)
from tests.eval_helpers import CASES, call, good_calls, perfect, report_for

# g04: 1 item (spaces, expected fail).  g05: 1 (pass).  g16: 1 (needs_human).  g17: 1 (n/a).
# g03: 1 (needs_human).  g10: 1 (fail).  g14: 1 (needs_human).
SPACES = "wheelchair_spaces"
INTERNAL = "steps.internal_step_height_mm"
WC = "exterior_doors.wheelchair_door_clear_width_mm"


def cases(*ids):
    return [CASES[i] for i in ids]


def metrics(ids, reports):
    return compute_metrics(cases(*ids), reports)


def test_a_perfect_agent_scores_one_everywhere():
    ids = ["g04", "g05", "g16", "g17", "g10"]
    m = metrics(ids, perfect(ids))
    assert m.errors == 0 and m.n_items == 5
    for name in ("verdict_accuracy", "tool_selection_accuracy", "argument_correctness"):
        assert m.rates[name].value == 1.0, name
    assert m.rates["unsafe_pass_rate"].value == 0.0
    assert m.rates["needs_human_recall"].value == 1.0
    assert m.rates["needs_human_precision"].value == 1.0
    assert m.rates["citation_hit_rate"].value == 1.0


def test_verdict_accuracy_counts_every_mismatch():
    ids = ["g04", "g05", "g10", "g17"]
    reports = perfect(ids)
    reports["g04"] = report_for("g04", verdicts={SPACES: "pass"})  # expected fail
    reports["g17"] = report_for("g17", verdicts={"toilets.universal": "pass"})  # expected n/a
    m = metrics(ids, reports)
    assert (m.rates["verdict_accuracy"].k, m.rates["verdict_accuracy"].n) == (2, 4)


def test_unsafe_pass_is_pass_where_golden_says_fail_or_needs_human_only():
    ids = ["g04", "g16", "g17", "g05"]
    reports = perfect(ids)
    reports["g04"] = report_for("g04", verdicts={SPACES: "pass"})  # fail -> pass: unsafe
    reports["g16"] = report_for("g16", verdicts={INTERNAL: "pass"})  # needs_human -> pass: unsafe
    reports["g17"] = report_for("g17", verdicts={"toilets.universal": "pass"})  # n/a -> pass: not
    reports["g05"] = report_for("g05", verdicts={SPACES: "fail"})  # pass -> fail: wrong, safe
    r = metrics(ids, reports).rates["unsafe_pass_rate"]
    assert (r.k, r.n) == (2, 4)


def test_needs_human_precision_and_recall_from_a_hand_worked_mix():
    ids = ["g03", "g16", "g14", "g04", "g05"]  # expected escalations: g03, g16, g14
    reports = perfect(ids)
    reports["g14"] = report_for("g14", verdicts={WC: "fail"})  # missed an escalation
    reports["g04"] = report_for("g04", verdicts={SPACES: "needs_human"})  # needless escalation
    m = metrics(ids, reports)
    assert (m.rates["needs_human_recall"].k, m.rates["needs_human_recall"].n) == (2, 3)
    assert (m.rates["needs_human_precision"].k, m.rates["needs_human_precision"].n) == (2, 3)


def test_precision_has_no_value_when_the_agent_never_escalates():
    ids = ["g03", "g04"]
    reports = {
        "g03": report_for("g03", verdicts={INTERNAL: "fail"}),
        "g04": report_for("g04"),
    }
    m = metrics(ids, reports)
    assert m.rates["needs_human_precision"].value is None
    assert m.rates["needs_human_recall"].value == 0.0


def test_tool_selection_needs_the_expected_tools_in_order_with_extras_allowed():
    def ok(calls, case="g04", parameter=SPACES):
        report = report_for(case, calls={parameter: calls})
        return score_items(cases(case), {case: report})[0].tool_selection_ok

    s, e, c = (call(SPACES, n) for n in ("search_regulation", "extract_requirement", "check"))
    assert ok([s, e, c])
    assert ok([s, s, e, e, c])  # repeats are fine
    assert not ok([e, s, c])  # wrong order
    assert not ok([s, c])  # extraction skipped
    assert not ok([])


def test_an_alternative_tool_sequence_is_accepted():
    # g14 accepts check (rule path) or needs_human (escalate path)
    s, e, n = (call(WC, x) for x in ("search_regulation", "extract_requirement", "needs_human"))
    report = report_for("g14", calls={WC: [s, e, n]})
    assert score_items(cases("g14"), {"g14": report})[0].tool_selection_ok


def test_runtime_decided_calls_do_not_count_as_the_agents_tools():
    runtime = call(SPACES, "needs_human", source="runtime")
    report = report_for("g04", calls={SPACES: [runtime]})
    item = score_items(cases("g04"), {"g04": report})[0]
    assert item.agent_calls == 0 and not item.tool_selection_ok


def test_argument_correctness_checks_parameter_and_the_specs_value():
    good = good_calls(CASES["g04"], SPACES)
    wrong_value = call(SPACES, "check", {"parameter": SPACES, "spec_value": 2.0})  # spec has 1
    wrong_param = call(SPACES, "check", {"parameter": DOORS, "spec_value": 1.0})
    report = report_for("g04", calls={SPACES: [*good, wrong_value, wrong_param]})
    item = score_items(cases("g04"), {"g04": report})[0]
    assert (item.correct_check_calls, item.check_calls) == (1, 3)
    m = compute_metrics(cases("g04"), {"g04": report})
    assert (m.rates["argument_correctness"].k, m.rates["argument_correctness"].n) == (1, 3)


DOORS = "exterior_doors.clear_width_mm"


def test_argument_correctness_has_no_value_without_any_check_call():
    s = call(INTERNAL, "search_regulation")
    n = call(INTERNAL, "needs_human")
    report = report_for("g16", calls={INTERNAL: [s, n]})
    assert (
        compute_metrics(cases("g16"), {"g16": report}).rates["argument_correctness"].value is None
    )


def test_a_rejected_check_with_correct_arguments_is_still_correct_arguments():
    good = good_calls(CASES["g04"], SPACES)
    good[2] = good[2].model_copy(update={"ok": False})  # e.g. unknown requirement id
    report = report_for("g04", calls={SPACES: good})
    assert score_items(cases("g04"), {"g04": report})[0].correct_check_calls == 1


def test_citation_hit_and_precision():
    gold = CASES["g04"].expected[SPACES].gold_passages[0]
    other = "tsi-prm:Annex §9.9#1"
    both = report_for("g04", cited={SPACES: [gold, other]})
    wrong = report_for("g04", cited={SPACES: [other]})
    none = report_for("g04", cited={SPACES: []})
    a = score_items(cases("g04"), {"g04": both})[0]
    b = score_items(cases("g04"), {"g04": wrong})[0]
    c = score_items(cases("g04"), {"g04": none})[0]
    assert (a.citation_hit, a.citation_precision) == (True, 0.5)
    assert (b.citation_hit, b.citation_precision) == (False, 0.0)
    assert (c.citation_hit, c.citation_precision) == (None, None)


def test_items_with_no_citation_are_left_out_of_the_citation_rate():
    ids = ["g04", "g05"]
    reports = perfect(ids)
    reports["g05"] = report_for("g05", cited={SPACES: []})
    r = metrics(ids, reports).rates["citation_hit_rate"]
    assert (r.k, r.n) == (1, 1)


def test_a_crashed_case_counts_against_every_rate_and_as_an_error():
    ids = ["g04", "g05"]
    reports = {"g04": report_for("g04"), "g05": None}
    m = metrics(ids, reports)
    assert m.errors == 1
    assert (m.rates["verdict_accuracy"].k, m.rates["verdict_accuracy"].n) == (1, 2)
    assert m.rates["tool_selection_accuracy"].k == 1
    assert m.confusion["pass"] == {"error": 1}


def test_tool_calls_per_parameter_and_per_spec_figures():
    ids = ["g04", "g05"]
    reports = {"g04": report_for("g04", seconds=10), "g05": report_for("g05", seconds=30)}
    m = metrics(ids, reports)
    assert m.tool_calls_per_parameter == 3.0
    assert m.per_spec["tool_calls_mean"] == 3.0
    assert m.per_spec["seconds_mean"] == 20.0
    assert m.per_spec["seconds_p50"] == 20.0


def test_slices_by_tag():
    ids = ["g04", "g05", "g17"]  # g04, g05: table-boundary; g17: not-applicable
    reports = perfect(ids)
    reports["g04"] = report_for("g04", verdicts={SPACES: "pass"})
    m = metrics(ids, reports)
    boundary = m.by_tag["table-boundary"]["verdict_accuracy"]
    assert (boundary.k, boundary.n) == (1, 2)
    assert m.by_tag["not-applicable"]["verdict_accuracy"].value == 1.0


def test_confusion_matrix():
    ids = ["g04", "g05"]
    reports = perfect(ids)
    reports["g04"] = report_for("g04", verdicts={SPACES: "pass"})
    m = metrics(ids, reports)
    assert m.confusion == {"fail": {"pass": 1}, "pass": {"pass": 1}}


def test_wilson_interval_known_values():
    assert wilson(0, 0) == (0.0, 1.0)
    low, high = wilson(5, 5)
    assert 0.55 < low < 0.58 and high == 1.0
    low, high = wilson(0, 10)
    assert low == 0.0 and 0.25 < high < 0.35
    low, high = wilson(40, 43)
    assert 0.80 < low < 0.83 and 0.97 < high < 0.99


def test_rate_with_no_trials_has_no_value():
    assert rate(0, 0).value is None


@pytest.mark.parametrize(
    ("wanted", "seen", "ok"),
    [
        (["a", "b"], ["a", "x", "b"], True),
        (["a", "b"], ["b", "a"], False),
        (["a", "a"], ["a"], False),
        ([], ["a"], True),
    ],
)
def test_is_subsequence(wanted, seen, ok):
    assert is_subsequence(wanted, seen) is ok


def test_percentile():
    assert percentile([], 0.5) is None
    assert percentile([1, 2, 3, 4], 0.5) == 2.5
    assert percentile([10], 0.95) == 10
    assert percentile(list(range(101)), 0.95) == 95


def test_explanation_quality_scores_the_agents_own_escalation_reasons():
    from rail_compliance.evaluation.metrics import explanation_quality

    clean = call(SPACES, "needs_human", {"reason": "The table is ambiguous at 205 m."})
    rambling = call(SPACES, "needs_human",
                    {"reason": "It is 205 m. Wait, it is 210 m, so let me re-check."})  # fmt: skip
    rejected = call(SPACES, "needs_human", {"reason": "x. Wait."}, ok=False)
    runtime = call(SPACES, "needs_human", {"reason": "a. b. c."}, source="runtime")
    reports = {
        "g04": report_for("g04", calls={SPACES: [clean]}),
        "g05": report_for("g05", calls={SPACES: [rambling, rejected, runtime]}),
    }
    r = explanation_quality(reports.values())
    assert (r.k, r.n) == (1, 2)  # rejected and runtime-written reasons are not the agent's record


def test_metrics_carry_explanation_quality_but_the_gate_does_not_know_it():
    from rail_compliance.evaluation.gate import KNOWN

    m = metrics(["g16"], perfect(["g16"]))
    assert m.explanation_quality is not None
    assert "explanation_quality" not in KNOWN
