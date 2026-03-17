"""Create RGB image from GCOV product."""

import argparse
from pathlib import Path

import numpy as np
from nisar.products.readers import open_product
from osgeo import gdal, osr


class RGBDecompException(Exception):
    """Exception for known rgb decomp errors."""

    pass


def _prepare_geotif_data(data: np.ndarray) -> np.ndarray:
    data = np.nan_to_num(data, copy=False)
    data[data < pow(10.0, -48.0 / 10.0)] = 0.0
    return data


def _calculate_color_channel(
    copol: np.ndarray, crosspol: np.ndarray, color: str, threshold: float = -24, scale_factor: float = 254.0
) -> np.ndarray:
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


def _get_polarization_names(pols: list[str]) -> tuple[str, str] | None:
    if 'HH' in pols and 'HV' in pols:
        return 'HHHH', 'HVHV'
    elif 'VV' in pols and 'VH' in pols:
        return 'VVVV', 'VHVH'
    else:
        return None


def make_rgb_geotiff(gcov_product: Path, output_path: Path, frequency: str | None = None) -> Path:
    """Create RGB GeoTIFF from GCOV product."""
    output_geotiff = output_path / f'rgb_{gcov_product.stem}_{frequency}.tiff'

    if output_geotiff.exists():
        print(f'Skipping (exists): already Exists {output_geotiff.name}')
        return output_geotiff

    gcov = open_product(gcov_product)

    if frequency is None:
        frequency = gcov.frequencies[0]

    elif frequency not in gcov.frequencies:
        raise RGBDecompException(f'Skipping (frequency): {gcov_product.stem} does not have frequency {frequency}')

    polarizations = _get_polarization_names(gcov.polarizations[frequency])

    if polarizations is None:
        raise RGBDecompException(f'Skipping (single-pol): {gcov_product.stem}')

    print(f'Generating rgb for freq {frequency} for {gcov_product.name}')
    copol_name, crosspol_name = polarizations

    copol_ds = gcov.getImageDataset(frequency=frequency, polarization=copol_name)
    crosspol_ds = gcov.getImageDataset(frequency=frequency, polarization=crosspol_name)

    # create an RGB raster in memory
    grid = gcov.getGeoGridParameters(frequency=frequency, polarization=copol_name)

    driver = gdal.GetDriverByName('MEM')
    raster = driver.Create('', grid.width, grid.length, 3, gdal.GDT_Byte)

    geotransform = (grid.start_x, grid.spacing_x, 0, grid.start_y, 0, grid.spacing_y)
    raster.SetGeoTransform(geotransform)

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(grid.epsg)
    raster.SetProjection(srs.ExportToWkt())

    for chunk in copol_ds.iter_chunks():
        y_slice, x_slice = chunk
        y_off, x_off = y_slice.start, x_slice.start

        copol_chunk = _prepare_geotif_data(copol_ds[chunk])
        crosspol_chunk = _prepare_geotif_data(crosspol_ds[chunk])

        for band_idx, color in enumerate(('red', 'green', 'blue'), start=1):
            channel = _calculate_color_channel(copol_chunk, crosspol_chunk, color)

            band = raster.GetRasterBand(band_idx)
            band.WriteArray(channel, xoff=x_off, yoff=y_off)
            band.SetNoDataValue(0)

    # write RGB raster to disk as a cloud optimized geotiff
    gdal.GetDriverByName('COG').CreateCopy(
        output_geotiff, raster, options=['NUM_THREADS=ALL_CPUS', 'BIGTIFF=YES', 'RESAMPLING=NEAREST']
    )

    return output_geotiff


def main() -> None:
    """Create RGB image from GCOV product."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('gcov_path', type=Path, help='Path to GCOV .h5 file')
    parser.add_argument('output_path', type=Path, help='Path to output dir', default=Path.cwd() / 'rgb_decomps')
    parser.add_argument('-f', '--frequency', choices=('A', 'B'), help='Frequency to process')
    args = parser.parse_args()

    args.output_path.mkdir(exist_ok=True)

    make_rgb_geotiff(args.gcov_path, args.output_path, args.frequency)


if __name__ == '__main__':
    main()
