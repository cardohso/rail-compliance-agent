"""Runs the real rail_rag retrieval. Skipped unless the `local` group is installed and the
rail-regulation-rag data folder (RAIL_RAG_DATA_DIR) has a built index, so CI's offline job skips it.
"""

import pytest

pytest.importorskip("rail_rag")

from rail_compliance.config import get_settings  # noqa: E402
from rail_compliance.tools.search import LocalBackend, SearchError, search_regulation  # noqa: E402


@pytest.fixture(scope="module")
def backend():
    try:
        return LocalBackend.from_rail_rag(get_settings().rail_rag_data_dir)
    except SearchError as exc:
        pytest.skip(str(exc))


@pytest.mark.parametrize(
    ("question", "section"),
    [
        ("minimum number of wheelchair spaces per unit length", "Annex §4.2.2.2"),
        ("minimum clear usable width of exterior passenger doors", "Annex §4.2.2.3.2"),
        ("maximum height of external access step", "Annex §4.2.2.11.2"),
    ],
)
def test_real_retrieval_finds_the_right_prm_section(backend, question, section):
    result = search_regulation(question, backend, k=5)
    assert result.backend == "local"
    assert result.answer is None
    assert len(result.passages) == 5
    assert section in [p.section for p in result.passages[:3]]
    top = result.passages[0]
    assert top.url.startswith("https://eur-lex.europa.eu/")
    assert top.text


def test_real_corpus_text_passes_extraction_verification(backend):
    """The quotes a model would copy from real passages must verify against the real text."""
    from rail_compliance.models import Condition, RequirementCore, RequirementDraft
    from rail_compliance.tools.extract import extract_requirement

    result = search_regulation(
        "minimum clear useable width of exterior passenger doorways", backend
    )
    doors = next(p for p in result.passages if p.id == "tsi-prm:Annex §4.2.2.3.2#1")

    class Canned:
        def __init__(self, draft):
            self.draft = draft

        def extract(self, system, user, schema):
            return self.draft

    general = RequirementDraft(
        found=True,
        passage_id=doors.id,
        quote="All exterior passenger doorways shall have a minimum clear useable width of 800 mm",
        rule=RequirementCore(
            parameter="exterior_doors.clear_width_mm",
            subject="exterior_doorway",
            comparator=">=",
            value=800,
            unit="mm",
        ),
    )
    slow = RequirementDraft(
        found=True,
        passage_id=doors.id,
        quote="On trains with a design speed lower than 250 km/h, wheelchair access doors offering "
        "a level access as defined in point 2.3 shall have a minimum clear useable width of "
        "1 000 mm when open",
        rule=RequirementCore(
            parameter="exterior_doors.wheelchair_door_clear_width_mm",
            subject="wheelchair_doorway",
            comparator=">=",
            value=1000,
            unit="mm",
            conditions=[Condition(variable="design_speed_kmh", op="<", value=250)],
        ),
    )
    for draft in (general, slow):
        found = extract_requirement([doors], draft.rule.parameter, Canned(draft))
        assert found.status == "found", found.reason
        assert found.requirement.citation.url.startswith("https://eur-lex.europa.eu/")
