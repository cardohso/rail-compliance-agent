import pytest
from pydantic import ValidationError

from rail_compliance.tools.needs_human import needs_human


def test_returns_a_review_with_category_and_parameter():
    review = needs_human(
        "The rule refers to an external standard that is not in the corpus.",
        parameter="wheelchair_spaces",
        category="ambiguous_law",
    )
    assert review.category == "ambiguous_law"
    assert review.parameter == "wheelchair_spaces"
    assert "external standard" in review.reason


def test_parameter_is_optional_and_category_defaults_to_other():
    review = needs_human("Something the agent cannot decide.")
    assert review.parameter is None
    assert review.category == "other"


@pytest.mark.parametrize("reason", ["", "   ", "\n"])
def test_a_reason_is_required(reason):
    with pytest.raises(ValueError, match="reason"):
        needs_human(reason)


def test_reason_is_stripped():
    assert needs_human("  design speed is missing  ", category="missing_data").reason == (
        "design speed is missing"
    )


def test_unknown_category_is_rejected():
    with pytest.raises(ValidationError):
        needs_human("some reason here", category="lazy")
