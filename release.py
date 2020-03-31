#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import docopt

_DIR_OF_THIS_SCRIPT = os.path.split(__file__)[0]
_VERSION_FILE_NAME = 'version.txt'
_VERSION_FILE_PATH = os.path.join(
    _DIR_OF_THIS_SCRIPT, 'adbe', _VERSION_FILE_NAME)
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
    'version.txt',
    ]


def _get_version():
    with open(_VERSION_FILE_PATH, 'r') as file_handle:
        version = file_handle.read().strip()
        return version


def _set_version(version):
    if not version or len(version.strip()) == 0:
        raise Exception('version cannot be empty')
    with open(_VERSION_FILE_PATH, 'w') as file_handle:
        file_handle.write('%s\n' % version)


def _prompt_user_to_update_version(version_file):
    current_version = _get_version()
    print('Current version is %s' % current_version)
    new_version = input("Enter new version: ")
    _set_version(new_version or current_version)
    file_handle = open(version_file, 'w')
    file_handle.write(new_version)
    file_handle.close()


def _copy_files(src_file_names, src_dir, dest_dir):
    for src_file in src_file_names:
        src_path = os.path.join(src_dir, src_file)
        dest_path = os.path.join(dest_dir, src_file.split('/')[-1])
        _run_cmd_or_fail('cp %s %s' % (src_path, dest_path))


def _update_python_setup_tools():
    setup_tools = ['setuptools', 'wheel', 'twine']
    cmd = 'python3 -m pip install --user --upgrade %s' % ' '.join(setup_tools)
    _run_cmd_or_fail(cmd)


def _cleanup_build_dir(base_dir):
    build_dirs = ['build', 'dist']
    for build_dir in build_dirs:
        full_path = os.path.join(base_dir, build_dir)
        if os.path.exists(full_path):
            print('Deleting %s' % full_path)
            shutil.rmtree(full_path)


def _create_package():
    _run_cmd_or_fail('python3 %s/setup.py sdist bdist_wheel' % _DIR_OF_THIS_SCRIPT)

def _check_package():
    _run_cmd_or_fail('python3 -m twine check dist/*')


def _push_new_release_to_git(version_file):
    version = open(version_file).read()
    cmds = [
        'git add %s' % version_file,
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
    process = subprocess.Popen(cmd, shell=True, stdout=None, stderr=None)
    process.communicate()
    if process.returncode == 0:
        print('Successfully executed \"%s\"' % cmd)
    else:
        print('Failed to execute \"%s\"' % cmd)
        sys.exit(1)


def _publish_release(testing_release=False):
    version_file = os.path.join('adbe', 'version.txt')

    _prompt_user_to_update_version(version_file)

    _update_python_setup_tools()
    _cleanup_build_dir(_DIR_OF_THIS_SCRIPT)
    _create_package()
    _check_package()

    _push_new_release_to_git(version_file)
    _publish_package_to_pypi(testing_release)
    _cleanup_build_dir(_DIR_OF_THIS_SCRIPT)


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
