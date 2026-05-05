from nisar_py import gcov_rgb


def test_get_polarization_names():
    assert gcov_rgb._get_polarization_names(['HH', 'HV']) == ('HHHH', 'HVHV')
    assert gcov_rgb._get_polarization_names(['HV', 'HH']) == ('HHHH', 'HVHV')

    assert gcov_rgb._get_polarization_names(['HH']) == ('HHHH', None)
    assert gcov_rgb._get_polarization_names(['HV']) == (None, None)

    assert gcov_rgb._get_polarization_names(['VV', 'VH']) == ('VVVV', 'VHVH')
    assert gcov_rgb._get_polarization_names(['VH', 'VV']) == ('VVVV', 'VHVH')

    assert gcov_rgb._get_polarization_names(['VV']) == ('VVVV', None)
    assert gcov_rgb._get_polarization_names(['VH']) == (None, None)

    assert gcov_rgb._get_polarization_names([]) == (None, None)
