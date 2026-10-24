from rail_compliance.parameters import CHECKED_PARAMETERS
from rail_compliance.spec import parameter_info


def test_every_checked_parameter_is_a_spec_parameter():
    assert set(CHECKED_PARAMETERS) <= set(parameter_info())


def test_no_duplicates():
    assert len(set(CHECKED_PARAMETERS)) == len(CHECKED_PARAMETERS)


def test_every_checked_parameter_has_a_known_subject():
    from rail_compliance.parameters import SUBJECT_OF, SUBJECTS

    assert set(SUBJECT_OF) == set(CHECKED_PARAMETERS)
    assert set(SUBJECT_OF.values()) <= set(SUBJECTS)


def test_a_wheelchair_doorway_is_governed_by_rules_for_all_exterior_doorways_but_not_vice_versa():
    from rail_compliance.parameters import accepted_subjects

    assert accepted_subjects("exterior_doors.wheelchair_door_clear_width_mm") == [
        "wheelchair_doorway",
        "exterior_doorway",
    ]
    assert accepted_subjects("exterior_doors.clear_width_mm") == ["exterior_doorway"]


def test_other_parameters_accept_only_their_own_subject():
    from rail_compliance.parameters import accepted_subjects

    assert accepted_subjects("steps.internal_step_height_mm") == ["internal_step"]
    assert accepted_subjects("steps.external_step_height_mm") == ["external_step"]
