import filecmp

from nisar_py import gcov_rgb


def test_get_polarization_names():
    assert gcov_rgb._get_polarization_names(['HH', 'HV']) == ('HHHH', 'HVHV')
    assert gcov_rgb._get_polarization_names(['HV', 'HH']) == ('HHHH', 'HVHV')

    assert gcov_rgb._get_polarization_names(['HH']) == ('HHHH', None)
    assert gcov_rgb._get_polarization_names(['HV']) == (None, 'HVHV')

    assert gcov_rgb._get_polarization_names(['VV', 'VH']) == ('VVVV', 'VHVH')
    assert gcov_rgb._get_polarization_names(['VH', 'VV']) == ('VVVV', 'VHVH')

    assert gcov_rgb._get_polarization_names(['VV']) == ('VVVV', None)
    assert gcov_rgb._get_polarization_names(['VH']) == (None, 'VHVH')

    assert gcov_rgb._get_polarization_names([]) == (None, None)


def test_make_rgb_geotiff_single_pol(mock_gcov_granule, tmp_path, test_data_dir):
    output = gcov_rgb.make_rgb_geotiff(mock_gcov_granule, tmp_path, 'A')
    assert filecmp.cmp(output, test_data_dir / 'single_pol_output.tiff')


def test_make_rgb_geotiff_dual_pol(mock_gcov_granule, tmp_path, test_data_dir):
    output = gcov_rgb.make_rgb_geotiff(mock_gcov_granule, tmp_path, 'B')
    assert filecmp.cmp(output, test_data_dir / 'dual_pol_output.tiff')
