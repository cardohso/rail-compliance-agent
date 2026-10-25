"""The coverage check: a sentence in a passage the agent used that states another rule on the same
measure, which no extracted rule covers. Found necessary by CI run 2 (g14): the conditional 1000 mm
door rule was never extracted, so an unknown design speed never forced needs_human."""

import pytest

from rail_compliance.models import RequirementCore
from rail_compliance.parameters import CHECKED_PARAMETERS, MEASURES, SUBJECT_TERMS, SUBJECTS
from rail_compliance.tools.coverage import find_gaps, mm_numbers
from tests.factories import limit, passage

CLEAR = "exterior_doors.clear_width_mm"
WC = "exterior_doors.wheelchair_door_clear_width_mm"
INT = "steps.internal_step_height_mm"
EXT = "steps.external_step_height_mm"
UNI_DOOR = "toilets.universal_door_clear_width_mm"

# Text as the rail assistant's corpus holds it (PRM TSI 4.2.2.3.2 (1)-(3); numbered points on lines)
DOORS = passage(
    "(1) All exterior passenger doorways shall have a minimum clear useable width of 800 mm "
    "when open.\n(2) On trains with a design speed lower than 250 km/h, wheelchair access doors "
    "offering a level access as defined in point 2.3 shall have a minimum clear useable width "
    "of 1 000 mm when open.\n(3) All exterior passenger doorways shall be marked on the outside "
    "in a way that gives a contrast to the vehicle body-side surrounding them.",
    id_="tsi-prm:Annex §4.2.2.3.2#1",
)
# 4.2.2.11.2 (2) and (5) (and (8), which names no step by type)
STEPS = passage(
    "(1) All steps for access and egress shall be slip resistant.\n(2) Internal steps for external "
    "access shall have a minimum depth of 240 mm between the vertical edges of the step and a "
    "maximum height of 200 mm. The height of each step may be increased to a maximum of 230 mm "
    "if it can be demonstrated that this achieves a reduction of one in the total number of steps "
    "required.\n(5) An external access step, fixed or moveable, shall have a maximum height of "
    "230 mm between steps and a minimum depth of 150 mm.\n(8) Rolling stock intended to stop, in "
    "normal operation, at existing platforms below 380 mm height and having their passenger "
    "access doors above bogies need not comply with points (2) and (5) above if it can be "
    "demonstrated that this achieves a more even distribution of the steps height.",
    id_="tsi-prm:Annex §4.2.2.11.2#1",
)
TOILET_DOOR = passage(
    "(3) The toilet access door shall provide a minimum clear useable width of 800 mm. Where the "
    "door is automatic or semi-automatic, it shall be possible to open it partially.\n(6) There "
    "shall be a minimum clear space of 700 mm in front of the toilet seat that shall follow the "
    "seat profile.",
    id_="tsi-prm:Annex §5.3.2.4#1",
)


def rule(parameter, value, passage_, subject):
    """A minimum for widths, a maximum for step heights, citing `passage_`."""
    comparator = "<=" if "step" in parameter else ">="
    base = limit(parameter, comparator, value, "mm", subject=subject)
    return base.model_copy(
        update={"citation": base.citation.model_copy(update={"passage_id": passage_.id})}
    )


def gaps(parameter, passages, *rules):
    return find_gaps(parameter, {p.id: p for p in passages}, list(rules))


# --- the case that motivated it ---------------------------------------------------------------


def test_the_conditional_door_rule_is_flagged_when_only_the_general_rule_was_extracted():
    found = gaps(WC, [DOORS], rule(WC, 800, DOORS, "exterior_doorway"))
    assert len(found) == 1
    assert found[0].passage_id == DOORS.id
    assert "1 000 mm" in found[0].sentence and "wheelchair access doors" in found[0].sentence


def test_no_gap_when_both_door_rules_were_extracted():
    both = [rule(WC, 800, DOORS, "exterior_doorway"), rule(WC, 1000, DOORS, "wheelchair_doorway")]
    assert gaps(WC, [DOORS], *both) == []


def test_the_general_rule_is_flagged_when_only_the_special_rule_was_extracted():
    found = gaps(WC, [DOORS], rule(WC, 1000, DOORS, "wheelchair_doorway"))
    assert len(found) == 1 and "All exterior passenger doorways" in found[0].sentence


def test_a_wheelchair_door_rule_is_not_a_gap_for_the_narrowest_doorway():
    # it does not govern CLEAR (subject hierarchy): flagging it would be a false alarm
    assert gaps(CLEAR, [DOORS], rule(CLEAR, 800, DOORS, "exterior_doorway")) == []


# --- the exception ----------------------------------------------------------------------------


def test_the_internal_step_exception_is_flagged_when_only_the_200_mm_rule_was_extracted():
    found = gaps(INT, [STEPS], rule(INT, 200, STEPS, "internal_step"))
    assert len(found) == 1 and "230 mm" in found[0].sentence


def test_no_gap_when_the_exception_was_extracted_too():
    both = [rule(INT, 200, STEPS, "internal_step"), rule(INT, 230, STEPS, "internal_step")]
    assert gaps(INT, [STEPS], *both) == []


def test_the_external_step_does_not_trip_on_the_internal_steps_sentences():
    assert gaps(EXT, [STEPS], rule(EXT, 230, STEPS, "external_step")) == []


def test_a_sentence_that_names_no_step_type_is_not_a_candidate():
    # (8) mentions "380 mm height" and "steps height" but no subject: out of scope, documented
    assert gaps(EXT, [STEPS], rule(EXT, 230, STEPS, "external_step")) == []
    assert (
        gaps(
            INT,
            [STEPS],
            rule(INT, 200, STEPS, "internal_step"),
            rule(INT, 230, STEPS, "internal_step"),
        )
        == []
    )


def test_a_sentence_about_another_measure_is_not_a_candidate():
    # the depth sentence has "240 mm" and "150 mm" but the measure is height
    found = gaps(INT, [STEPS], rule(INT, 200, STEPS, "internal_step"))
    assert all("depth" not in g.sentence or "230 mm" in g.sentence for g in found)


def test_the_toilet_door_rule_is_covered_and_the_unrelated_clearance_is_not_a_candidate():
    assert (
        gaps(UNI_DOOR, [TOILET_DOOR], rule(UNI_DOOR, 800, TOILET_DOOR, "universal_toilet_door"))
        == []
    )


# --- scope and mechanics ----------------------------------------------------------------------


def test_only_passages_the_agent_extracted_a_rule_from_are_inspected():
    other = passage(
        "(1) All exterior passenger doorways shall have a clear useable width of 700 mm.",
        id_="tsi-prm:Annex §9.9#1",
    )
    found = gaps(CLEAR, [DOORS, other], rule(CLEAR, 800, DOORS, "exterior_doorway"))
    assert found == []


def test_nothing_extracted_means_nothing_to_inspect():
    assert gaps(WC, [DOORS]) == []


@pytest.mark.parametrize("parameter", ["wheelchair_spaces", "toilets.universal"])
def test_count_parameters_are_out_of_scope(parameter):
    spaces = passage(
        "(3) Over the full length of the wheelchair space the width shall be 700 mm.",
        id_="tsi-prm:Annex §4.2.2.2#1",
    )
    base = limit(parameter, ">=", 2, subject="wheelchair_space")
    cited = base.citation.model_copy(update={"passage_id": spaces.id})
    r = base.model_copy(update={"citation": cited})
    assert gaps(parameter, [spaces], r) == []


def test_the_same_sentence_is_reported_once():
    a, b = rule(WC, 800, DOORS, "exterior_doorway"), rule(WC, 800, DOORS, "exterior_doorway")
    assert len(gaps(WC, [DOORS], a, b)) == 1


@pytest.mark.parametrize(
    ("text", "numbers"),
    [
        ("width of 1 000 mm when open", {1000.0}),
        ("width of 1 000 mm", {1000.0}),
        ("a depth of 45 mm to 55 mm", {45.0, 55.0}),
        ("0,5 mm and 2.5 mm", {0.5, 2.5}),
        ("lower than 250 km/h", set()),
        ("a gap of 75 mm measured horizontally and 50 mm vertically", {75.0, 50.0}),
    ],
)
def test_mm_numbers(text, numbers):
    assert mm_numbers(text) == numbers


def test_the_registries_cover_exactly_what_they_should():
    assert set(MEASURES) <= set(CHECKED_PARAMETERS)
    assert set(SUBJECT_TERMS) == set(SUBJECTS)
    assert set(MEASURES) == {CLEAR, WC, INT, EXT, UNI_DOOR}  # the mm-valued parameters
    assert all(terms for terms in MEASURES.values()) and all(SUBJECT_TERMS.values())


def test_rule_requirements_are_unchanged_by_the_check():
    requirement = rule(WC, 800, DOORS, "exterior_doorway")
    before = requirement.model_dump()
    gaps(WC, [DOORS], requirement)
    assert requirement.model_dump() == before and isinstance(requirement, RequirementCore)


# --- a missed rule matters only if it could change the verdict ------------------------------------
# Replaying the check over 148 saved real verdicts found 1 catch (g14) and 4 false alarms, all the
# same: spec 180 mm against the 200 mm internal-step limit, with the 230 mm exception not extracted.
# The exception only relaxes the limit, so it cannot undo a pass.


def relevant(parameter, passage_, value, *rules):
    return find_gaps(parameter, {passage_.id: passage_}, list(rules), spec_value=value)


def test_a_stricter_missed_rule_that_the_value_fails_is_relevant():
    found = relevant(WC, DOORS, 900, rule(WC, 800, DOORS, "exterior_doorway"))
    assert len(found) == 1 and "1 000 mm" in found[0].sentence  # 900 < 1000


def test_a_stricter_missed_rule_that_the_value_meets_is_not_relevant():
    assert relevant(WC, DOORS, 1100, rule(WC, 800, DOORS, "exterior_doorway")) == []  # 1100 >= 1000


def test_a_more_lenient_missed_exception_cannot_undo_a_pass_and_is_not_relevant():
    assert relevant(INT, STEPS, 180, rule(INT, 200, STEPS, "internal_step")) == []  # 180 <= 230


def test_a_lenient_exception_beside_a_failing_value_is_still_reported():
    # 215 fails 200 and would pass 230: the exception could rescue it, so it is a gap
    # (the verdict stays fail, as before, but the gap is recorded for the reader)
    comparator_max = limit(INT, "<=", 200, "mm", subject="internal_step")
    cited = comparator_max.citation.model_copy(update={"passage_id": STEPS.id})
    r = comparator_max.model_copy(update={"citation": cited})
    found = relevant(INT, STEPS, 215, r)
    assert len(found) == 1 and "230 mm" in found[0].sentence


def test_without_a_spec_value_every_gap_is_reported():
    assert len(gaps(INT, [STEPS], rule(INT, 200, STEPS, "internal_step"))) == 1
