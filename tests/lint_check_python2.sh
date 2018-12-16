#!/usr/bin/env bash
set -eou pipefail

# R = refactor
# C = convention
# W = warning

# Don't check asyncio_helper for Python2 since it is written only for Python3
python -m pylint src/adb_enhanced.py src/adb_helper.py src/main.py src/output_helper.py tests/*.py release/setup.py --disable=R,C,W