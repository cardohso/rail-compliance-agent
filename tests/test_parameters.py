from rail_compliance.parameters import CHECKED_PARAMETERS
from rail_compliance.spec import parameter_info


def test_every_checked_parameter_is_a_spec_parameter():
    assert set(CHECKED_PARAMETERS) <= set(parameter_info())


def test_no_duplicates():
    assert len(set(CHECKED_PARAMETERS)) == len(CHECKED_PARAMETERS)
