#!/usr/bin/env bash
set -eou pipefail

# R = refactor
# C = convention
# W = warning

# E0602 is due to undefined variable unicode which is defined only for Python 2
# W0511 is fixme due to TODOs in the code.
# src/adbe.py:756:8: W0601: Global variable 'screen_record_file_path_on_device' undefined at the module level (global-variable-undefined)
# src/adbe.py:764:8: W0601: Global variable 'screen_record_file_path_on_device' undefined at the module level (global-variable-undefined)
# src/adbe.py:752:4: W0621: Redefining name 'screen_record_file_path_on_device' from outer scope (line 759) (redefined-outer-name)
# C0111: Missing function docstring (missing-docstring)
python3 -m pylint src/*.py tests/*.py release/setup.py release/release.py --disable=R0123,R0911,R0912,R0914,R0915,R1705,R1710,C0103,C0111,C0301,C0302,C0411,C0413,C1801,W0511,W0621,W0601,W0603