"""Create RGB image from GCOV product."""

import argparse
from math import pi
from pathlib import Path

import xarray as xr
from osgeo import gdal, osr


gdal.UseExceptions()


class RGBDecompException(Exception):
    """Exception for known rgb decomp errors."""

    pass


def _prepare_geotif_data(data: xr.Dataset) -> xr.Dataset:
    data = data.fillna(0.0)
    data[data < pow(10.0, -48.0 / 10.0)] = 0.0
    return data


def _calculate_color_channel(
    copol: xr.Dataset, crosspol: xr.Dataset | None, color: str, threshold: float = -24, scale_factor: float = 254.0
) -> xr.Dataset:

    if crosspol is None:
        crosspol = copol.where(False, copol * 0.1)
        crosspol = crosspol.where(copol > 0.4, copol * 0.0555555556 + 0.0177777778)
        crosspol = crosspol.where(copol > 0.04, 0.0)

    power_threshold = 10.0 ** (threshold / 10.0)
    below_threshold_mask = crosspol < power_threshold

    zp = xr.ufuncs.arctan(xr.ufuncs.sqrt((copol - crosspol).clip(0))) * (2.0 / pi)
    zp = zp.where(below_threshold_mask, 0.0)

    if color == 'red':
        channel = 2.0 * xr.ufuncs.sqrt((copol - 3.0 * crosspol).clip(0))
        channel = channel.where(~below_threshold_mask, 0.0)
        channel += zp
    elif color == 'green':
        channel = 3.0 * xr.ufuncs.sqrt(crosspol)
        channel = channel.where(~below_threshold_mask, 0.0)
        channel += 2.0 * zp
    elif color == 'blue':
        channel = 5.0 * zp

    channel = channel * scale_factor + 1.0

    channel = channel.where(copol > 0, 0.0)

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
    gcov = xr.open_datatree(gcov_product, chunks='auto')
    grids = gcov.science.LSAR.GCOV.grids

    if frequency is None:
        if 'frequencyA' in grids:
            frequency = 'A'
        else:
            frequency = 'B'

    elif f'frequency{frequency}' not in grids:
        raise RGBDecompException(f'{gcov_product.stem} does not have frequency {frequency}')

    output_geotiff = output_path / f'rgb_{gcov_product.stem}_{frequency}.tiff'

    if output_geotiff.exists():
        print(f'Skipping because output product already exists: {output_geotiff}')
        return output_geotiff

    print(f'Generating rgb for freq {frequency} for {gcov_product.name}')
    frequency_group = grids[f'frequency{frequency}']
    copol_name, crosspol_name = _get_polarization_names(frequency_group.listOfPolarizations.values.astype(str))

    if copol_name is None:
        raise RGBDecompException(f'{gcov_product.stem} has no copol data for frequency {frequency}')

    copol_ds = frequency_group[copol_name]
    if crosspol_name:
        crosspol_ds = frequency_group[crosspol_name]
    else:
        crosspol_ds = None

    # create an RGB raster in memory
    xmin = frequency_group.xCoordinates.min()
    xres = frequency_group.xCoordinateSpacing.values
    ymax = frequency_group.yCoordinates.max()
    yres = frequency_group.yCoordinateSpacing.values
    width = copol_ds.shape[0]
    length = copol_ds.shape[1]

    driver = gdal.GetDriverByName('MEM')
    raster = driver.Create('', length, width, 3, gdal.GDT_Byte)

    geotransform = (xmin - xres / 2, xres, 0, ymax - yres / 2, 0, yres)
    raster.SetGeoTransform(geotransform)

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(int(frequency_group.projection.values))
    raster.SetProjection(srs.ExportToWkt())

    for band_idx, color in enumerate(('red', 'green', 'blue'), start=1):
        channel = _calculate_color_channel(copol_ds, crosspol_ds, color)

        band = raster.GetRasterBand(band_idx)
        band.WriteArray(channel.values)
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
