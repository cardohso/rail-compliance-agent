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
