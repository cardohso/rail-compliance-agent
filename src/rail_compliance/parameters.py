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
    "wheelchair_space_layout.width_mm",
    "wheelchair_space_layout.hand_clearance_mm",
    "wheelchair_space_layout.turning_space_diameter_mm",
    "stairs.step_height_mm",
    "stairs.step_depth_mm",
    "handrails.outside_diameter_mm",
    "priority_seats.cushion_height_mm",
    "noise.stationary_db",
    "noise.pass_by_80_db",
    "noise.pass_by_250_db",
    "noise.cab_standstill_horn_db",
    "noise.cab_max_speed_db",
)

# The regulation that governs each parameter (corpus doc id). A rule quoted from another one is
# rejected: the PRM TSI's dB figures for door signals say nothing about a unit's noise.
REGULATIONS: dict[str, str] = {
    "tsi-prm": "PRM TSI (Regulation (EU) No 1300/2014)",
    "tsi-noi": "Noise TSI (Regulation (EU) No 1304/2014)",
}
REGULATION_OF: dict[str, str] = {
    p: "tsi-noi" if p.startswith("noise.") else "tsi-prm" for p in CHECKED_PARAMETERS
}

SUBJECTS: dict[str, str] = {
    "wheelchair_space": "a wheelchair space in a unit",
    "exterior_doorway": "exterior passenger doorways in general (every one of them)",
    "wheelchair_doorway": "the doorways designated for wheelchair access",
    "external_step": "external access steps",
    "internal_step": "internal steps used for external access",
    "universal_toilet": "the universal toilet a train with toilets must provide",
    "universal_toilet_door": "the access door of a universal toilet",
    "wheelchair_space_area": "the dimensions of a wheelchair space",
    "turning_space": "the space where a wheelchair turns 180 degrees",
    "internal_stairs": "internal steps and stairs other than those for external access",
    "handrail": "handrails fitted to a vehicle",
    "priority_seat": "a priority seat",
    "stationary_noise": "the stationary noise of a unit",
    "pass_by_noise": "the pass-by noise of a unit",
    "cab_noise": "the noise inside the driver's cab",
}

SUBJECT_OF: dict[str, str] = {
    "wheelchair_spaces": "wheelchair_space",
    "exterior_doors.clear_width_mm": "exterior_doorway",
    "exterior_doors.wheelchair_door_clear_width_mm": "wheelchair_doorway",
    "steps.external_step_height_mm": "external_step",
    "steps.internal_step_height_mm": "internal_step",
    "toilets.universal": "universal_toilet",
    "toilets.universal_door_clear_width_mm": "universal_toilet_door",
    "wheelchair_space_layout.width_mm": "wheelchair_space_area",
    "wheelchair_space_layout.hand_clearance_mm": "wheelchair_space_area",
    "wheelchair_space_layout.turning_space_diameter_mm": "turning_space",
    "stairs.step_height_mm": "internal_stairs",
    "stairs.step_depth_mm": "internal_stairs",
    "handrails.outside_diameter_mm": "handrail",
    "priority_seats.cushion_height_mm": "priority_seat",
    "noise.stationary_db": "stationary_noise",
    "noise.pass_by_80_db": "pass_by_noise",
    "noise.pass_by_250_db": "pass_by_noise",
    "noise.cab_standstill_horn_db": "cab_noise",
    "noise.cab_max_speed_db": "cab_noise",
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


# --- the coverage check (tools/coverage.py) ------------------------------------------------------
# How a passage refers to each subject, in the regulation's own words. A numbered point is "about" a
# parameter when it names one of the subjects that govern it.
SUBJECT_TERMS: dict[str, tuple[str, ...]] = {
    "wheelchair_space": ("wheelchair space",),
    "exterior_doorway": ("exterior passenger doorway", "exterior doorway"),
    "wheelchair_doorway": (
        "wheelchair access door",
        "doorways designated for wheelchair",
        "wheelchair exterior accessible doorway",
    ),
    "external_step": ("external access step", "external step"),
    "internal_step": ("internal step",),
    "universal_toilet": ("universal toilet",),
    "universal_toilet_door": ("toilet access door",),
    "wheelchair_space_area": ("wheelchair space",),
    "turning_space": ("turning space",),
    "internal_stairs": ("internal steps",),
    "handrail": ("handrail",),
    "priority_seat": ("priority seat",),
    "stationary_noise": ("stationary noise",),
    "pass_by_noise": ("pass-by noise",),
    "cab_noise": ("driver's cab",),
}

# What a sentence must name to state a rule on the same measure as the parameter. For millimetre
# parameters a figure is "<n> mm"; for counts it is "<n> <noun>" or "a <noun> shall be provided".
MEASURES: dict[str, tuple[str, ...]] = {
    "wheelchair_spaces": ("wheelchair space",),
    "toilets.universal": ("universal toilet",),
    "exterior_doors.clear_width_mm": ("clear useable width",),
    "exterior_doors.wheelchair_door_clear_width_mm": ("clear useable width",),
    "steps.external_step_height_mm": ("height",),
    "steps.internal_step_height_mm": ("height",),
    "toilets.universal_door_clear_width_mm": ("clear useable width",),
    "wheelchair_space_layout.width_mm": ("width",),
    "wheelchair_space_layout.hand_clearance_mm": ("width",),
    "wheelchair_space_layout.turning_space_diameter_mm": ("diameter",),
    "stairs.step_height_mm": ("height",),
    "stairs.step_depth_mm": ("depth",),
    "handrails.outside_diameter_mm": ("diameter",),
    "priority_seats.cushion_height_mm": ("above floor level",),
}
