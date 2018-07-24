#!/bin/bash
set -e

# Works on both Mac and GNU/Linux.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VERSION_FILENAME=${DIR}/version.txt

# Copy the relevant files
cp ${DIR}/../adbe.py ${DIR}/adbe/ && 
  cp ${DIR}/../README.md ${DIR}/README.md &&
  # Open setup file to increment the version
  echo -n "Next the editor will open ${VERSION_FILENAME}, increment the version number in it. Press enter to continue:" &&
    # Wait for a keypress to ensure that user has seen the previous message
  read -n 1 -s &&
  vim ${VERSION_FILENAME} &&
  # One time setup
  python3 -m pip install --user --upgrade setuptools wheel twine &&
  # Cleanup before creating the package
  rm -r build/ dist/
  # Create the package. Reference: https://packaging.python.org/tutorials/packaging-projects/
  python3 setup.py sdist bdist_wheel &&
  # Commit to git before sending package upstream
  git add ${DIR}/README.md ${DIR}/adbe/adbe.py ${VERSION_FILENAME} &&
  git commit -m "Setup release $(cat $VERSION_FILENAME)" &&
  git tag $(cat $VERSION_FILENAME) &&
  git push origin master &&
  git push origin master --tags &&
  # Send the package upstream
  twine upload dist/* &&
  echo "Few mins later, check https://pypi.org/project/adb-enhanced/#history to confirm upload" &&
  # Cleanup
  rm -r build/ dist/
