"""What a written explanation must look like: one short sentence, with no thinking out loud.

The agent's escalation reason goes into the report as written, so a reason that reasons ("wait,
210 m is above 205 m ...") is a reason a reviewer has to untangle. `needs_human` rejects such a
reason and the model rewrites it; the evaluation scores the reasons that were recorded. Everything
here is deterministic: a regex, not a judge.
"""

from __future__ import annotations

import re

MAX_CHARS = 300

# A full stop, ! or ? followed by space and a capital letter starts a new sentence. "4.2.2.8" and
# "e.g. the" do not match: the first has no space, the second no capital.
_SENTENCE_BREAK = re.compile(r"[.!?](?=\s+[A-Z])")
_SELF_CORRECTION = re.compile(
    r"\b(wait|actually|hmm|let me|let's|let us|re-?verify|re-?check|on second thought|"
    r"i mean|no,)",
    re.IGNORECASE,
)


def explanation_problems(text: str) -> list[str]:
    """What is wrong with `text` as a recorded explanation; empty when nothing is."""
    text = text.strip()
    problems = []
    if len(text) > MAX_CHARS:
        problems.append(f"{len(text)} characters, more than {MAX_CHARS}")
    if n := len(_SENTENCE_BREAK.findall(text)):
        problems.append(f"{n + 1} sentences, not one sentence")
    if markers := sorted({m.group(0).lower() for m in _SELF_CORRECTION.finditer(text)}):
        problems.append(f"self-correction ({', '.join(repr(m) for m in markers)})")
    return problems
