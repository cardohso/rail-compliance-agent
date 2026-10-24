"""Typed objects passed between the agent's tools.

A `Requirement` is the numeric rule pulled from a cited passage. `check` compares a spec value
against it with no LLM involved, so everything `check` needs (value or bands, comparator, unit,
conditions) is a field here and nothing is left to free text.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Comparator = Literal[">=", "<=", "==", ">", "<"]
# Verdicts the report shows are pass / fail / needs_human. `not_applicable` is internal: a
# conditional rule whose condition is false for this spec (the agent moves on to the next rule).
Verdict = Literal["pass", "fail", "needs_human", "not_applicable"]
HumanReason = Literal["ambiguous_law", "missing_data", "weak_citation", "other"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Passage(_Strict):
    """A passage of regulation text, as returned by the rail assistant."""

    id: str  # "<doc_id>:<section>#<n>", the rail assistant's citation key
    doc_id: str
    document: str
    section: str
    heading: str = ""
    text: str
    url: str = ""
    score: float = 0.0


class SearchResult(_Strict):
    question: str
    passages: list[Passage]
    backend: str  # "local", "live", "replay": where the passages came from
    answer: str | None = None  # only the live backend has a generated answer
    refused: bool = False  # the rail assistant declined to answer (live backend only)


class Citation(_Strict):
    """Where a requirement comes from: the passage and the verbatim words that state the rule."""

    passage_id: str
    doc_id: str
    document: str
    section: str
    url: str = ""
    quote: str


class Condition(_Strict):
    """The rule applies only when `variable op value`. Booleans are 1 (true) and 0 (false)."""

    variable: str  # a spec parameter path, e.g. "design_speed_kmh"
    op: Comparator
    value: float


class BandDraft(_Strict):
    """A table row as the model proposes it: not yet checked for consistency."""

    lower: float | None = None
    lower_inclusive: bool = True
    upper: float | None = None
    upper_inclusive: bool = True
    value: float


class Band(BandDraft):
    """One row of a table: the required value when the selecting variable falls in this range."""

    @model_validator(mode="after")
    def _ordered(self) -> Band:
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError(f"band lower {self.lower} is above upper {self.upper}")
        return self

    def intersects(self, lo: float, hi: float) -> bool:
        """Does any value in the closed interval [lo, hi] fall in this row?"""
        if self.lower is not None and (
            hi < self.lower or (hi == self.lower and not self.lower_inclusive)
        ):
            return False
        return not (
            self.upper is not None
            and (lo > self.upper or (lo == self.upper and not self.upper_inclusive))
        )

    def contains(self, x: float) -> bool:
        if self.lower is not None and (
            x < self.lower or (x == self.lower and not self.lower_inclusive)
        ):
            return False
        return not (
            self.upper is not None
            and (x > self.upper or (x == self.upper and not self.upper_inclusive))
        )


class RuleDraft(_Strict):
    """A rule as the model proposes it. Parsing it never fails on inconsistency: the extraction
    tool validates it afterwards (as `RequirementCore`) and reports a bad one as unverified."""

    parameter: str  # the spec parameter path the rule constrains, e.g. "wheelchair_spaces"
    subject: str  # what the rule is stated for (see parameters.SUBJECTS), e.g. "exterior_doorway"
    comparator: Comparator  # spec_value <comparator> required
    contingency: str | None = None  # what must be shown for the rule to hold; not a spec value
    value: float | None = None
    unit: str | None = None
    bands: list[BandDraft] = Field(default_factory=list)
    band_variable: str | None = None  # spec parameter path that selects the band
    conditions: list[Condition] = Field(default_factory=list)


class RequirementCore(RuleDraft):
    """The rule itself. Exactly one of `value` (a single limit) or `bands` (a table)."""

    bands: list[Band] = Field(default_factory=list)

    @model_validator(mode="after")
    def _value_xor_bands(self) -> RequirementCore:
        if (self.value is None) == (not self.bands):
            raise ValueError("give exactly one of `value` or `bands`")
        if self.bands and not self.band_variable:
            raise ValueError("`bands` need a `band_variable` to select the band")
        if not self.bands and self.band_variable:
            raise ValueError("`band_variable` is only for `bands`")
        return self


class Requirement(RequirementCore):
    citation: Citation


class CheckResult(_Strict):
    parameter: str
    verdict: Verdict
    reason: str
    spec_value: float | None = None
    required_value: float | None = None
    comparator: Comparator | None = None
    unit: str | None = None
    margin: float | None = None  # spec_value - required_value, in the requirement's unit
    contingency: str | None = None  # the rule holds only if this is shown (see Requirement)


class HumanReview(_Strict):
    """An escalation: something the agent must not decide on its own."""

    parameter: str | None = None
    category: HumanReason
    reason: str


class RequirementDraft(_Strict):
    """What the LLM returns from `extract_requirement`, before the tool verifies it."""

    found: bool
    note: str | None = None  # when not found: why (e.g. "refers to an external standard")
    passage_id: str | None = None
    quote: str | None = None  # copied word for word from the passage
    rule: RuleDraft | None = None


ExtractionStatus = Literal["found", "not_found", "unverified"]


class ExtractionResult(_Strict):
    status: ExtractionStatus
    reason: str
    requirement: Annotated[Requirement | None, Field(default=None)] = None
