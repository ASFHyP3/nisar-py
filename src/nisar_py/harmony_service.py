"""Harmony service for nisar-py."""

import argparse
import tempfile
from pathlib import Path

import harmony_service_lib
import pystac
from harmony_service_lib.exceptions import HarmonyException

from nisar_py.gcov_rgb import make_rgb_geotiff


class HarmonyAdapter(harmony_service_lib.BaseHarmonyAdapter):
    """Harmony adapter for nisar-py."""

    def process_item(self, item: pystac.Item, source: harmony_service_lib.message.Source | None = None) -> pystac.Item:
        """Processes a single input item.

        Parameters
        ----------
        item : pystac.Item
            the item that should be processed
        source : harmony_service_lib.message.Source
            the input source defining the variables, if any, to subset from the item

        Returns:
        -------
        pystac.Item
            a STAC catalog whose metadata and assets describe the service output
        """
        self.logger.info(f'Processing item {item.id}')

        granule_url = _get_asset_url(item, '.h5')

        with tempfile.TemporaryDirectory() as temp_dir:
            granule_filename = harmony_service_lib.util.download(
                url=granule_url,
                destination_dir=temp_dir,
                logger=self.logger,
                access_token=self.message.accessToken,
            )
            rgb_path = make_rgb_geotiff(
                gcov_product=Path(granule_filename),
                frequency='A',
                output_path=Path(temp_dir),
            )
            url = harmony_service_lib.util.stage(
                local_filename=str(rgb_path),
                remote_filename=rgb_path.name,
                mime='image/tiff',
                location=self.message.stagingLocation,
                logger=self.logger,
            )

            result = item.clone()
            result.assets = {
                'rgb_browse': pystac.Asset(url, title=rgb_path.name, media_type='image/tiff', roles=['visual'])
            }

        return result


def _get_asset_url(item: pystac.Item, suffix: str) -> str:
    try:
        return next(asset.href for asset in item.assets.values() if asset.href.endswith(suffix))
    except StopIteration:
        raise HarmonyException(f'No {suffix} asset found for {item.id}')


def main() -> None:
    """Run the Harmony service."""
    parser = argparse.ArgumentParser(description='Run the Harmony service')
    harmony_service_lib.setup_cli(parser)
    args = parser.parse_args()
    harmony_service_lib.run_cli(parser, args, HarmonyAdapter)


if __name__ == '__main__':
    main()
