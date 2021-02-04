import functools
import subprocess
import sys

try:
    # This fails when the code is executed directly and not as a part of python package installation,
    # I definitely need a better way to handle this.
    from adbe.output_helper import print_error, print_error_and_exit, print_verbose
except ImportError:
    # This works when the code is executed directly.
    from output_helper import print_error, print_error_and_exit, print_verbose


_adb_prefix = 'adb'
_IGNORED_LINES = [
    'WARNING: linker: libdvm.so has text relocations. This is wasting memory and is a security risk. Please fix.'
]

# Below version 24, if an adb shell command fails, then it still has an incorrect exit code of 0.
_MIN_VERSION_ABOVE_WHICH_ADB_SHELL_RETURNS_CORRECT_EXIT_CODE = 24

# This won't be required once I deprecate Python 2.
if sys.version_info[0] >= 3:
    unicode = str


def get_adb_prefix():
    return _adb_prefix


def set_adb_prefix(adb_prefix):
    # pylint: disable=global-statement
    global _adb_prefix
    _adb_prefix = adb_prefix


def get_adb_shell_property(property_name, device_serial=None):
    _, stdout, _ = execute_adb_shell_command2('getprop %s' % property_name, device_serial=device_serial)
    return stdout


def execute_adb_shell_command2(adb_cmd, piped_into_cmd=None, ignore_stderr=False, device_serial=None):
    return execute_adb_command2('shell %s' % adb_cmd, piped_into_cmd=piped_into_cmd,
                                ignore_stderr=ignore_stderr, device_serial=device_serial)


def execute_adb_command2(adb_cmd, piped_into_cmd=None, ignore_stderr=False, device_serial=None):
    adb_prefix = _adb_prefix
    if device_serial:
        adb_prefix = '%s -s %s' % (adb_prefix, device_serial)

    final_cmd = ('%s %s' % (adb_prefix, adb_cmd))
    if piped_into_cmd:
        final_cmd = '%s | %s' % (final_cmd, piped_into_cmd)

    print_verbose("Executing \"%s\"" % final_cmd)
    ps1 = subprocess.Popen(final_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_data, stderr_data = ps1.communicate()
    return_code = ps1.returncode
    try:
        stdout_data = stdout_data.decode('utf-8')
    except UnicodeDecodeError:
        print_error('Unable to decode data as UTF-8, defaulting to printing the binary data')
    stderr_data = stderr_data.decode('utf-8')

    _check_for_adb_not_found_error(stderr_data)
    _check_for_more_than_one_device_error(stderr_data)
    _check_for_device_not_found_error(stderr_data)
    if not ignore_stderr and stderr_data:
        print_error(stderr_data)

    if not stdout_data:
        return return_code, None, stderr_data

    # stdout_data is not None
    if isinstance(stdout_data, bytes):
        print_verbose("Result is \"%s\"" % stdout_data)
        return return_code, stdout_data, stderr_data
    # str for Python 3, this used to be unicode type for python 2
    elif isinstance(stdout_data, str):
        output = ''
        first_line = True
        for line in stdout_data.split('\n'):
            line = line.strip()
            if not line:
                continue
            if line in _IGNORED_LINES:
                continue
            if first_line:
                output += line
                first_line = False
            else:
                output += '\n' + line
        print_verbose("Result is \"%s\"" % output)
        return return_code, output, stderr_data
    else:
        print_error_and_exit('stdout_data is weird type: %s' % type(stdout_data))


def execute_adb_shell_command(adb_cmd, piped_into_cmd=None, ignore_stderr=False, device_serial=None):
    _, stdout, _ = execute_adb_command2(
        'shell %s' % adb_cmd, piped_into_cmd, ignore_stderr, device_serial=device_serial)
    return stdout


def execute_file_related_adb_shell_command(adb_shell_cmd, file_path, piped_into_cmd=None, ignore_stderr=False,
                                           device_serial=None):
    file_not_found_message = 'No such file or directory'
    is_a_directory_message = 'Is a directory'  # Error when someone tries to delete a dir with "-r"

    adb_cmds_prefix = []
    run_as_package = get_package(file_path)
    if run_as_package:
        adb_cmds_prefix.append('shell run-as %s' % run_as_package)
    if root_required_to_access_file(file_path):
        adb_cmds_prefix.append('shell su root')
    # As a backup, still try with a plain-old access, if run-as is not possible and root is not available.
    adb_cmds_prefix.append('shell')

    stdout = None
    attempt_count = 1
    for adb_cmd_prefix in adb_cmds_prefix:
        print_verbose('Attempt %d/%d: "%s"' % (attempt_count, len(adb_cmds_prefix), adb_cmd_prefix))
        attempt_count += 1
        adb_cmd = '%s %s' % (adb_cmd_prefix, adb_shell_cmd)
        return_code, stdout, stderr = execute_adb_command2(adb_cmd, piped_into_cmd, ignore_stderr,
                                                           device_serial=device_serial)

        if stderr.find(file_not_found_message) >= 0:
            print_error('File not found: %s' % file_path)
            return stderr
        if stderr.find(is_a_directory_message) >= 0:
            print_error('%s is a directory' % file_path)
            return stderr

        api_version = get_device_android_api_version()
        if api_version >= _MIN_VERSION_ABOVE_WHICH_ADB_SHELL_RETURNS_CORRECT_EXIT_CODE and return_code == 0:
            return stdout

    return stdout


# Gets the package name given a file path.
# Eg. if the file is in /data/data/com.foo/.../file1 then package is com.foo
# Limitation: Does not work with the new multi-user mode on Android.
def get_package(file_path):
    if file_path and file_path.startswith('/data/data/'):
        run_as_package = file_path.split('/')[3]
        return run_as_package
    return None


# adb shell getprop ro.build.version.sdk
@functools.lru_cache(maxsize=10)
def get_device_android_api_version(device_serial=None):
    version_string = get_adb_shell_property('ro.build.version.sdk', device_serial=device_serial)
    if version_string is None:
        print_error_and_exit('Unable to get Android device version, is it still connected?')
    return int(version_string)


def root_required_to_access_file(remote_file_path):
    if not remote_file_path:
        return False
    elif remote_file_path.startswith('/data/local/tmp'):
        return False
    elif remote_file_path.startswith('/sdcard'):
        return False
    return True


def _check_for_adb_not_found_error(stderr_data):
    if not stderr_data:
        return
    stderr_data = stderr_data.strip()
    if stderr_data.endswith('%s: command not found' % _adb_prefix):
        message = 'ADB (Android debug bridge) command not found.\n'
        message += 'Install ADB via https://developer.android.com/studio/releases/platform-tools.html'
        print_error_and_exit(message)


def _check_for_more_than_one_device_error(stderr_data):
    if not stderr_data:
        return
    for line in stderr_data.split('\n'):
        line = line.strip()
        if line:
            print_verbose(line)
        if line.find('error: more than one') != -1:
            message = ''
            message += 'More than one device/emulator are connected.\n'
            message += 'Please select a device by providing the serial ID (-s parameter).\n'
            message += 'You can list all connected devices/emulators via \"devices\" subcommand.'
            print_error_and_exit(message)


def _check_for_device_not_found_error(stderr_data):
    if not stderr_data:
        return
    for line in stderr_data.split('\n'):
        line = line.strip()
        if line:
            print_verbose(line)
        if line.find('error: device') > -1 and line.find('not found') > -1:
            print_error_and_exit(line)


def toggle_screen():
    return execute_adb_shell_command2("input keyevent KEYCODE_POWER")
