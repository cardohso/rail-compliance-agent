"""The parameters the agent checks, in report order, and what each one is about.

Inputs such as unit length and design speed are not checked: they select which rule applies.
A parameter the spec does not supply is reported as `needs_human` without a search.

Every rule the model extracts is labelled with the *subject* it is stated for. A parameter is
governed by rules for its own subject and for any broader subject it sits inside: a wheelchair
doorway is an exterior doorway, so a rule for "all exterior passenger doorways" governs it; the
reverse is not true, so a rule for wheelchair doorways says nothing about the narrowest doorway.
"""

CHECKED_PARAMETERS: tuple[str, ...] = (
    "wheelchair_spaces",
    "exterior_doors.clear_width_mm",
    "exterior_doors.wheelchair_door_clear_width_mm",
    "steps.external_step_height_mm",
    "steps.internal_step_height_mm",
    "toilets.universal",
    "toilets.universal_door_clear_width_mm",
)

SUBJECTS: dict[str, str] = {
    "wheelchair_space": "a wheelchair space in a unit",
    "exterior_doorway": "exterior passenger doorways in general (every one of them)",
    "wheelchair_doorway": "the doorways designated for wheelchair access",
    "external_step": "external access steps",
    "internal_step": "internal steps used for external access",
    "universal_toilet": "the universal toilet a train with toilets must provide",
    "universal_toilet_door": "the access door of a universal toilet",
}

SUBJECT_OF: dict[str, str] = {
    "wheelchair_spaces": "wheelchair_space",
    "exterior_doors.clear_width_mm": "exterior_doorway",
    "exterior_doors.wheelchair_door_clear_width_mm": "wheelchair_doorway",
    "steps.external_step_height_mm": "external_step",
    "steps.internal_step_height_mm": "internal_step",
    "toilets.universal": "universal_toilet",
    "toilets.universal_door_clear_width_mm": "universal_toilet_door",
}

# subject -> the broader subject it sits inside
WITHIN: dict[str, str] = {"wheelchair_doorway": "exterior_doorway"}


def accepted_subjects(parameter: str) -> list[str]:
    """Subjects whose rules govern `parameter`: its own, then each broader one."""
    subject, out = SUBJECT_OF[parameter], []
    while subject:
        out.append(subject)
        subject = WITHIN.get(subject)
    return out
