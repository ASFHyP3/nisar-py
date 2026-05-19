from tempfile import NamedTemporaryFile
from pathlib import Path

import pytest
from xarray import DataTree, Dataset, DataArray, Variable


@pytest.fixture
def test_data_dir():
    return Path(__file__).parent / 'data'


@pytest.fixture
def mock_gcov_granule():
    """
    Creates a mock gcov .h5 granule with sufficient data to be opened and read by ISCE3.

    frequencyA contains a 1000x512 HHHH raster with pixel values corresponding to the X coordinate of the pixel

    frequencyB contains a 1000x512 VVVV raster with pixel values corresponding to the X coordinate of the pixel,
    and a VHVH raster with pixel values corresponding to the Y coordinate of the pixel.
    """
    step_size = 0.001
    x_cooridnates = [ii * step_size for ii in range(0, 1000, 1)]
    y_coorindates = [ii * step_size for ii in range(512, 0, -1)]

    dt = DataTree.from_dict(
        {
            '/science/LSAR/GCOV/grids/frequencyA': Dataset(
                {
                    'HHHH': Variable(
                        dims=('yCoordinates', 'xCoordinates'),
                        data=[[x for x in x_cooridnates] for y in y_coorindates],
                    ).astype('float32'),
                    'xCoordinates': x_cooridnates,
                    'yCoordinates': y_coorindates,
                    'xCoordinateSpacing': step_size,
                    'yCoordinateSpacing': -step_size,
                    'listOfPolarizations': (
                        'phony_dim_0',
                        ['HH'],
                    ),
                    'projection': DataArray(3413),
                },
            ),
            '/science/LSAR/GCOV/grids/frequencyB': Dataset(
                {
                    'VVVV': Variable(
                        dims=('yCoordinates', 'xCoordinates'),
                        data=[[x for x in x_cooridnates] for y in y_coorindates],
                    ).astype('float32'),
                    'VHVH': Variable(
                        dims=('yCoordinates', 'xCoordinates'),
                        data=[[y for x in x_cooridnates] for y in y_coorindates],
                    ).astype('float32'),
                    'xCoordinates': x_cooridnates,
                    'yCoordinates': y_coorindates,
                    'xCoordinateSpacing': step_size,
                    'yCoordinateSpacing': -step_size,
                    'listOfPolarizations': (
                        'phony_dim_0',
                        ['VV', 'VH'],
                    ),
                    'projection': DataArray(3413),
                },
            ),
            '/science/LSAR/identification': Dataset(
                {
                    'productType': 'GCOV',
                    'missionId': 'NISAR',
                    'absoluteOrbitNumber': 123,
                    'lookDirection': 'Left',
                    'orbitPassDirection': 'Ascending',
                    'zeroDopplerStartTime': '2026-01-01T00:00:00.000000000',
                    'zeroDopplerEndTime': '2026-01-01T00:00:01.000000000',
                    'boundingPolygon': 'POLYGON ((0.0 0.0, 0.0 .512, 1.0 .512, 1.0 0.0, 0.0 0.0))',
                    'listOfFrequencies': ['A', 'B'],
                    'diagnosticModeFlag': 0,
                    'plannedDatatakeId': 'dtid_2025359150444',
                    'plannedObservationId': 'oid_2025359150500',
                    'isUrgentObservation': 'False',
                    'isJointObservation': 'False',
                },
            ),
        },
    )

    with NamedTemporaryFile() as temp_file:
        dt.to_netcdf(
            filepath=temp_file.name,
            encoding={
                '/science/LSAR/GCOV/grids/frequencyA': {
                    'HHHH': {'chunksizes': (512, 512), 'compression': 'gzip'},
                },
                '/science/LSAR/GCOV/grids/frequencyB': {
                    'VVVV': {'chunksizes': (512, 512), 'compression': 'gzip'},
                    'VHVH': {'chunksizes': (512, 512), 'compression': 'gzip'},
                },
            },
        )
        yield Path(temp_file.name)
