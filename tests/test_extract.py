import pytest

from rail_compliance.models import (
    Band,
    BandDraft,
    Condition,
    RequirementCore,
    RequirementDraft,
    RuleDraft,
)
from rail_compliance.parameters import SUBJECT_OF
from rail_compliance.tools.extract import extract_requirement, numbers_in
from tests.factories import passage

# Text copied from the PRM TSI as ingested by rail-regulation-rag (data/processed/tsi-prm.jsonl).
DOORS = (
    "(1) All exterior passenger doorways shall have a minimum clear useable width of 800 mm "
    "when open.\n(2) On trains with a design speed lower than 250 km/h, wheelchair access doors "
    "offering a level access as defined in point 2.3 shall have a minimum clear useable width "
    "of 1 000 mm when open."
)
TABLE = (
    "(1) According to the length of the unit, excluding the locomotive or power head, there "
    "shall be in that unit not less than the number of accessible wheelchair spaces shown in "
    "the following table: Table 5 Minimum number of wheelchair spaces per unit length Unit "
    "length | Number of wheelchair spaces by unit Less than 30 m | 1 wheelchair space 30 to 205 "
    "metres | 2 wheelchair spaces More than 205 to 300 metres | 3 wheelchair spaces More than "
    "300 metres | 4 wheelchair spaces"
)
DOOR_PASSAGE = passage(DOORS)
TABLE_PASSAGE = passage(TABLE, id_="tsi-prm:Annex §4.2.2.2#1", section="Annex §4.2.2.2")
QUOTE_800 = (
    "All exterior passenger doorways shall have a minimum clear useable width of 800 mm when open."
)


class FakeLLM:
    """Returns a canned draft and records what it was asked."""

    def __init__(self, draft: RequirementDraft):
        self.draft, self.calls = draft, []

    def extract(self, system, user, schema):
        self.calls.append((system, user, schema))
        return self.draft


def door_draft(**over) -> RequirementDraft:
    rule = RequirementCore(
        parameter="exterior_doors.clear_width_mm",
        subject=SUBJECT_OF["exterior_doors.clear_width_mm"],
        comparator=">=",
        value=800,
        unit="mm",
    )
    fields = {"found": True, "passage_id": DOOR_PASSAGE.id, "quote": QUOTE_800, "rule": rule}
    return RequirementDraft(**{**fields, **over})


def run(draft, passages=(DOOR_PASSAGE,), parameter="exterior_doors.clear_width_mm"):
    llm = FakeLLM(draft)
    return extract_requirement(list(passages), parameter, llm), llm


def test_verified_rule_becomes_a_requirement_with_a_citation():
    result, _ = run(door_draft())
    assert result.status == "found"
    req = result.requirement
    assert (req.parameter, req.comparator, req.value, req.unit) == (
        "exterior_doors.clear_width_mm",
        ">=",
        800,
        "mm",
    )
    assert req.citation.passage_id == DOOR_PASSAGE.id
    assert req.citation.document == "PRM TSI"
    assert req.citation.section == "Annex §4.2.2.3.2"
    assert req.citation.url == DOOR_PASSAGE.url
    assert req.citation.quote == QUOTE_800


def test_the_prompt_names_the_parameter_its_unit_and_every_passage_id():
    _, llm = run(door_draft())
    system, user, schema = llm.calls[0]
    assert schema is RequirementDraft
    assert "exterior_doors.clear_width_mm" in user
    assert "mm" in user
    assert DOOR_PASSAGE.id in user
    assert "unit_length_m" in user  # spec variables the model may use for conditions and bands
    assert "word for word" in system


def test_a_quote_that_is_not_in_the_passage_is_unverified():
    result, _ = run(door_draft(quote="Doors shall be at least 800 mm wide."))
    assert result.status == "unverified"
    assert "not found in the passage" in result.reason
    assert result.requirement is None


def test_a_value_that_is_not_in_the_quote_is_unverified():
    wrong = RequirementCore(
        parameter="exterior_doors.clear_width_mm",
        subject=SUBJECT_OF["exterior_doors.clear_width_mm"],
        comparator=">=",
        value=900,
        unit="mm",
    )
    result, _ = run(door_draft(rule=wrong))
    assert result.status == "unverified"
    assert "900" in result.reason


def test_an_unknown_passage_id_is_unverified():
    result, _ = run(door_draft(passage_id="tsi-prm:Annex §9.9#1"))
    assert result.status == "unverified"
    assert "passage" in result.reason


def test_a_rule_for_another_parameter_is_unverified():
    result, _ = run(door_draft(), parameter="steps.external_step_height_mm")
    assert result.status == "unverified"
    assert "steps.external_step_height_mm" in result.reason


def test_found_without_a_rule_is_unverified():
    result, _ = run(door_draft(rule=None))
    assert result.status == "unverified"


def test_not_found_reports_the_models_note():
    draft = RequirementDraft(found=False, note="the passage refers to an external standard")
    result, _ = run(draft)
    assert result.status == "not_found"
    assert "external standard" in result.reason


def test_no_passages_means_not_found_without_calling_the_model():
    result, llm = run(door_draft(), passages=())
    assert result.status == "not_found"
    assert llm.calls == []


def test_thousand_separator_spaces_are_read_as_one_number():
    rule = RequirementCore(
        parameter="exterior_doors.wheelchair_door_clear_width_mm",
        subject=SUBJECT_OF["exterior_doors.wheelchair_door_clear_width_mm"],
        comparator=">=",
        value=1000,
        unit="mm",
        conditions=[Condition(variable="design_speed_kmh", op="<", value=250)],
    )
    quote = (
        "On trains with a design speed lower than 250 km/h, wheelchair access doors offering a "
        "level access as defined in point 2.3 shall have a minimum clear useable width of "
        "1 000 mm when open."
    )
    result, _ = run(
        door_draft(quote=quote, rule=rule),
        parameter="exterior_doors.wheelchair_door_clear_width_mm",
    )
    assert result.status == "found"
    assert result.requirement.conditions[0].value == 250


def test_non_breaking_spaces_in_the_source_do_not_break_verification():
    nbsp = passage(DOORS.replace("1 000", "1 000"))
    rule = RequirementCore(
        parameter="exterior_doors.wheelchair_door_clear_width_mm",
        subject=SUBJECT_OF["exterior_doors.wheelchair_door_clear_width_mm"],
        comparator=">=",
        value=1000,
        unit="mm",
    )
    quote = "shall have a minimum clear useable width of 1 000 mm when open"
    result, _ = run(
        door_draft(quote=quote, rule=rule),
        passages=(nbsp,),
        parameter="exterior_doors.wheelchair_door_clear_width_mm",
    )
    assert result.status == "found"


def test_a_condition_value_the_quote_does_not_state_is_unverified():
    rule = RequirementCore(
        parameter="exterior_doors.wheelchair_door_clear_width_mm",
        subject=SUBJECT_OF["exterior_doors.wheelchair_door_clear_width_mm"],
        comparator=">=",
        value=1000,
        unit="mm",
        conditions=[Condition(variable="design_speed_kmh", op="<", value=300)],  # text says 250
    )
    quote = (
        "On trains with a design speed lower than 250 km/h, wheelchair access doors offering a "
        "level access as defined in point 2.3 shall have a minimum clear useable width of "
        "1 000 mm when open."
    )
    result, _ = run(
        door_draft(quote=quote, rule=rule),
        parameter="exterior_doors.wheelchair_door_clear_width_mm",
    )
    assert result.status == "unverified"
    assert "300" in result.reason


def test_boolean_conditions_need_no_number_in_the_quote():
    rule = RequirementCore(
        parameter="exterior_doors.wheelchair_door_clear_width_mm",
        subject=SUBJECT_OF["exterior_doors.wheelchair_door_clear_width_mm"],
        comparator=">=",
        value=1000,
        unit="mm",
        conditions=[
            Condition(variable="exterior_doors.wheelchair_door_level_access", op="==", value=1)
        ],
    )
    quote = "shall have a minimum clear useable width of 1 000 mm when open"
    result, _ = run(
        door_draft(quote=quote, rule=rule),
        parameter="exterior_doors.wheelchair_door_clear_width_mm",
    )
    assert result.status == "found"


def test_a_table_is_verified_against_every_bound_and_value():
    bands = [
        Band(upper=30, upper_inclusive=False, value=1),
        Band(lower=30, upper=205, value=2),
        Band(lower=205, lower_inclusive=False, upper=300, value=3),
        Band(lower=300, lower_inclusive=False, value=4),
    ]
    rule = RequirementCore(
        parameter="wheelchair_spaces",
        subject=SUBJECT_OF["wheelchair_spaces"],
        comparator=">=",
        bands=bands,
        band_variable="unit_length_m",
    )
    quote = TABLE[TABLE.index("Less than 30 m") :]
    draft = RequirementDraft(found=True, passage_id=TABLE_PASSAGE.id, quote=quote, rule=rule)
    result, _ = run(draft, passages=(TABLE_PASSAGE,), parameter="wheelchair_spaces")
    assert result.status == "found"
    assert len(result.requirement.bands) == 4


def test_a_table_with_an_invented_bound_is_unverified():
    bands = [Band(upper=40, upper_inclusive=False, value=1), Band(lower=40, value=2)]
    rule = RequirementCore(
        parameter="wheelchair_spaces",
        subject=SUBJECT_OF["wheelchair_spaces"],
        comparator=">=",
        bands=bands,
        band_variable="unit_length_m",
    )
    quote = TABLE[TABLE.index("Less than 30 m") :]
    draft = RequirementDraft(found=True, passage_id=TABLE_PASSAGE.id, quote=quote, rule=rule)
    result, _ = run(draft, passages=(TABLE_PASSAGE,), parameter="wheelchair_spaces")
    assert result.status == "unverified"
    assert "40" in result.reason


def test_quote_may_skip_text_with_an_ellipsis_but_each_part_must_be_verbatim():
    ok = door_draft(quote="All exterior passenger doorways shall have ... width of 800 mm")
    assert run(ok)[0].status == "found"
    bad = door_draft(
        quote="All exterior passenger doorways shall have ... width of 800 millimetres"
    )
    assert run(bad)[0].status == "unverified"


def test_curly_and_straight_quotes_and_dashes_match():
    p = passage("(1) The ‘step location’ shall be 800 mm — measured at the nose.")
    rule = RequirementCore(
        parameter="steps.external_step_height_mm",
        subject=SUBJECT_OF["steps.external_step_height_mm"],
        comparator="<=",
        value=800,
    )
    draft = RequirementDraft(
        found=True,
        passage_id=p.id,
        quote="The 'step location' shall be 800 mm - measured at the nose.",
        rule=rule,
    )
    assert run(draft, passages=(p,), parameter="steps.external_step_height_mm")[0].status == "found"


def test_numbers_in():
    assert numbers_in("1 000 mm") == {1000.0}
    assert numbers_in("1 450 mm and 50 mm") == {1450.0, 50.0}
    assert numbers_in("30 to 205 metres | 2 wheelchair spaces") == {30.0, 205.0, 2.0}
    assert numbers_in("a depth of 0,5 m or 2.5 m") == {0.5, 2.5}
    assert numbers_in("no digits here") == set()


# --- focus, number words and existence rules ------------------------------------------------

TOILET = passage(
    "(1) When toilets are fitted in a train, a universal toilet shall be provided accessible "
    "from the wheelchair space.\n(2) The standard toilet shall be compliant with the "
    "requirements of points 5.3.2.2 and 5.3.2.3.",
    id_="tsi-prm:Annex §4.2.2.5#1",
    section="Annex §4.2.2.5",
)


def toilet_draft(**over) -> RequirementDraft:
    rule = RequirementCore(
        parameter="toilets.universal",
        subject=SUBJECT_OF["toilets.universal"],
        comparator=">=",
        value=1,
        conditions=[Condition(variable="toilets.fitted", op=">", value=0)],
    )
    fields = {
        "found": True,
        "passage_id": TOILET.id,
        "quote": "When toilets are fitted in a train, a universal toilet shall be provided",
        "rule": rule,
    }
    return RequirementDraft(**{**fields, **over})


def test_an_existence_rule_with_an_article_is_verified_as_at_least_one():
    result, _ = run(toilet_draft(), passages=(TOILET,), parameter="toilets.universal")
    assert result.status == "found"
    assert result.requirement.value == 1


def test_the_article_only_counts_as_one_for_a_shall_be_provided_rule():
    rule = RequirementCore(
        parameter="exterior_doors.clear_width_mm",
        subject=SUBJECT_OF["exterior_doors.clear_width_mm"],
        comparator=">=",
        value=1,
        unit="mm",
    )
    result, _ = run(door_draft(rule=rule))  # quote: "...minimum clear useable width of 800 mm"
    assert result.status == "unverified"


def test_number_words_count_as_numbers():
    assert numbers_in("not less than two wheelchair spaces") == {2.0}
    assert numbers_in("One step and Ten doors") == {1.0, 10.0}
    assert numbers_in("someone, nonetheless") == set()  # words inside other words do not count


def test_focus_is_passed_to_the_model():
    llm = FakeLLM(door_draft())
    extract_requirement(
        [DOOR_PASSAGE],
        "exterior_doors.clear_width_mm",
        llm,
        focus="the rule for ordinary doorways, not wheelchair doors",
    )
    assert "ordinary doorways" in llm.calls[0][1]


def test_without_focus_the_prompt_has_no_focus_line():
    _, llm = run(door_draft())
    assert "Focus" not in llm.calls[0][1]


# --- malformed model output (seen in the first real run) --------------------------------------


def lenient_rule(**fields) -> RuleDraft:
    return RuleDraft(
        **{
            "parameter": "wheelchair_spaces",
            "subject": "wheelchair_space",
            "comparator": ">=",
            **fields,
        }
    )


def test_a_rule_with_both_value_and_bands_is_unverified_not_a_crash():
    # Gemini returned this for Table 5: a single value AND one band
    rule = lenient_rule(
        value=1,
        bands=[BandDraft(upper=30, upper_inclusive=False, value=1)],
        band_variable="unit_length_m",
    )
    draft = RequirementDraft(
        found=True,
        passage_id=TABLE_PASSAGE.id,
        quote="Less than 30 m | 1 wheelchair space",
        rule=rule,
    )
    result, _ = run(draft, passages=(TABLE_PASSAGE,), parameter="wheelchair_spaces")
    assert result.status == "unverified"
    assert "malformed" in result.reason
    assert "exactly one of" in result.reason


def test_a_band_with_lower_above_upper_is_unverified():
    rule = lenient_rule(
        bands=[BandDraft(lower=300, upper=30, value=1)], band_variable="unit_length_m"
    )
    draft = RequirementDraft(
        found=True,
        passage_id=TABLE_PASSAGE.id,
        quote="Less than 30 m | 1 wheelchair space",
        rule=rule,
    )
    result, _ = run(draft, passages=(TABLE_PASSAGE,), parameter="wheelchair_spaces")
    assert result.status == "unverified"
    assert "malformed" in result.reason


def test_the_system_prompt_tells_the_model_to_give_a_whole_table():
    from rail_compliance.tools.extract import SYSTEM

    assert "every row" in SYSTEM
    assert "to null" in " ".join(SYSTEM.split())


# --- conditions are checked by the kind of parameter they refer to (first real run) -----------


def toilet_rule(*conditions, **over) -> RequirementDraft:
    rule = RequirementCore(
        parameter="toilets.universal",
        subject=SUBJECT_OF["toilets.universal"],
        comparator=">=",
        value=1,
        conditions=list(conditions),
    )
    return toilet_draft(rule=rule, **over)


def run_toilet(draft):
    return run(draft, passages=(TOILET,), parameter="toilets.universal")[0]


def test_a_count_compared_with_equals_one_is_unverified_when_the_quote_never_says_one():
    # The model read "when toilets are fitted" as `toilets.fitted == 1`: wrong for a count
    result = run_toilet(toilet_rule(Condition(variable="toilets.fitted", op="==", value=1)))
    assert result.status == "unverified"
    assert "toilets.fitted" in result.reason
    assert "1" in result.reason


@pytest.mark.parametrize(
    "condition",
    [
        Condition(variable="toilets.fitted", op=">", value=0),
        Condition(variable="toilets.fitted", op=">=", value=1),
    ],
)
def test_existence_of_a_count_is_greater_than_zero_and_needs_no_number_in_the_quote(condition):
    assert run_toilet(toilet_rule(condition)).status == "found"


def test_a_count_threshold_must_be_stated_in_the_quote():
    result = run_toilet(toilet_rule(Condition(variable="toilets.fitted", op=">", value=3)))
    assert result.status == "unverified"
    assert "3" in result.reason


def test_a_boolean_parameter_takes_only_zero_or_one():
    bad = Condition(variable="exterior_doors.wheelchair_door_level_access", op="==", value=2)
    result = run_toilet(toilet_rule(bad))
    assert result.status == "unverified"
    assert "true/false" in result.reason


def test_a_condition_on_an_unknown_parameter_is_unverified():
    result = run_toilet(toilet_rule(Condition(variable="toilets.size", op=">", value=0)))
    assert result.status == "unverified"
    assert "toilets.size" in result.reason


def test_a_band_variable_that_is_not_a_spec_parameter_is_unverified():
    bands = [Band(upper=30, upper_inclusive=False, value=1), Band(lower=30, value=2)]
    rule = RequirementCore(
        parameter="wheelchair_spaces",
        subject=SUBJECT_OF["wheelchair_spaces"],
        comparator=">=",
        bands=bands,
        band_variable="train_length",
    )
    quote = TABLE[TABLE.index("Less than 30 m") :]
    draft = RequirementDraft(found=True, passage_id=TABLE_PASSAGE.id, quote=quote, rule=rule)
    result, _ = run(draft, passages=(TABLE_PASSAGE,), parameter="wheelchair_spaces")
    assert result.status == "unverified"
    assert "train_length" in result.reason


def test_the_prompt_says_which_parameters_are_flags_counts_and_numbers():
    _, llm = run(door_draft())
    user = llm.calls[0][1]
    assert "toilets.fitted (count)" in user
    assert "exterior_doors.wheelchair_door_level_access (true/false" in user
    assert "design_speed_kmh (number, km/h)" in user


def test_the_prompt_says_a_table_is_one_rule_and_focus_selects_the_rule():
    from rail_compliance.tools.extract import SYSTEM

    assert "one rule" in SYSTEM.lower()
    assert "fitted" in SYSTEM  # the worked meaning of an existence condition on a count
    assert "Focus" in SYSTEM


# --- subject, qualifier and contingency (run 01: causes A, B, C, D) ----------------------------

WC = "exterior_doors.wheelchair_door_clear_width_mm"
CLEAR = "exterior_doors.clear_width_mm"
WHEELCHAIR_QUOTE = (
    "On trains with a design speed lower than 250 km/h, wheelchair access doors offering a level "
    "access as defined in point 2.3 shall have a minimum clear useable width of 1 000 mm when open"
)


def door_rule(parameter, subject, value=800, quote=QUOTE_800, **fields):
    rule = RequirementCore(
        parameter=parameter, subject=subject, comparator=">=", value=value, unit="mm", **fields
    )
    return RequirementDraft(found=True, passage_id=DOOR_PASSAGE.id, quote=quote, rule=rule)


def test_a_rule_for_a_narrower_subject_does_not_govern_the_broader_parameter():
    # run 01 g08: the wheelchair-door rule was applied to the narrowest-doorway parameter
    wheelchair_rule = door_rule(CLEAR, "wheelchair_doorway", 1000, WHEELCHAIR_QUOTE)
    result, _ = run(wheelchair_rule, parameter=CLEAR)
    assert result.status == "unverified"
    assert "wheelchair_doorway" in result.reason and "exterior_doorway" in result.reason


def test_a_rule_for_a_broader_subject_governs_the_narrower_parameter():
    # run 01 g11-g13: the rule for ALL exterior doorways also governs the wheelchair doorways
    result, _ = run(door_rule(WC, "exterior_doorway"), parameter=WC)
    assert result.status == "found"
    assert result.requirement.subject == "exterior_doorway"
    assert result.requirement.parameter == WC


def test_a_rule_for_the_parameters_own_subject_is_accepted():
    result, _ = run(door_rule(WC, "wheelchair_doorway", 1000, WHEELCHAIR_QUOTE), parameter=WC)
    assert result.status == "found"


def test_an_unknown_subject_is_unverified_and_the_reason_lists_the_valid_ones():
    result, _ = run(door_rule(CLEAR, "doors"), parameter=CLEAR)
    assert result.status == "unverified"
    assert "doors" in result.reason and "exterior_doorway" in result.reason


def test_the_prompt_states_which_subjects_govern_the_parameter():
    _, llm = run(door_rule(WC, "exterior_doorway"), parameter=WC)
    user = llm.calls[0][1]
    assert "wheelchair_doorway" in user and "exterior_doorway" in user
    assert "also governs" in user or "also govern" in user
    _, llm = run(door_rule(CLEAR, "exterior_doorway"), parameter=CLEAR)
    assert "wheelchair_doorway (" in llm.calls[0][1]  # listed in the vocabulary...
    assert "Subjects whose rules govern this parameter: exterior_doorway" in llm.calls[0][1]


@pytest.mark.parametrize("variable", ["length_includes_power_head"])
def test_a_condition_on_a_qualifier_is_unverified(variable):
    # run 01 g04/g05/g20: "excluding the locomotive or power head" became a condition on the flag
    rule = door_rule(
        WC, "exterior_doorway", conditions=[Condition(variable=variable, op="==", value=0)]
    )
    result, _ = run(rule, parameter=WC)
    assert result.status == "unverified"
    assert "qualifier" in result.reason and "unit_length_m" in result.reason


def test_a_table_may_not_be_selected_by_a_qualifier():
    bands = [Band(upper=30, upper_inclusive=False, value=1), Band(lower=30, value=2)]
    rule = RequirementCore(
        parameter="wheelchair_spaces", subject="wheelchair_space", comparator=">=", bands=bands,
        band_variable="length_includes_power_head",
    )  # fmt: skip
    quote = TABLE[TABLE.index("Less than 30 m") :]
    draft = RequirementDraft(found=True, passage_id=TABLE_PASSAGE.id, quote=quote, rule=rule)
    result, _ = run(draft, passages=(TABLE_PASSAGE,), parameter="wheelchair_spaces")
    assert result.status == "unverified" and "qualifier" in result.reason


def test_qualifiers_are_not_offered_as_variables_in_the_prompt():
    _, llm = run(door_rule(CLEAR, "exterior_doorway"), parameter=CLEAR)
    variables = llm.calls[0][1].split("Passages:")[0]
    assert "length_includes_power_head" not in variables
    assert "unit_length_m" in variables


STEP_PASSAGE = passage(
    "(2) Internal steps for external access shall have a minimum depth of 240 mm between the "
    "vertical edges of the step and a maximum height of 200 mm. The height of each step may be "
    "increased to a maximum of 230 mm if it can be demonstrated that this achieves a reduction "
    "of one in the total number of steps required.",
    id_="tsi-prm:Annex §4.2.2.11.2#1",
    section="Annex §4.2.2.11.2",
)
EXCEPTION_QUOTE = (
    "The height of each step may be increased to a maximum of 230 mm if it can be demonstrated "
    "that this achieves a reduction of one in the total number of steps required."
)


def exception_draft(contingency):
    rule = RequirementCore(
        parameter="steps.internal_step_height_mm", subject="internal_step", comparator="<=",
        value=230, unit="mm", contingency=contingency,
    )  # fmt: skip
    return RequirementDraft(
        found=True, passage_id=STEP_PASSAGE.id, quote=EXCEPTION_QUOTE, rule=rule
    )


def test_an_exception_keeps_its_contingency_on_the_requirement():
    # run 01 g03/g16: the 230 mm exception was extracted as an unconditional rule
    draft = exception_draft("a demonstrated reduction of one in the total number of steps")
    result, _ = run(draft, passages=(STEP_PASSAGE,), parameter="steps.internal_step_height_mm")
    assert result.status == "found"
    assert (
        result.requirement.contingency
        == "a demonstrated reduction of one in the total number of steps"
    )


def test_a_contingency_the_quote_does_not_support_is_unverified():
    draft = exception_draft("an inspection by the national authority")
    draft = draft.model_copy(update={"quote": "a maximum height of 200 mm"})
    result, _ = run(draft, passages=(STEP_PASSAGE,), parameter="steps.internal_step_height_mm")
    assert result.status == "unverified"
    assert "contingency" in result.reason


# --- found by the first full CI run: "a universal toilet shall be provided" read as "no number" ---


def normalised_system():
    from rail_compliance.tools.extract import SYSTEM

    return " ".join(SYSTEM.split())


def test_the_prompt_says_that_shall_be_provided_states_a_minimum_of_one():
    text = normalised_system()
    assert '"shall be provided"' in text and "minimum of one" in text
    assert "value` 1" in text and '">="' in text
    assert "not a case of" in text and "no numeric requirement" in text


def test_that_instruction_comes_before_the_not_found_rule_so_it_is_not_overridden():
    text = normalised_system()
    assert text.index("minimum of one") < text.index("set `found` to false")


def test_the_rule_the_prompt_asks_for_is_exactly_what_the_verifier_accepts():
    """The prompt and the verifier must agree: value 1, comparator >=, quoting the sentence."""
    draft = toilet_rule(Condition(variable="toilets.fitted", op=">", value=0))
    result = run_toilet(draft)
    assert result.status == "found"
    assert result.requirement.value == 1 and result.requirement.comparator == ">="
    assert "shall be provided" in result.requirement.citation.quote


def test_an_unfocused_extraction_gets_the_same_instruction():
    # run 01 of CI: the agent called extraction with no focus; the instruction is in the system
    # prompt, so it does not depend on how the agent words the call
    _, llm = run(toilet_rule(Condition(variable="toilets.fitted", op=">", value=0)),
                 passages=(TOILET,), parameter="toilets.universal")  # fmt: skip
    system, user, _schema = llm.calls[0]
    assert "minimum of one" in system and "Focus:" not in user
