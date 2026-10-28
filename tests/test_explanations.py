import pytest

from rail_compliance.explanations import MAX_CHARS, explanation_problems

G19 = (
    "Unit length (210 m) falls into the boundary of the table bracket (30 to 205 metres vs More "
    "than 205 to 300 metres), but wait—the unit length is 210 m which is 'More than 205 to 300 "
    "metres' (requiring 3 spaces). Wait, 210 m is strictly greater than 205 m."
)


@pytest.mark.parametrize(
    "text",
    [
        "The rule refers to EN 16584-1, which is not in the corpus.",
        "Design speed is not supplied, and 4.2.2.3.2(5) depends on it.",
        "Whether the 230 mm step in 4.2.2.8(2) applies depends on a demonstration the spec "
        "cannot show.",
    ],
)
def test_a_short_single_sentence_has_no_problems(text):
    assert explanation_problems(text) == []


def test_section_numbers_and_units_are_not_sentence_breaks():
    text = "Point 4.2.2.11.2 (8) and Table 5 of Section 4.2.2.2.2.1 give 2 spaces per 30 m."
    assert explanation_problems(text) == []


def test_the_g19_reason_is_flagged_for_every_fault():
    found = explanation_problems(G19)
    assert any("sentences" in p for p in found)
    assert any("self-correction" in p for p in found)


@pytest.mark.parametrize(
    "text", ["Actually, the rule is conditional.", "Let me re-check the table bracket.",
             "Hmm, the passage is unclear.", "Let's re-verify the rule."],
)  # fmt: skip
def test_self_correction_markers_are_flagged(text):
    assert any("self-correction" in p for p in explanation_problems(text))


def test_a_reason_over_the_limit_is_flagged():
    text = "The " + "very " * (MAX_CHARS // 5) + "long reason."
    assert any("characters" in p for p in explanation_problems(text))


def test_the_word_wait_inside_another_word_is_not_a_marker():
    assert explanation_problems("The await period in the rule is not supplied.") == []
