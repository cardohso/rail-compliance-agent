"""`needs_human`: escalate instead of guessing.

The agent calls this when the law is ambiguous, the rule depends on data the spec does not
supply, or the citation is too weak to rest a verdict on. It is a tool, not a fallthrough, so an
escalation is a recorded action that the evaluation can score for precision and recall.
"""

from __future__ import annotations

from rail_compliance.explanations import explanation_problems
from rail_compliance.models import HumanReason, HumanReview


def needs_human(
    reason: str,
    parameter: str | None = None,
    category: HumanReason = "other",
    requirement_id: str | None = None,
) -> HumanReview:
    reason = reason.strip()
    if not reason:
        raise ValueError("needs_human needs a reason: say what a person must decide")
    if problems := explanation_problems(reason):
        raise ValueError(
            f"reason rejected ({'; '.join(problems)}): state the decision a person must make "
            "in one sentence, without reasoning out loud"
        )
    return HumanReview(
        parameter=parameter, category=category, reason=reason, requirement_id=requirement_id
    )
