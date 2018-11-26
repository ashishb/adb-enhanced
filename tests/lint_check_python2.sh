#!/usr/bin/env bash
set -eou pipefail

# R = refactor
# C = convention
# W = warning

# Don't check asyncio_helper for Python2 since it is written only for Python3
python -m pylint src/adb_helper.py src/adbe.py src/output_helper.py --disable=R,C,W