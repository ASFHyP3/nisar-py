import filecmp

import numpy as np

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


def test_create_color_channel():
    calc = gcov_rgb._calculate_color_channel

    copol = np.array([0.0, 0.00001, 0.01, 0.1, 1.0, 100.0, np.nan])
    crosspol = copol
    invalid_pixels = np.array([False, False, False, False, False, False, False])

    assert np.all(calc(copol, crosspol, invalid_pixels, 'red') == [1, 1, 1, 1, 1, 1, 1])
    assert np.all(calc(copol, crosspol, invalid_pixels, 'green') == [1, 1, 77, 241, 255, 255, 1])
    assert np.all(calc(copol, crosspol, invalid_pixels, 'blue') == [1, 1, 1, 1, 1, 1, 1])

    copol = np.array([0.01, 0.02, 0.03, 0.05])
    crosspol = np.array([0.0, 0.0, 0.0, 0.0])
    invalid_pixels = np.array([False, True, False, False])

    assert np.all(calc(copol, crosspol, invalid_pixels, 'red') == [17, 0, 28, 36])
    assert np.all(calc(copol, crosspol, invalid_pixels, 'green') == [33, 0, 56, 72])
    assert np.all(calc(copol, crosspol, invalid_pixels, 'blue') == [81, 0, 139, 178])

    copol = np.array([0.02, 0.04, 0.06, .1])
    crosspol = np.array([0.002, 0.004, 0.006, .01])
    invalid_pixels = np.array([False, False, False, False])

    assert np.all(calc(copol, crosspol, invalid_pixels, 'red') == [22, 86, 105, 135])
    assert np.all(calc(copol, crosspol, invalid_pixels, 'green') == [44, 49, 60, 77])
    assert np.all(calc(copol, crosspol, invalid_pixels, 'blue') == [108, 1, 1, 1])
