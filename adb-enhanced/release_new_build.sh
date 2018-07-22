#!/bin/bash
set -e

# Works on both Mac and GNU/Linux.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Copy the relevant files
cp ${DIR}/../adbe.py ${DIR}/adbe/ && 
  cp ${DIR}/../README.md README.md &&
  # Open setup file to increment the version
  vim setup.py &&
  # One time setup
  python3 -m pip install --user --upgrade setuptools wheel twine &&
  # Create the package. Reference: https://packaging.python.org/tutorials/packaging-projects/
  python3 setup.py sdist bdist_wheel &&
  # Send the package upstream
  twine upload dist/* &&
  echo "Few mins later, check https://pypi.org/project/adb-enhanced/#history to confirm upload" &&
  #Cleanup
  rm -r build/ dist/
