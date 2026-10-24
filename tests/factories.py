"""Builders for requirements and passages shared by the tool tests."""

from rail_compliance.models import (
    Band,
    Citation,
    Condition,
    Passage,
    Requirement,
)

CITATION = Citation(
    passage_id="tsi-prm:Annex §4.2.2.2#1",
    doc_id="tsi-prm",
    document="PRM TSI",
    section="Annex §4.2.2.2",
    url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02014R1300-20230928",
    quote="quote",
)


def limit(parameter, comparator, value, unit=None, conditions=(), contingency=None, subject="s"):
    return Requirement(
        parameter=parameter,
        subject=subject,
        comparator=comparator,
        value=value,
        unit=unit,
        conditions=list(conditions),
        contingency=contingency,
        citation=CITATION,
    )


def table5() -> Requirement:
    """PRM TSI 4.2.2.2 Table 5: minimum wheelchair spaces by unit length."""
    return Requirement(
        parameter="wheelchair_spaces",
        subject="wheelchair_space",
        comparator=">=",
        bands=[
            Band(upper=30, upper_inclusive=False, value=1),
            Band(lower=30, upper=205, value=2),
            Band(lower=205, lower_inclusive=False, upper=300, value=3),
            Band(lower=300, lower_inclusive=False, value=4),
        ],
        band_variable="unit_length_m",
        citation=CITATION,
    )


def wheelchair_door_rule() -> Requirement:
    """PRM TSI 4.2.2.3.2 (2): level-access wheelchair doors on trains slower than 250 km/h."""
    return limit(
        "exterior_doors.wheelchair_door_clear_width_mm",
        ">=",
        1000,
        "mm",
        conditions=[
            Condition(variable="design_speed_kmh", op="<", value=250),
            Condition(variable="exterior_doors.wheelchair_door_level_access", op="==", value=1),
        ],
    )


def passage(text: str, id_="tsi-prm:Annex §4.2.2.3.2#1", **kw) -> Passage:
    return Passage(
        id=id_,
        doc_id=kw.get("doc_id", "tsi-prm"),
        document=kw.get("document", "PRM TSI"),
        section=kw.get("section", "Annex §4.2.2.3.2"),
        text=text,
        url=kw.get("url", "https://eur-lex.europa.eu/x"),
        score=kw.get("score", 0.8),
    )
