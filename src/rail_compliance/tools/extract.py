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

from pydantic import BaseModel, ValidationError

from rail_compliance.models import (
    Citation,
    ExtractionResult,
    Passage,
    Requirement,
    RequirementCore,
    RequirementDraft,
)
from rail_compliance.spec import parameter_info, parameter_kinds

T = TypeVar("T", bound=BaseModel)

SYSTEM = """\
You extract one numeric requirement from passages of EU railway law (TSI).

Rules:
- Extract only the requirement for the parameter you are asked about. Do not infer, convert or
  round: use the number and unit as the passage states them.
- If the request has a Focus line, extract exactly the rule it names and ignore other rules in the
  passages, even if they are for the same parameter.
- Copy the words that state the rule into `quote`, word for word from ONE passage, and give that
  passage's id in `passage_id`. You may use "..." to skip text, but each part must be verbatim.
- `comparator` is how the spec value must relate to the required value: "at least" or "minimum"
  is ">=", "at most" or "maximum" is "<=".
- A rule that applies only in some cases (for example "on trains with a design speed lower than
  250 km/h") goes in `conditions`, using only the spec parameters listed in the request. Express
  true/false parameters as 1/0 and only those. The request tells you each parameter's type. A
  count is not a flag: "when toilets are fitted" means `toilets.fitted` > 0, never == 1.
- A table is ONE rule: give it in one answer, never one answer per row. A table whose required
  value depends on another parameter (for example unit length) goes in `bands`: one band for
  every row of the table, none left out, and `quote` must contain the whole table. Set `value` to
  null when you give `bands`, and `bands` to an empty list when you give `value`; never both.
  `band_variable` names the spec parameter that selects the row. Mind inclusive/exclusive bounds:
  "less than 30 m" excludes 30, "30 to 205 metres" includes both.
- If the passages do not state a number for this parameter (they refer to an external standard,
  describe something else, or are ambiguous), set `found` to false and explain in `note`.
"""

_DASHES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "−": "-"})
_NUMBER = re.compile(
    r"\d{1,3}(?: \d{3})+(?!\d)(?:[.,]\d+)?|\d+(?:[.,]\d+)?"
    r"|\b(?:one|two|three|four|five|six|seven|eight|nine|ten)\b",
    re.IGNORECASE,
)
WORDS = {
    w: float(i)
    for i, w in enumerate(
        ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"], 1
    )
}
# "a universal toilet shall be provided": the article is the number 1 only in this construction
_EXISTENCE = re.compile(
    r"\b(?:a|an)\s+[\w\- ]{0,40}?\bshall be (?:provided|fitted|installed)\b", re.IGNORECASE
)


class StructuredOutputError(RuntimeError):
    """The model's reply could not be parsed into the requested schema."""


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
        word = token.lower()
        out.add(WORDS[word] if word in WORDS else float(token.replace(" ", "").replace(",", ".")))
    return out


def _quote_in(quote: str, passage_text: str) -> bool:
    haystack = _norm(passage_text)
    parts = [p for p in re.split(r"\.\.\.|…", quote) if _norm(p)]
    return bool(parts) and all(_norm(p) in haystack for p in parts)


def _prompt(parameter: str, passages: Sequence[Passage], focus: str | None) -> str:
    info = parameter_info()
    unit, description = info.get(parameter, (None, ""))
    kinds = parameter_kinds()
    labels = {"bool": "true/false, use 1/0", "count": "count", "number": "number"}

    def label(path: str, u: str | None) -> str:
        return (
            labels[kinds[path]].split(",")[0]
            + (f", {u}" if u else "")
            + (", use 1/0" if kinds[path] == "bool" else "")
        )

    variables = "\n".join(f"- {path} ({label(path, u)}): {d}" for path, (u, d) in info.items())
    blocks = "\n\n".join(f"[{p.id}] {p.document}, {p.section}\n{p.text}" for p in passages)
    focus_line = f"Focus: {focus}\n\n" if focus else ""
    return (
        f"Parameter: {parameter}"
        + (f" (unit: {unit})" if unit else "")
        + f"\n{description}\n\n"
        + focus_line
        + f"Spec parameters you may use in conditions and bands:\n{variables}\n\n"
        f"Passages:\n{blocks}"
    )


def _is_existence(cond) -> bool:
    """`count > 0` and `count >= 1` both say "there is at least one"."""
    return (cond.op, cond.value) in {(">", 0.0), (">=", 1.0)}


def _check_variables(rule: RequirementCore, kinds: dict[str, str]) -> str | None:
    """Conditions and tables may only use real spec parameters, the way their type allows."""
    names = [c.variable for c in rule.conditions] + ([rule.band_variable] if rule.bands else [])
    for name in names:
        if name not in kinds:
            return f"the rule refers to {name}, which is not a spec parameter"
    for cond in rule.conditions:
        if kinds[cond.variable] == "bool" and cond.value not in (0.0, 1.0):
            return f"{cond.variable} is true/false, so its value must be 1 or 0, not {cond.value:g}"
    return None


def _unverified(reason: str) -> ExtractionResult:
    return ExtractionResult(status="unverified", reason=reason)


def extract_requirement(
    passages: Sequence[Passage], parameter: str, llm: StructuredLLM, focus: str | None = None
) -> ExtractionResult:
    """Extract one rule for `parameter`. A parameter can have several rules (a general minimum and
    a stricter one for some cases): `focus` names the one to extract on this call."""
    if not passages:
        return ExtractionResult(status="not_found", reason="no passages were given")
    draft = llm.extract(SYSTEM, _prompt(parameter, passages, focus), RequirementDraft)

    if not draft.found:
        return ExtractionResult(
            status="not_found", reason=draft.note or "the model found no requirement"
        )
    if draft.rule is None or not draft.quote or not draft.passage_id:
        return _unverified("the model said it found a rule but gave no rule, quote or passage")
    try:
        rule = RequirementCore.model_validate(draft.rule.model_dump())
    except ValidationError as exc:
        problem = exc.errors()[0]["msg"].removeprefix("Value error, ")
        return _unverified(f"the model's rule is malformed: {problem}")
    if rule.parameter != parameter:
        return _unverified(f"the model extracted a rule for {rule.parameter}, not for {parameter}")
    source = next((p for p in passages if p.id == draft.passage_id), None)
    if source is None:
        return _unverified(f"passage {draft.passage_id} is not one of the passages given")
    if not _quote_in(draft.quote, source.text):
        return _unverified(f"the quote was not found in the passage {source.id}")

    kinds = parameter_kinds()
    problem = _check_variables(rule, kinds)
    if problem:
        return _unverified(problem)

    stated = numbers_in(draft.quote)
    rule_numbers = [rule.value] if rule.value is not None else []
    for band in rule.bands:
        rule_numbers += [band.value, band.lower, band.upper]
    # "a universal toilet shall be provided" states the rule's own value as an article, not a digit
    # (this allowance covers the rule's value only, never a condition's).
    if (
        rule.comparator == ">="
        and rule.value == 1
        and not rule.bands
        and _EXISTENCE.search(_norm(draft.quote))
    ):
        rule_numbers.remove(1.0)
    missing = sorted({x for x in rule_numbers if x is not None and x not in stated})
    if missing:
        shown = ", ".join(f"{x:g}" for x in missing)
        return _unverified(f"the number(s) {shown} are not stated in the quote")
    # A flag's 1/0 and a count's "there is at least one" are not numbers the quote has to state.
    for cond in rule.conditions:
        if kinds[cond.variable] != "bool" and not _is_existence(cond) and cond.value not in stated:
            return _unverified(
                f"the condition {cond.variable} {cond.op} {cond.value:g} uses a number the quote "
                "does not state (for 'is fitted' or 'is provided' on a count, use > 0)"
            )

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
