#!/usr/bin/env python3
import os
import re
import subprocess
import sys

import docopt

_DIR_OF_THIS_SCRIPT = os.path.split(__file__)[0]
_VERSION_FILE_NAME = 'pyproject.toml'
_VERSION_FILE_PATH = os.path.join(_DIR_OF_THIS_SCRIPT, _VERSION_FILE_NAME)
# Matches the `version = "x.y.z"` line of the [project] table
_VERSION_REGEX = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)
_README_FILE_NAME = os.path.join('docs', 'README.rst')
_TEST_PYPI_URL = 'https://test.pypi.org/legacy/'

_PROJECT_NAME = 'adb-enhanced'
_SRC_FILE_NAMES = [
    'abe.jar',
    'apksigner.jar',
    'adb_enhanced.py',
    'adb_helper.py',
    'asyncio_helper.py',
    'main.py',
    'output_helper.py',
    ]


def _get_version():
    with open(_VERSION_FILE_PATH, 'r') as file_handle:
        match = _VERSION_REGEX.search(file_handle.read())
    if not match:
        raise ValueError('failed to find the version in %s' % _VERSION_FILE_PATH)
    return match.group(1)


def _set_version(version):
    if not version or not version.strip():
        raise ValueError('version cannot be empty')
    with open(_VERSION_FILE_PATH, 'r') as file_handle:
        contents = file_handle.read()
    contents, count = _VERSION_REGEX.subn(
        'version = "%s"' % version.strip(), contents, count=1)
    if count != 1:
        raise ValueError('failed to find the version in %s' % _VERSION_FILE_PATH)
    with open(_VERSION_FILE_PATH, 'w') as file_handle:
        file_handle.write(contents)


def _prompt_user_to_update_version():
    current_version = _get_version()
    print('Current version is %s' % current_version)
    new_version = input("Enter new version: ")
    _set_version(new_version or current_version)


def _push_new_release_to_git():
    version = _get_version()
    cmds = [
        'git add %s' % _VERSION_FILE_PATH,
        'git commit -m "Setup release %s"' % version,
        'git tag %s' % version,
        'git push --tags',
    ]
    for cmd in cmds:
        _run_cmd_or_fail(cmd)


def _publish_package_to_pypi(testing_release=False):
    if testing_release:
        _run_cmd_or_fail(
            'python3 -m twine upload --repository-url %s dist/*' % _TEST_PYPI_URL)
        print('Few mins later, check https://test.pypi.org/project/%s/#history to confirm upload' %
              _PROJECT_NAME)
    else:
        _run_cmd_or_fail('python3 -m twine upload dist/*')
        print('Few mins later, check https://pypi.org/project/%s/#history to confirm upload' %
              _PROJECT_NAME)


def _run_cmd_or_fail(cmd):
    print('Executing \"%s\"...' % cmd)
    with subprocess.Popen(cmd, shell=True, stdout=None, stderr=None) as process:
        process.communicate()
        if process.returncode == 0:
            print('Successfully executed \"%s\"' % cmd)
        else:
            print('Failed to execute \"%s\"' % cmd)
            sys.exit(1)


def _publish_release(testing_release=False):
    _prompt_user_to_update_version()
    _run_cmd_or_fail('make build')

    _publish_package_to_pypi(testing_release)
    _push_new_release_to_git()


# List of things which this release tool does as of today.
USAGE_STRING = """
Release script for %s

Usage:
    release.py test release
    release.py production release
    
""" % _PROJECT_NAME


def _using_python2():
    return sys.version_info < (3, 0)


def main():
    if _using_python2():
        print('Python 2 is not supported, only Python 3 is supported')
        sys.exit(1)

    args = docopt.docopt(USAGE_STRING, version='1.0')
    if args['test'] and args['release']:
        _publish_release(testing_release=True)
    elif args['production'] and args['release']:
        _publish_release(testing_release=False)
    else:
        print('Unexpected command')
        sys.exit(1)


if __name__ == '__main__':
    main()
