"""The parameters the agent checks, in report order.

Inputs such as unit length and design speed are not checked: they select which rule applies.
A parameter the spec does not supply is reported as `needs_human` without a search.
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
