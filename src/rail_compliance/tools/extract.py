"""`extract_requirement`: pull the numeric rule for one parameter out of cited passages.

The LLM proposes a typed rule plus the exact words it came from. This tool then verifies the
proposal without the LLM: the passage must exist, the quote must appear in it word for word, and
every number in the rule (value, band bounds, condition thresholds) must appear in the quote. A
rule that fails verification is returned as `unverified`, never as a requirement, so the agent
cannot pass an invented number to `check`.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Protocol, TypeVar

from pydantic import BaseModel

from rail_compliance.models import (
    Citation,
    ExtractionResult,
    Passage,
    Requirement,
    RequirementDraft,
)
from rail_compliance.spec import parameter_info

T = TypeVar("T", bound=BaseModel)

SYSTEM = """\
You extract one numeric requirement from passages of EU railway law (TSI).

Rules:
- Extract only the requirement for the parameter you are asked about. Do not infer, convert or
  round: use the number and unit as the passage states them.
- Copy the words that state the rule into `quote`, word for word from ONE passage, and give that
  passage's id in `passage_id`. You may use "..." to skip text, but each part must be verbatim.
- `comparator` is how the spec value must relate to the required value: "at least" or "minimum"
  is ">=", "at most" or "maximum" is "<=".
- A rule that applies only in some cases (for example "on trains with a design speed lower than
  250 km/h") goes in `conditions`, using only the spec parameters listed in the request. Express
  true/false parameters as 1/0.
- A table whose required value depends on another parameter (for example unit length) goes in
  `bands`, one band per row, with `band_variable` naming the spec parameter that selects the row.
  Mind inclusive/exclusive bounds: "less than 30 m" excludes 30, "30 to 205 metres" includes both.
- If the passages do not state a number for this parameter (they refer to an external standard,
  describe something else, or are ambiguous), set `found` to false and explain in `note`.
"""

_DASHES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "−": "-"})
_NUMBER = re.compile(r"\d{1,3}(?: \d{3})+(?!\d)(?:[.,]\d+)?|\d+(?:[.,]\d+)?")


class StructuredLLM(Protocol):
    def extract(self, system: str, user: str, schema: type[T]) -> T:
        """Return the model's answer parsed into `schema`."""


def _norm(text: str) -> str:
    text = text.translate(_DASHES)
    text = re.sub(r"[   ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def numbers_in(text: str) -> set[float]:
    """Numbers written in the text, reading "1 000" (a space as thousands separator) as 1000."""
    out = set()
    for token in _NUMBER.findall(_norm(text)):
        digits = token.replace(" ", "").replace(",", ".")
        out.add(float(digits))
    return out


def _quote_in(quote: str, passage_text: str) -> bool:
    haystack = _norm(passage_text)
    parts = [p for p in re.split(r"\.\.\.|…", quote) if _norm(p)]
    return bool(parts) and all(_norm(p) in haystack for p in parts)


def _prompt(parameter: str, passages: Sequence[Passage]) -> str:
    info = parameter_info()
    unit, description = info.get(parameter, (None, ""))
    variables = "\n".join(
        f"- {path}" + (f" ({u})" if u else "") + f": {d}" for path, (u, d) in info.items()
    )
    blocks = "\n\n".join(f"[{p.id}] {p.document}, {p.section}\n{p.text}" for p in passages)
    return (
        f"Parameter: {parameter}" + (f" (unit: {unit})" if unit else "") + f"\n{description}\n\n"
        f"Spec parameters you may use in conditions and bands:\n{variables}\n\n"
        f"Passages:\n{blocks}"
    )


def _unverified(reason: str) -> ExtractionResult:
    return ExtractionResult(status="unverified", reason=reason)


def extract_requirement(
    passages: Sequence[Passage], parameter: str, llm: StructuredLLM
) -> ExtractionResult:
    if not passages:
        return ExtractionResult(status="not_found", reason="no passages were given")
    draft = llm.extract(SYSTEM, _prompt(parameter, passages), RequirementDraft)

    if not draft.found:
        return ExtractionResult(
            status="not_found", reason=draft.note or "the model found no requirement"
        )
    if draft.rule is None or not draft.quote or not draft.passage_id:
        return _unverified("the model said it found a rule but gave no rule, quote or passage")
    rule = draft.rule
    if rule.parameter != parameter:
        return _unverified(f"the model extracted a rule for {rule.parameter}, not for {parameter}")
    source = next((p for p in passages if p.id == draft.passage_id), None)
    if source is None:
        return _unverified(f"passage {draft.passage_id} is not one of the passages given")
    if not _quote_in(draft.quote, source.text):
        return _unverified(f"the quote was not found in the passage {source.id}")

    stated = numbers_in(draft.quote)
    claimed = [rule.value] if rule.value is not None else []
    for band in rule.bands:
        claimed += [band.value, band.lower, band.upper]
    claimed += [c.value for c in rule.conditions if c.value not in (0.0, 1.0)]  # 1/0 = booleans
    missing = sorted({x for x in claimed if x is not None and x not in stated})
    if missing:
        shown = ", ".join(f"{x:g}" for x in missing)
        return _unverified(f"the number(s) {shown} are not stated in the quote")

    citation = Citation(
        passage_id=source.id,
        doc_id=source.doc_id,
        document=source.document,
        section=source.section,
        url=source.url,
        quote=draft.quote,
    )
    requirement = Requirement(**rule.model_dump(), citation=citation)
    return ExtractionResult(
        status="found", reason=f"verified against {source.id}", requirement=requirement
    )
