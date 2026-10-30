"""The Noise TSI (Regulation (EU) No 1304/2014): limits by rolling-stock category, a table whose
rows are categories rather than ranges, and parameters that only the Noise TSI governs."""

import pytest
from pydantic import ValidationError

from rail_compliance.models import Band, Requirement, RequirementCore, RequirementDraft
from rail_compliance.parameters import CHECKED_PARAMETERS, REGULATION_OF
from rail_compliance.spec import TrainSpec, spec_categories, unit_of
from rail_compliance.tools.check import check
from rail_compliance.tools.extract import _category_stated, extract_requirement
from tests.factories import CITATION, passage
from tests.test_extract import FakeLLM

STATIONARY = "noise.stationary_db"
CATEGORY = "rolling_stock_category"
TABLE_2 = (
    "Table 2 Limit values for stationary noise Category of the rolling stock subsystem | "
    "LpAeq,T[unit] [dB] | Li pAeq,T [dB] | Li pAFmax [dB] Electric locomotives and special "
    "vehicles with electric traction | 70 | 75 | 85 Diesel locomotives and special vehicles with "
    "diesel traction | 71 | 78 EMUs | 65 | 68 DMUs | 72 | 76 Coaches | 64 | 68 Wagons | 65 | "
    "n.a. | n.a."
)
NOISE_PASSAGE = passage(TABLE_2, id_="tsi-noi:Annex §4.2.1#1", doc_id="tsi-noi",
                        document="Noise TSI", section="Annex §4.2.1")  # fmt: skip


def by_category(**rows):
    return [Band(category=c, value=v) for c, v in rows.items()]


def stationary(**rows):
    return Requirement(parameter=STATIONARY, subject="stationary_noise", comparator="<=",
                       bands=by_category(**rows), band_variable=CATEGORY, unit="dB",
                       citation=CITATION)  # fmt: skip


ROWS = {"emu": 65, "dmu": 72, "coach": 64}


# --- the spec --------------------------------------------------------------------------------


def test_noise_values_are_in_decibels_and_the_category_is_a_choice():
    s = TrainSpec(name="t", unit_length_m=100, rolling_stock_category="emu",
                  noise={"stationary_db": 64})  # fmt: skip
    assert unit_of(STATIONARY) == "dB"
    assert spec_categories(s)[CATEGORY] == "emu"
    with pytest.raises(ValidationError):
        TrainSpec(name="t", unit_length_m=100, rolling_stock_category="tram")


def test_every_parameter_belongs_to_one_regulation():
    assert set(REGULATION_OF) == set(CHECKED_PARAMETERS)
    assert REGULATION_OF[STATIONARY] == "tsi-noi"
    assert REGULATION_OF["wheelchair_spaces"] == "tsi-prm"


# --- a table selected by category ------------------------------------------------------------


@pytest.mark.parametrize(
    ("category", "value", "verdict"),
    [("emu", 65, "pass"), ("emu", 66, "fail"), ("coach", 65, "fail"), ("dmu", 70, "pass")],
)
def test_a_category_table_picks_the_row_for_the_spec_category(category, value, verdict):
    r = check(value, stationary(**ROWS), context={CATEGORY: category})
    assert r.verdict == verdict
    assert r.required_value == ROWS[category]


def test_a_category_the_table_has_no_row_for_is_needs_human():
    r = check(60, stationary(**ROWS), context={CATEGORY: "wagon"})
    assert r.verdict == "needs_human" and "wagon" in r.reason


def test_an_unknown_category_is_needs_human_unless_every_row_is_met():
    assert check(70, stationary(**ROWS), context={}).verdict == "needs_human"
    assert check(60, stationary(**ROWS), context={}).verdict == "pass"


def test_a_band_is_a_range_or_a_category_not_both():
    with pytest.raises(ValidationError, match="category"):
        Band(category="emu", lower=0, value=65)


def test_a_table_mixes_no_range_rows_with_category_rows():
    with pytest.raises(ValidationError, match="category"):
        RequirementCore(parameter=STATIONARY, subject="stationary_noise", comparator="<=",
                        bands=[Band(category="emu", value=65), Band(upper=30, value=1)],
                        band_variable=CATEGORY)  # fmt: skip


@pytest.mark.parametrize(
    ("value", "text", "stated"),
    [
        ("emu", "EMUs | 65 | 68", True),
        ("electric_locomotive", "Electric locomotives and special vehicles", True),
        ("coach", "Coaches | 64 | 68", True),
        ("dmu", "EMUs | 65 | 68", False),
    ],
)
def test_the_regulation_names_categories_in_its_own_words(value, text, stated):
    assert _category_stated(value, text) is stated


# --- extraction ------------------------------------------------------------------------------


def table_draft(rows=None, quote=TABLE_2, passage_id=NOISE_PASSAGE.id):
    bands = by_category(**(rows or ROWS))
    rule = RequirementCore(parameter=STATIONARY, subject="stationary_noise", comparator="<=",
                           bands=bands, band_variable=CATEGORY, unit="dB")  # fmt: skip
    return RequirementDraft(found=True, passage_id=passage_id, quote=quote, rule=rule)


def test_a_category_table_is_verified_against_the_quote():
    assert (
        extract_requirement([NOISE_PASSAGE], STATIONARY, FakeLLM(table_draft())).status == "found"
    )


def test_a_row_for_a_category_the_quote_does_not_name_is_unverified():
    result = extract_requirement([NOISE_PASSAGE], STATIONARY,
                                 FakeLLM(table_draft(ROWS | {"emu": 65, "tram": 60})))  # fmt: skip
    assert result.status == "unverified"


PRM_SIGNAL = passage(
    "(4) The door closing signal shall be between 3 and 7 dB above the ambient noise level.",
    id_="tsi-prm:Annex §4.2.2.4.1#1",
)


def test_a_rule_quoted_from_another_regulation_is_rejected():
    rule = RequirementCore(parameter=STATIONARY, subject="stationary_noise", comparator="<=",
                           value=7, unit="dB")  # fmt: skip
    draft = RequirementDraft(found=True, passage_id=PRM_SIGNAL.id, rule=rule,
                             quote="between 3 and 7 dB above the ambient noise level")  # fmt: skip
    result = extract_requirement([PRM_SIGNAL], STATIONARY, FakeLLM(draft))
    assert result.status == "unverified" and "tsi-noi" in result.reason


# --- the agent ---------------------------------------------------------------------------------


def test_the_task_names_the_regulation_and_only_prm_parameters_get_the_appendix_f_hint():
    from rail_compliance.agent import _task_message

    cats = {"unit_status": "renewed", CATEGORY: "emu"}
    noise = _task_message(STATIONARY, {STATIONARY: 64.0}, cats)
    assert "Noise TSI" in noise and "Appendix F" not in noise
    prm = _task_message(
        "handrails.outside_diameter_mm", {"handrails.outside_diameter_mm": 35.0}, cats
    )
    assert "PRM TSI" in prm and "Appendix F" in prm


def test_a_renewed_units_noise_is_left_to_a_person_without_a_search():
    from tests.test_agent import run

    s = TrainSpec(name="t", unit_length_m=100, unit_status="renewed", noise={"stationary_db": 64})
    report, llm, *_ = run(s, [])
    result = report.result_for(STATIONARY)
    assert result.verdict == "needs_human" and "first authorised" in result.reason
    assert llm.seen == []


def test_a_valid_category_row_the_quote_does_not_name_is_unverified():
    quote = "EMUs | 65 | 68 DMUs | 72 | 76 Coaches | 64 | 68"  # no wagon row in the quote
    draft = table_draft(ROWS | {"wagon": 65}, quote=quote)
    result = extract_requirement([NOISE_PASSAGE], STATIONARY, FakeLLM(draft))
    assert result.status == "unverified" and "wagon" in result.reason


def test_a_row_name_that_is_not_a_choice_is_unverified_even_if_the_quote_has_the_word():
    draft = table_draft(ROWS | {"traction": 70})  # "traction" is in the table text
    result = extract_requirement([NOISE_PASSAGE], STATIONARY, FakeLLM(draft))
    assert result.status == "unverified" and "Valid:" in result.reason
