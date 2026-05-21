"""Create RGB image from GCOV product."""

import argparse
from pathlib import Path

import numpy as np
from nisar.products.readers import open_product
from osgeo import gdal, osr


class RGBDecompException(Exception):
    """Exception for known rgb decomp errors."""

    pass


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

    return channel


def _get_polarization_names(pols: list[str]) -> tuple[str | None, str | None]:
    copol, crosspol = None, None

    if 'HH' in pols:
        copol = 'HHHH'
    elif 'VV' in pols:
        copol = 'VVVV'

    if 'HV' in pols:
        crosspol = 'HVHV'
    elif 'VH' in pols:
        crosspol = 'VHVH'

    return copol, crosspol


def make_rgb_geotiff(gcov_product: Path, output_path: Path, frequency: str | None = None) -> Path:
    """Create RGB GeoTIFF from GCOV product."""
    gcov = open_product(gcov_product)

    if frequency is None:
        frequency = gcov.frequencies[0]

    elif frequency not in gcov.frequencies:
        raise RGBDecompException(f'{gcov_product.stem} does not have frequency {frequency}')

    output_geotiff = output_path / f'rgb_{gcov_product.stem}_{frequency}.tiff'

    if output_geotiff.exists():
        print(f'Skipping because output product already exists: {output_geotiff}')
        return output_geotiff

    print(f'Generating rgb for freq {frequency} for {gcov_product.name}')
    copol_name, crosspol_name = _get_polarization_names(gcov.polarizations[frequency])

    if copol_name is None:
        raise RGBDecompException(f'{gcov_product.stem} has no copol data for frequency {frequency}')

    copol_ds = gcov.getImageDataset(frequency=frequency, polarization=copol_name)
    if crosspol_name:
        crosspol_ds = gcov.getImageDataset(frequency=frequency, polarization=crosspol_name)
    else:
        crosspol_ds = None
    mask = gcov.getImageDataset(frequency=frequency, polarization='mask')

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

        mask_chunk = np.isin(mask[chunk], [0, 255])

        copol_chunk = copol_ds[chunk]
        copol_chunk[mask_chunk] = np.nan

        if crosspol_ds:
            crosspol_chunk = crosspol_ds[chunk]
            crosspol_chunk[mask_chunk] = np.nan
        else:
            crosspol_chunk = copol_chunk * 0.1
            crosspol_chunk[copol_chunk <= 0.4] = copol_chunk[copol_chunk <= 0.4] * 0.0555555556 + 0.0177777778
            crosspol_chunk[copol_chunk <= 0.04] = 0

        for band_idx, color in enumerate(('red', 'green', 'blue'), start=1):
            channel = _calculate_color_channel(copol_chunk, crosspol_chunk, color)

            band = raster.GetRasterBand(band_idx)
            band.WriteArray(channel, xoff=x_off, yoff=y_off)
            band.SetNoDataValue(0)

    # write RGB raster to disk as a cloud optimized geotiff
    gdal.GetDriverByName('COG').CreateCopy(
        output_geotiff, raster, options=['NUM_THREADS=ALL_CPUS', 'BIGTIFF=YES', 'RESAMPLING=NEAREST', 'OVERVIEWS=NONE']
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
