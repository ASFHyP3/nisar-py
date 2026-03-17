# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [PEP 440](https://www.python.org/dev/peps/pep-0440/)
and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2]

### Changed
- `frequency` is now an optional argument and the first available frequency is chosen
- Errors from `gcov_rgb.make_rgb_geotiff` in `harmony_service.py` are now raised as `HarmonyException` to show nice error messages

## [0.1.1]

### Changed
- `rgb_decomp` now processes data in 512x512 chunks to reduce peak memory usage

## [0.1.0]

### Added
- Add a Harmony service for creating an RGB GeoTIFF from a GCOV product.
