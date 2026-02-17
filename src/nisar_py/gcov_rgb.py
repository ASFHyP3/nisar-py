import argparse
import numpy as np
from pathlib import Path

from osgeo import gdal, osr
from nisar.products.readers import open_product
# from memory_profiler import profile


def prepare_geotif_data(data: np.ndarray) -> np.ndarray:
    data = np.nan_to_num(data, copy=False)
    data[data < pow(10.0, -48.0 / 10.0)] = 0.0
    return data


def calculate_color_channel(
    copol: np.ndarray, crosspol: np.ndarray, color: str, threshold: float = -24, scale_factor: float = 254.0
):
    power_threshold = 10.0 ** (threshold / 10.0)
    below_threshold_mask = crosspol < power_threshold

    zp = np.arctan(np.sqrt(np.clip(copol - crosspol, 0, None))) * (2.0 / np.pi)
    zp[~below_threshold_mask] = 0.0

    if color == 'red':
        channel = 2.0 * np.sqrt(np.clip(copol - 3.0 * crosspol, 0, None))
        channel[below_threshold_mask] = 0.0
        channel += zp
    elif color == 'green':
        channel = 3.0 * np.sqrt(crosspol)
        channel[below_threshold_mask] = 0.0
        channel += 2.0 * zp
    elif color == 'blue':
        channel = 5.0 * zp

    channel = channel * scale_factor + 1.0

    invalid_crosspol_mask = ~(crosspol > 0)
    channel[invalid_crosspol_mask] = 0.0

    return channel


# @profile
def make_rgb_geotiff(gcov_product: Path, output_path: Path, frequency: str) -> Path:
    output_geotiff = output_path / f'rgb_{gcov_product.stem}_{frequency}.tiff'

    if output_geotiff.exists():
        print(f'Skipping (exists): already Exists {output_geotiff.name}')
        return

    gcov = open_product(gcov_product)
    if frequency not in gcov.frequencies:
        print(f'Skipping (frequency): {gcov_product.stem} does not have frequency {frequency}')
        return

    polarizations = _get_polarization_names(gcov.polarizations[frequency])

    if polarizations is None:
        print(f'Skipping (single-pol): {gcov_product.stem}')
        return

    print(f'Generating rgb for freq {frequency} for {gcov_product.name}')
    copol_name, crosspol_name = polarizations
    copol = gcov.getImageDataset(frequency=frequency, polarization=copol_name)[:, :]
    crosspol = gcov.getImageDataset(frequency=frequency, polarization=crosspol_name)[:, :]

    # create an RGB raster in memory
    grid = gcov.getGeoGridParameters(frequency=frequency, polarization=copol_name)

    driver = gdal.GetDriverByName('MEM')
    raster = driver.Create('', grid.width, grid.length, 3, gdal.GDT_Byte)

    geotransform = (grid.start_x, grid.spacing_x, 0, grid.start_y, 0, grid.spacing_y)
    raster.SetGeoTransform(geotransform)

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(grid.epsg)
    raster.SetProjection(srs.ExportToWkt())

    copol = prepare_geotif_data(copol)
    crosspol = prepare_geotif_data(crosspol)

    for band_idx, color in enumerate(('red', 'green', 'blue'), start=1):
        channel = calculate_color_channel(copol, crosspol, color)
        raster.GetRasterBand(band_idx).WriteArray(channel)
        raster.GetRasterBand(band_idx).SetNoDataValue(0)

    # write RGB raster to disk as a cloud optimized geotiff
    gdal.GetDriverByName('COG').CreateCopy(
        output_geotiff, raster, options=['NUM_THREADS=ALL_CPUS', 'BIGTIFF=YES', 'RESAMPLING=NEAREST']
    )


def _get_polarization_names(pols: list[str]) -> tuple[str, str] | None:
    if 'HH' in pols and 'HV' in pols:
        return 'HHHH', 'HVHV'
    elif 'VV' in pols and 'VH' in pols:
        return 'VVVV', 'VHVH'
    else:
        return None


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('gcov_path', type=Path, help='Path to GCOV .h5 file')
    parser.add_argument('output_path', type=Path, help='Path to output dir', default=Path.cwd() / 'rgb_decomps')
    parser.add_argument('frequency', choices=('A', 'B'))
    args = parser.parse_args()

    args.output_path.mkdir(exist_ok=True)

    make_rgb_geotiff(args.gcov_path, args.output_path, args.frequency)

    # gcov_dir = Path.home() / 'Data' / 'nisar' / 'gcov'
    # output_dir = Path.cwd() / 'rgb_decomps'
    # output_dir.mkdir(exist_ok=True)
    #
    # for gcov_path in gcov_dir.iterdir():
    #
    #     if gcov_path.is_dir():
    #         continue
    #     if gcov_path.name != 'NISAR_L2_PR_GCOV_004_076_A_022_2005_QPDH_A_20251103T110514_20251103T110549_X05007_N_F_J_002.h5':
    #         continue
    #
    #     for frequency in ('A', 'B'):
    #         make_rgb_geotiff(gcov_path, output_dir, frequency)
    #         return


if __name__ == '__main__':
    main()
