"""Reproject NISAR product."""

import argparse
from pathlib import Path

from nisar.products.readers import open_product
from osgeo import gdal, osr

NORTH_POLE_EPSG = 'EPSG:3413'
SOUTH_POLE_EPSG = 'EPSG:3031'

class ReprojectionException(Exception):
    """Exception for known reprojection errors."""

    pass

def get_min_max_lats(rgb):
    info = gdal.Info(rgb, format='json')
    coords = info['wgs84Extent']['coordinates'][0]
    lats = []
    for lon, lat in coords:
        lats.append(lat)
    return min(lats), max(lats)

def reproject_geotiff(rgb_product: Path, output_path: Path, projection: str | None = None) -> Path:
    """Create RGB GeoTIFF from GCOV product."""

    if projection is None:
        min_lat, max_lat = get_min_max_lats(rgb_product)
        if min_lat > 60:
            epsg_code = NORTH_POLE_EPSG
        elif max_lat < -60:
            epsg_code = SOUTH_POLE_EPSG
        else:
            print(f'{rgb_product} not in polar region. Skipping reprojection.')
            return rgb_product


    output_geotiff = output_path / f'polar_projected_{rgb_product.stem}.tiff'

    if output_geotiff.exists():
        print(f'Skipping because output product already exists: {output_geotiff}')
        return output_geotiff

    print(f'Reprojecting to EPSG:{epsg_code} for {rgb_product.name}')

    gdal.Warp(rgb_product,
              output_geotiff,
              format='COG',
              dstSRS=epsg_code)

    return output_geotiff


def main() -> None:
    """Reproject NISAR product."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('gcov_path', type=Path, help='Path to GCOV RGB product')
    parser.add_argument('output_path', type=Path, help='Path to output dir', default=Path.cwd() / 'polar_reprojections')
    parser.add_argument('-p', '--output_projection', help='EPSG for output projection')
    args = parser.parse_args()

    args.output_path.mkdir(exist_ok=True)

    reproject_geotiff(args.nisar_path, args.output_path, args.output_projection)


if __name__ == '__main__':
    main()
