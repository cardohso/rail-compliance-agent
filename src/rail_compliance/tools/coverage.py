"""Coverage check: did the agent extract every rule on this measure from the passages it used?

The verdict is computed from the rules that were extracted, and code cannot otherwise know a rule
is missing. In CI run 2 the agent extracted the general 800 mm door rule twice and never the
conditional 1000 mm rule beside it, so an unknown design speed never forced `needs_human` and the
parameter came out `pass`. This finds that situation deterministically:

- look only at passages the agent extracted a rule from;
- in each numbered point that names a subject governing the parameter (the subject hierarchy:
  a wheelchair doorway is governed by rules for all exterior doorways, not the other way round),
- a sentence that names the parameter's measure and carries a millimetre figure is a candidate;
- it is covered if some extracted rule's value is one of those figures; otherwise it is a gap.

Counts (wheelchair spaces, universal toilets) use "<n> <noun>" and "a <noun> shall be provided" as
figures; a passage that states a whole table of counts must be extracted as a table (every row's
figure covered), because reducing it to one value bypasses the deterministic row selection.

Deliberately narrow: only these seven parameters, only cited passages, and a sentence that names no
subject (for example 4.2.2.11.2 (8), which talks of "steps height" without saying which steps) is
not a candidate. It finds a sibling rule in the same passage; it cannot find one elsewhere.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from rail_compliance.models import Passage, Requirement
from rail_compliance.parameters import MEASURES, SUBJECT_TERMS, accepted_subjects
from rail_compliance.spec import parameter_kinds
from rail_compliance.tools.extract import _norm

_MM = re.compile(r"(\d{1,3}(?: \d{3})+(?!\d)|\d+(?:[.,]\d+)?)\s*mm\b")
_SENTENCE_END = re.compile(r"(?<=[.;])\s+(?=[A-Z(])")


class Gap:
    """A sentence on the same measure that no extracted rule covers."""

    __slots__ = ("passage_id", "sentence")

    def __init__(self, passage_id: str, sentence: str):
        self.passage_id, self.sentence = passage_id, sentence

    def __repr__(self) -> str:
        return f"Gap({self.passage_id!r}, {self.sentence[:60]!r})"


def mm_numbers(text: str) -> set[float]:
    """Figures written in millimetres; "1 000 mm" (a space as thousands separator) reads as 1000."""
    return {float(token.replace(" ", "").replace(",", ".")) for token in _MM.findall(_norm(text))}


_COUNT_WORDS = {
    w: float(i)
    for i, w in enumerate(
        ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"], 1
    )
}


def count_figures(text: str, noun: str) -> set[float]:
    """Counts of `noun` the text states: "2 wheelchair spaces", "two wheelchair spaces", or
    "a universal toilet shall be provided" (one). A number elsewhere in the sentence is not one."""
    text, noun = _norm(text).lower(), re.escape(noun.lower())
    out = {
        _COUNT_WORDS.get(n) or float(n)
        for n in re.findall(
            rf"\b(\d+|{'|'.join(_COUNT_WORDS)})\s+(?:accessible\s+)?{noun}s?\b", text
        )
    }
    if re.search(rf"\b(?:a|an)\s+{noun}\s+shall be (?:provided|fitted|installed)\b", text):
        out.add(1.0)
    return out


def _figures(parameter: str, sentence: str) -> set[float]:
    if parameter_kinds()[parameter] == "count":
        return set().union(*(count_figures(sentence, noun) for noun in MEASURES[parameter]))
    return mm_numbers(sentence)


def _rule_values(requirements: Iterable[Requirement]) -> set[float]:
    values: set[float] = set()
    for r in requirements:
        values.update(float(x) for x in (r.value, r.value_max) if x is not None)
        values.update(float(b.value) for b in r.bands)
    return values


def _matters(
    figures: set[float], spec_value: float, requirements: list[Requirement], values: set[float]
) -> bool:
    """Could a missed rule with these figures change the verdict for this spec value?

    - A stricter missed figure that the value violates can turn a pass into something else.
    - A more lenient one (an exception) cannot undo a pass, so it is irrelevant when the extracted
      rules accept the value; but when they already reject it, an exception could rescue it.
    """
    comparator = requirements[0].comparator
    if comparator == ">=":
        return any(spec_value < f for f in figures) or any(spec_value < v for v in values)
    if comparator == "<=":
        return any(spec_value > f for f in figures) or any(spec_value > v for v in values)
    return True  # other comparators: report, do not guess


def find_gaps(
    parameter: str,
    passages: Mapping[str, Passage],
    requirements: Iterable[Requirement],
    spec_value: float | None = None,
) -> list[Gap]:
    """Sentences on this parameter's measure that no extracted rule covers. With `spec_value`, only
    those that could change the verdict for that value (see `_matters`)."""
    measure_terms = MEASURES.get(parameter)
    requirements = list(requirements)
    if not measure_terms or not requirements:
        return []
    subject_terms = [
        term for subject in accepted_subjects(parameter) for term in SUBJECT_TERMS[subject]
    ]
    values = _rule_values(requirements)
    cited = dict.fromkeys(r.citation.passage_id for r in requirements)

    found: list[Gap] = []
    seen: set[tuple[str, str]] = set()
    for passage_id in cited:
        passage = passages.get(passage_id)
        if passage is None:
            continue
        for point in passage.text.split("\n"):
            point_text = _norm(point)
            if not any(term in point_text.lower() for term in subject_terms):
                continue  # this point is about something else
            for sentence in _SENTENCE_END.split(point_text):
                if not any(term in sentence.lower() for term in measure_terms):
                    continue
                figures = _figures(parameter, sentence)
                if not figures:
                    continue
                if len(figures) > 1 and parameter_kinds()[parameter] == "count":
                    # a table of counts must be extracted as a table: every row's figure covered
                    if figures <= values:
                        continue
                elif figures & values:
                    continue  # an extracted rule already carries this figure
                elif spec_value is not None and not _matters(
                    figures, spec_value, requirements, values
                ):
                    continue
                if (passage_id, sentence) not in seen:
                    seen.add((passage_id, sentence))
                    found.append(Gap(passage_id, sentence))
    return found
