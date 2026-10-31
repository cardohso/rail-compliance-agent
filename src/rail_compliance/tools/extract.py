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
    Condition,
    ExtractionResult,
    Passage,
    Requirement,
    RequirementCore,
    RequirementDraft,
)
from rail_compliance.parameters import (
    REGULATION_OF,
    REGULATIONS,
    SUBJECT_OF,
    SUBJECTS,
    accepted_subjects,
)
from rail_compliance.spec import (
    CATEGORY_SECTIONS,
    CATEGORY_TERMS,
    QUALIFIERS,
    condition_variables,
    parameter_choices,
    parameter_info,
    parameter_kinds,
)

T = TypeVar("T", bound=BaseModel)

SYSTEM = """\
You extract one numeric requirement from passages of EU railway law (TSI).

Rules:
- Extract only the requirement for the parameter you are asked about. Do not infer, convert or
  round: use the number and unit as the passage states them.
- If the request has a Focus line, extract exactly the rule it names and ignore other rules in the
  passages, even if they are for the same parameter.
- Label the rule with the `subject` it is STATED for, from the list in the request: a rule stated
  for "all exterior passenger doorways" has subject exterior_doorway even if you are asked about
  wheelchair doors, and a rule stated only for wheelchair access doors has subject
  wheelchair_doorway. Rules for a broader subject also govern a narrower one; never present a
  narrower rule as if it governed the broader parameter.
- Copy the words that state the rule into `quote`, word for word from ONE passage, and give that
  passage's id in `passage_id`. You may use "..." to skip text, but each part must be verbatim.
- `comparator` is how the spec value must relate to the required value: "at least" or "minimum"
  is ">=", "at most" or "maximum" is "<=". A range ("30 mm to 40 mm", "between 430 and 500 mm")
  is ONE rule with comparator "between", the lower bound in `value` and the upper in `value_max`.
  Leave `value_max` null for every other comparator.
- A rule or exception that holds only if something is shown, approved or demonstrated (for
  example "if it can be demonstrated that ...") is not unconditional: say what must be shown in
  `contingency`, in a few words from the quote. Leave `contingency` null for ordinary rules.
- A rule that applies only in some cases (for example "on trains with a design speed lower than
  250 km/h") goes in `conditions`, using only the spec parameters listed in the request. Express
  true/false parameters as 1/0 and only those. A category parameter is tested by name with
  "==" ("on double-deck units": the deck parameter == "double_deck"), using one of the names the
  request lists for it. The request tells you each parameter's type. A
  Never make a condition out of wording that only says how a value is measured ("excluding the
  locomotive or power head"): the spec handles that outside the rules. A
  count is not a flag: "when toilets are fitted" means `toilets.fitted` > 0, never == 1.
  Read the sentence for words that limit the rule to a case ("on each side that is adjacent to
  an obstacle", "on trains with ...", "where ... is fitted"). If a listed spec parameter
  describes that case, the rule needs a condition on it: a rule with no conditions holds for
  every spec.
- A permission to depart from the general rule in some cases ("for double deck trains it is
  permitted to reduce this value to 270 mm") is its own rule: set `relaxes` to true, give the
  relaxed value, and put the cases in `conditions`. Never fold it into the general rule, and
  leave `relaxes` false for every other rule. A permission that holds only if something is shown
  ("if it can be demonstrated that ...") is not a relaxation: it goes in `contingency` with
  `relaxes` false. "Reduce" lowers a minimum and "increase" raises a maximum; name the measure
  the sentence is about (a sentence on the depth is not a rule for the height).
- For a renewed unit, Appendix F says when a rule need not be met ("compliance with point 4.2.2.9
  is only mandatory where existing handrails are being renewed or upgraded"). Give such an
  exemption as its own rule with comparator "exempt", no value, and `conditions` saying when
  compliance is NOT mandatory, always including unit_status == "renewed": here
  unit_status == "renewed" and renewal.handrails_renewed == 0. "Only mandatory if A and B" is two
  exemptions, one for "not A" and one for "not B": extract the one the Focus line names. A part
  that depends on something the spec cannot show ("can be accommodated without structural
  alteration") goes in `contingency`.
- A table is ONE rule: give it in one answer, never one answer per row. A table whose required
  value depends on another parameter (for example unit length) goes in `bands`: one band for
  every row of the table, none left out, and `quote` must contain the whole table. Set `value` to
  null when you give `bands`, and `bands` to an empty list when you give `value`; never both.
  `band_variable` names the spec parameter that selects the row. A table whose rows are
  categories ("EMUs | 65", "Coaches | 64") selects by a category parameter: give each row its
  `category` name from the request and no bounds. Mind inclusive/exclusive bounds:
  "less than 30 m" excludes 30, "30 to 205 metres" includes both.
- A requirement that something "shall be provided", "shall be fitted" or "shall be installed" (for
  example "a universal toilet shall be provided") states a minimum of one: give `value` 1 with
  comparator ">=" and quote that sentence. It is a rule, not a case of "no numeric requirement".
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
    kinds, choices = parameter_kinds(), parameter_choices()
    labels = {"bool": "true/false", "count": "count", "number": "number", "category": "category"}

    def label(path: str, u: str | None) -> str:
        return (
            labels[kinds[path]]
            + (f", {u}" if u else "")
            + (", use 1/0" if kinds[path] == "bool" else "")
            + (f", one of {' / '.join(choices[path])}" if kinds[path] == "category" else "")
        )

    allowed = set(condition_variables())
    variables = "\n".join(
        f"- {path} ({label(path, u)}): {d}" for path, (u, d) in info.items() if path in allowed
    )
    vocabulary = "\n".join(f"- {name} ({text})" for name, text in SUBJECTS.items())
    governing = accepted_subjects(parameter) if parameter in SUBJECT_OF else []
    subjects = f"Subjects whose rules govern this parameter: {', '.join(governing)}"
    if len(governing) > 1:
        subjects += (
            f" (a rule for {', '.join(governing[1:])} also governs it, because it is a kind of "
            f"{governing[1]})"
        )
    blocks = "\n\n".join(f"[{p.id}] {p.document}, {p.section}\n{p.text}" for p in passages)
    focus_line = f"Focus: {focus}\n\n" if focus else ""
    return (
        f"Parameter: {parameter}"
        + (f" (unit: {unit})" if unit else "")
        + f"\n{description}\n\n"
        + focus_line
        + f"Rule subjects:\n{vocabulary}\n{subjects}\n\n"
        + f"Spec parameters you may use in conditions and bands:\n{variables}\n\n"
        f"Passages:\n{blocks}"
    )


def _is_existence(cond) -> bool:
    """`count > 0` and `count >= 1` say "there is at least one"; `== 0` and `< 1` say "none"."""
    return (cond.op, cond.value) in {(">", 0.0), (">=", 1.0), ("==", 0.0), ("<", 1.0)}


def _category_stated(value: str, quote: str, section: str = "") -> bool:
    """Is the category named in the quote? "double_deck" matches "double-deck" and "double deck";
    a value with regulation wording (CATEGORY_TERMS) matches any of its stems, and a quote from a
    section about that value (CATEGORY_SECTIONS) states it."""
    if any(section.startswith(s) for s in CATEGORY_SECTIONS.get(value, ())):
        return True
    if value in CATEGORY_TERMS:
        stems = "|".join(re.escape(t) for t in CATEGORY_TERMS[value])
        return re.search(rf"\b(?:{stems})\w*", _norm(quote), re.IGNORECASE) is not None
    words = [re.escape(w) for w in value.split("_")]
    return (
        re.search(r"\b" + r"[\s\-]?".join(words) + r"\b", _norm(quote), re.IGNORECASE) is not None
    )


def _check_variables(
    rule: RequirementCore,
    kinds: dict[str, str],
    choices: dict[str, tuple[str, ...]] | None = None,
) -> str | None:
    """Conditions and tables may only use real spec parameters, the way their type allows."""
    choices = parameter_choices() if choices is None else choices
    names = [c.variable for c in rule.conditions] + ([rule.band_variable] if rule.bands else [])
    for name in names:
        if name in QUALIFIERS:
            return (
                f"{name} is a qualifier of {QUALIFIERS[name]} (it says how the value was "
                "measured), not a circumstance that selects a rule: leave it out"
            )
        if name not in kinds:
            return f"the rule refers to {name}, which is not a spec parameter"
    if rule.bands and rule.bands[0].category is not None:
        options = choices.get(rule.band_variable, ())
        if not options:
            return f"{rule.band_variable} is not a category, so a table cannot have a row per name"
        unknown = [b.category for b in rule.bands if b.category not in options]
        if unknown:
            return f"{rule.band_variable} has no value {unknown[0]!r}. Valid: {', '.join(options)}"
    elif rule.bands and kinds[rule.band_variable] == "category":
        return f"{rule.band_variable} is a category: give each row its `category`, not a range"
    for cond in rule.conditions:
        is_category = kinds[cond.variable] == "category"
        if is_category and not isinstance(cond.value, str):
            options = ", ".join(choices.get(cond.variable, ()))
            return f"{cond.variable} is a category: test it by name ({options}), not a number"
        if isinstance(cond.value, str):
            if not is_category:
                return (
                    f"{cond.variable} is a {kinds[cond.variable]}: test it with a number, "
                    f"not '{cond.value}'"
                )
            if cond.value not in choices.get(cond.variable, ()):
                options = ", ".join(choices.get(cond.variable, ()))
                return f"{cond.variable} has no value '{cond.value}'. Valid: {options}"
            continue
        if kinds[cond.variable] == "bool" and cond.value not in (0.0, 1.0):
            return f"{cond.variable} is true/false, so its value must be 1 or 0, not {cond.value:g}"
    return None


def _check_subject(rule: RequirementCore, parameter: str) -> str | None:
    """A rule governs a parameter if it is stated for the parameter's subject or a broader one."""
    if rule.subject not in SUBJECTS:
        return f"unknown subject '{rule.subject}'. Valid subjects: {', '.join(SUBJECTS)}"
    if parameter in SUBJECT_OF and rule.subject not in accepted_subjects(parameter):
        valid = ", ".join(accepted_subjects(parameter))
        return (
            f"the rule is stated for '{rule.subject}' ({SUBJECTS[rule.subject]}), which does not "
            f"govern {parameter}. Rules for these subjects do: {valid}"
        )
    return None


_CONDITIONAL = re.compile(
    r"\b(?:if|where|provided|unless|subject to|only when|on condition|in case)\b", re.IGNORECASE
)


_EXEMPTION = re.compile(
    r"\b(?:not mandatory|only mandatory|only required|not required|does not need to be)\b", re.I
)
# A relaxation moves a limit in the permitted direction, and its verb says which way it moves:
# reducing a minimum or increasing a maximum is more permissive; the opposite is stricter.
_REDUCES = re.compile(r"\b(?:reduc\w*|decreas\w*)\b", re.I)  # not "lower": "the lower deck"
_INCREASES = re.compile(r"\b(?:increas\w*)\b", re.I)
_PERMISSION = re.compile(r"\b(?:permitted|allowed|may|can be reduced|can be increased)\b", re.I)


def _relaxation_direction(comparator: str, quote: str) -> str | None:
    """A quote that says 'reduce' cannot relax a maximum, nor 'increase' a minimum."""
    reduces, increases = _REDUCES.search(quote), _INCREASES.search(quote)
    if comparator in ("<=", "<") and reduces and not increases:
        return (
            "the quote reduces the value, but the rule is a maximum: reducing a maximum makes it "
            "stricter, not a relaxation. A permission to reduce applies to a minimum; check which "
            "value the sentence reduces (the sentence may be about another measure)"
        )
    if comparator in (">=", ">") and increases and not reduces:
        return (
            "the quote increases the value, but the rule is a minimum: increasing a minimum makes "
            "it stricter, not a relaxation. A permission to increase applies to a maximum; check "
            "which value the sentence increases"
        )
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
    prompt = _prompt(parameter, passages, focus)
    result = _verify(llm.extract(SYSTEM, prompt, RequirementDraft), passages, parameter)
    if result.status != "unverified":
        return result
    # The verifier rejected the rule. The extraction model is deterministic, so asking again with
    # the same words gives the same rule: it has to be shown why this one was rejected. Once.
    feedback = (
        f"{prompt}\n\nYour previous answer was rejected: {result.reason}.\n"
        "Correct exactly that, or set `found` to false if the passages do not state this rule."
    )
    return _verify(llm.extract(SYSTEM, feedback, RequirementDraft), passages, parameter)


def _verify(
    draft: RequirementDraft, passages: Sequence[Passage], parameter: str
) -> ExtractionResult:
    """Check the model's draft against the passages: the rule is only as good as its quote."""
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
    problem = _check_subject(rule, parameter)
    if problem:
        return _unverified(problem)
    source = next((p for p in passages if p.id == draft.passage_id), None)
    if source is None:
        return _unverified(f"passage {draft.passage_id} is not one of the passages given")
    if not _quote_in(draft.quote, source.text):
        return _unverified(f"the quote was not found in the passage {source.id}")
    regulation = REGULATION_OF.get(parameter)
    if regulation and source.doc_id != regulation:
        return _unverified(
            f"{parameter} is governed by the {REGULATIONS[regulation]} ({regulation}); passage "
            f"{source.id} is from {source.doc_id}, which does not set it"
        )

    kinds = parameter_kinds()
    problem = _check_variables(rule, kinds)
    if problem:
        return _unverified(problem)
    if rule.comparator == "exempt":
        if not _EXEMPTION.search(_norm(draft.quote)):
            return _unverified(
                "the rule is marked as an exemption, but the quote does not say compliance is not "
                "mandatory or only mandatory in some case. Quote that sentence"
            )
        renewed = Condition(variable="unit_status", op="==", value="renewed")
        if renewed not in rule.conditions:
            return _unverified(
                "an exemption of Appendix F holds only for a renewed unit: add the condition "
                "unit_status == renewed"
            )
    if rule.relaxes:
        problem = _relaxation_direction(rule.comparator, _norm(draft.quote))
        if problem:
            return _unverified(problem)
    if rule.relaxes and not _PERMISSION.search(_norm(draft.quote)):
        return _unverified(
            "the rule is marked as a relaxation, but the quote states no permission ('permitted', "
            "'allowed', 'may'). Quote the sentence that permits it or set relaxes to false"
        )
    if rule.contingency and not _CONDITIONAL.search(_norm(draft.quote)):
        return _unverified(
            f"the contingency '{rule.contingency}' is not supported by the quote, which states no "
            "'if', 'where', 'provided' or 'unless'. Either quote the sentence that makes the rule "
            "conditional or leave contingency empty"
        )

    stated = numbers_in(draft.quote)
    rule_numbers = [x for x in (rule.value, rule.value_max) if x is not None]
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
    for band in rule.bands:
        if band.category and not _category_stated(band.category, draft.quote, source.section):
            return _unverified(f"the table row for {band.category} names a category the quote "
                               "does not state")  # fmt: skip
    for cond in rule.conditions:
        if isinstance(cond.value, str):
            if not _category_stated(cond.value, draft.quote, source.section):
                return _unverified(
                    f"the condition {cond.describe()} names a category the quote does not state"
                )
            continue
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
