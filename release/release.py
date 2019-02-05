#!/usr/bin/env python3
import os
import subprocess
import sys
import docopt

_DIR_OF_THIS_SCRIPT = os.path.split(__file__)[0]
_VERSION_FILE_NAME = 'version.txt'
_VERSION_FILE_PATH = os.path.join(
    _DIR_OF_THIS_SCRIPT, '..', 'src', _VERSION_FILE_NAME)
_README_FILE_NAME = 'README.md'
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
    with open(_VERSION_FILE_PATH, 'w') as file_handle:
        file_handle.write('%s\n' % version)

def _prompt_user_to_update_version(version_file):
    version = _get_version()
    print('Current version is %s' % version)
    new_version = input("Enter new version: ")
    _set_version(new_version)
    file_handle = open(version_file, 'w')
    file_handle.write(new_version)
    file_handle.close()


def _copy_files(src_file_names, src_dir, dest_dir):
    for src_file in src_file_names:
        src_path = os.path.join(src_dir, src_file)
        dest_path = os.path.join(dest_dir, src_file)
        _run_cmd_or_fail('cp %s %s' % (src_path, dest_path))


def _update_python_setup_tools():
    setup_tools = ['setuptools', 'wheel', 'twine']
    cmd = 'python3 -m pip install --user --upgrade %s' % ' '.join(setup_tools)
    _run_cmd_or_fail(cmd)


def _cleanup_build_dir(base_dir):
    build_dirs = ['build', 'dist']
    for build_dir in build_dirs:
        if os.path.exists(build_dir):
            full_path = os.path.join(base_dir, build_dir)
            print('Deleting %s' % full_path)
            os.removedirs(full_path)


def _create_package():
    _run_cmd_or_fail('python3 setup.py sdist bdist_wheel')


def _push_new_release_to_git(version_file):
    version = open(version_file).read()
    cmds = [
        'git add %s' % version_file,
        'git commit -m "Setup release %s"' % version,
        'git tag %s' % version,
        'git push origin master',
        'git push origin master --tags',
    ]
    for cmd in cmds:
        _run_cmd_or_fail(cmd)


def _publish_package_to_pypi(pypi_url=None):
    if pypi_url:
        # Use pypi_url = "https://test.pypi.org/legacy/" to test
        _run_cmd_or_fail(
            'python3 -m twine upload --repository-url %s dist/*' % pypi_url)
        print('Few mins later, check %s/project/%s/#history to confirm upload' %
              (pypi_url, _PROJECT_NAME))
    else:
        _run_cmd_or_fail('python3 -m twine upload dist/*')
        print('Few mins later, check https://pypi.org/project/%s/#history to confirm upload' %
              _PROJECT_NAME)


def _run_cmd_or_fail(cmd):
    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process.communicate()
    if process.returncode == 0:
        print('Successfully executed \"%s\"' % cmd)
    else:
        print('Failed to execute \"%s\"' % cmd)
        sys.exit(1)

def _publish_release(pypi_url=None):
    src_dir = os.path.join(_DIR_OF_THIS_SCRIPT, '..', 'src')
    dest_dir = os.path.join(_DIR_OF_THIS_SCRIPT, 'adbe')
    version_file = os.path.join(src_dir, 'version.txt')

    _prompt_user_to_update_version(version_file)
    _copy_files(_SRC_FILE_NAMES, src_dir, dest_dir)
    _copy_files([_README_FILE_NAME], os.path.join(
        _DIR_OF_THIS_SCRIPT, '..'), _DIR_OF_THIS_SCRIPT)
    _update_python_setup_tools()
    _cleanup_build_dir(_DIR_OF_THIS_SCRIPT)
    _create_package()
    _push_new_release_to_git(version_file)
    _publish_package_to_pypi(pypi_url)
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
        _publish_release(pypi_url=_TEST_PYPI_URL)
    elif args['production'] and args['release']:
        _publish_release()
    else:
        print('Unexpected command')
        sys.exit(1)


if __name__ == '__main__':
    main()
