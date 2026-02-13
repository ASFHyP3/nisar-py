import numpy as np
from pathlib import Path

from osgeo import gdal, osr
from nisar.products.readers import open_product


def prepare_geotif_data(data: np.ndarray) -> np.ndarray:
    data = np.nan_to_num(data)
    data[data < pow(10.0, -48.0 / 10.0)] = 0.0
    return data


def calculate_color_channel(
    copol_data: np.ndarray, crosspol_data: np.ndarray, color: str, threshold: float=-24, scale_factor: float=254.0
):
    """Calculate color channel values for the RGB decomposition of copol and crosspol data

    Args:
        copol_data: copol data
        crosspol_data: crosspol data
        threshold: decomposition threshold value in db
        scale_factor: scale data by this factor
        color: the color channel to calculate

    Returns:
        color_channel: color channel data
    """

    power_threshold = pow(10.0, threshold / 10.0)  # db to power
    below_threshold_mask = crosspol_data < power_threshold

    # I don't know what 'zp' is...
    zp = np.arctan(np.sqrt(np.clip(copol_data - crosspol_data, 0, None))) * 2.0 / np.pi
    zp[~below_threshold_mask] = 0

    if color == 'red':
        z_constant = 1.0
        color_term = 2.0 * np.sqrt(np.clip(copol_data - 3.0 * crosspol_data, 0, None))
        color_term[below_threshold_mask] = 0.0

    elif color == 'green':
        z_constant = 2.0
        color_term = 3.0 * np.sqrt(crosspol_data)
        color_term[below_threshold_mask] = 0.0

    elif color == 'blue':
        z_constant = 5.0
        color_term = np.zeros(copol_data.shape)

    else:
        raise ValueError(f'Unknown color {color}, pick red, green, or blue')

    # Find all our no data and bad data pixels
    # NOTE: we're using crosspol here because it will typically have the most bad
    # data and we want the same mask applied to all 3 channels (otherwise, we'll
    # accidentally be changing colors from intended)
    invalid_crosspol_mask = ~(crosspol_data > 0)

    color_channel = 1.0 + (color_term + z_constant * zp) * scale_factor
    color_channel[invalid_crosspol_mask] = 0

    return color_channel


def main():
    gcov_dir = Path.home() / 'Data' / 'nisar' / 'gcov'
    output_dir = Path.cwd() / 'rgb_decomps'
    output_dir.mkdir(exist_ok=True)

    for gcov_path in gcov_dir.iterdir():
        if gcov_path.is_dir():
            continue

        gcov = open_product(gcov_path)
        for frequency in gcov.frequencies:
            output_decomp = output_dir / f'rgb_{gcov_path.stem}_{frequency}.tiff'
            print(gcov.polarizations)
            print(f'Processing {output_decomp.name}')
            if output_decomp.exists():
                continue

            print(f'Generating rgb for freq {frequency} for {gcov_path.name}')
            co_pol_key, cross_pol_key = _get_polarization_keys(gcov.polarizations[frequency])

            if co_pol_key is None:
                print(f'Skipping single-pol: {gcov_path.stem}')
                continue

            # co_pol, cross_pol
            co_pol = gcov.getImageDataset(frequency=frequency, polarization=co_pol_key)[:, :]
            cross_pol = gcov.getImageDataset(frequency=frequency, polarization=cross_pol_key)[:, :]
            co_pol = prepare_geotif_data(co_pol)
            cross_pol = prepare_geotif_data(cross_pol)

            # create an RGB raster in memory
            grid = gcov.getGeoGridParameters(frequency=frequency, polarization=co_pol_key)

            driver = gdal.GetDriverByName('MEM')
            raster = driver.Create('', grid.width, grid.length, 3, gdal.GDT_Byte)

            geotransform = (grid.start_x, grid.spacing_x, 0, grid.start_y, 0, grid.spacing_y)
            raster.SetGeoTransform(geotransform)

            srs = osr.SpatialReference()
            srs.ImportFromEPSG(grid.epsg)
            raster.SetProjection(srs.ExportToWkt())

            for band_idx, color in enumerate(('red', 'green', 'blue'), start=1):
                color_channel = calculate_color_channel(co_pol, cross_pol, color=color)
                raster.GetRasterBand(band_idx).WriteArray(color_channel)
                raster.GetRasterBand(band_idx).SetNoDataValue(0)

            # write RGB raster to disk as a cloud optimized geotiff
            gdal.GetDriverByName('COG').CreateCopy(
                output_dir / f'rgb_{gcov_path.stem}_{frequency}.tiff',
                raster,
                options=['NUM_THREADS=ALL_CPUS', 'BIGTIFF=YES', 'RESAMPLING=NEAREST']
            )


def _get_polarization_keys(pols):
    if 'HH' in pols and 'HV' in pols:
        return 'HHHH', 'HVHV'
    elif 'VV' in pols and 'VH' in pols:
        return 'VVVV', 'VHVH'
    else:
        return None, None


if __name__ == '__main__':
    main()
