from rail_compliance.models import Band, Condition, RequirementCore, RequirementDraft
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
        parameter="exterior_doors.clear_width_mm", comparator=">=", value=800, unit="mm"
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
        parameter="exterior_doors.clear_width_mm", comparator=">=", value=900, unit="mm"
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
        parameter="wheelchair_spaces", comparator=">=", bands=bands, band_variable="unit_length_m"
    )
    quote = TABLE[TABLE.index("Less than 30 m") :]
    draft = RequirementDraft(found=True, passage_id=TABLE_PASSAGE.id, quote=quote, rule=rule)
    result, _ = run(draft, passages=(TABLE_PASSAGE,), parameter="wheelchair_spaces")
    assert result.status == "found"
    assert len(result.requirement.bands) == 4


def test_a_table_with_an_invented_bound_is_unverified():
    bands = [Band(upper=40, upper_inclusive=False, value=1), Band(lower=40, value=2)]
    rule = RequirementCore(
        parameter="wheelchair_spaces", comparator=">=", bands=bands, band_variable="unit_length_m"
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
    rule = RequirementCore(parameter="steps.external_step_height_mm", comparator="<=", value=800)
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
