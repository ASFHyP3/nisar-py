#!/bin/bash --login
# TODO confirm correct for this project
set -e
conda activate nisar-py
exec python -um nisar_py "$@"
