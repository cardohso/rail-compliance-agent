from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
EVAL = yaml.safe_load((ROOT / ".github/workflows/eval.yml").read_text(encoding="utf-8"))
STEPS = {s.get("name", s.get("uses")): s for s in EVAL["jobs"]["golden-set"]["steps"]}


def test_the_gates_cannot_fail_a_partial_manual_run_but_do_fail_full_ones():
    for name in (
        "Gate on tool use, verdicts and escalation",
        "Gate on retrieval, citations and grounding (goldpass)",
    ):
        assert STEPS[name]["continue-on-error"] == "${{ inputs.cases != '' }}"


def test_the_model_cache_is_saved_even_when_the_run_or_the_gate_fails():
    assert STEPS["Save the model and search cache"]["if"] == "always()"
    assert STEPS["Upload results"]["if"] == "always()"


def test_the_case_filter_reaches_the_script_through_the_environment_not_interpolation():
    run = STEPS["Run the agent on the golden set"]
    assert "CASES" in run["env"] and "${{" not in run["run"]


def test_pull_requests_from_forks_are_skipped_because_they_get_no_secret():
    condition = EVAL["jobs"]["golden-set"]["if"]
    assert "pull_request" in condition and "head.repo.full_name" in condition


def test_a_manual_run_picks_a_suite_and_pull_requests_run_core():
    triggers = EVAL.get("on", EVAL.get(True))  # YAML 1.1 reads the key `on` as true
    inputs = triggers["workflow_dispatch"]["inputs"]
    from rail_compliance.golden import SUITES

    assert inputs["suite"]["options"] == list(SUITES) and inputs["suite"]["default"] == "core"
    run = STEPS["Run the agent on the golden set"]
    assert (
        run["env"]["SUITE"] == "${{ inputs.suite || 'core' }}" and '--suite "$SUITE"' in run["run"]
    )
    assert STEPS["Gate on retrieval, citations and grounding (goldpass)"]["if"] == (
        "(inputs.suite || 'core') == 'core'"
    )
