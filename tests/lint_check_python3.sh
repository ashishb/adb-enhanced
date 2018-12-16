#!/usr/bin/env bash
set -eou pipefail

# R = refactor
# C = convention
# W = warning

# E0602 is due to undefined variable unicode which is defined only for Python 2
# W0511 is fixme due to TODOs in the code.
# src/adbe.py:38:4: W0406: Module import itself (import-self)
# src/adbe.py:39:4: W0406: Module import itself (import-self)
# src/adbe.py:752:4: W0621: Redefining name 'screen_record_file_path_on_device' from outer scope (line 759) (redefined-outer-name)
# src/adbe.py:756:8: W0601: Global variable 'screen_record_file_path_on_device' undefined at the module level (global-variable-undefined)
# src/adbe.py:764:8: W0601: Global variable 'screen_record_file_path_on_device' undefined at the module level (global-variable-undefined)
python3 -m pylint src/*.py tests/*.py --disable=R,C,W0603,E0602,W0511,W0406,W0621,W0601
