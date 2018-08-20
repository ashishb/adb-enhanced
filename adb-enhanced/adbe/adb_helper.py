import subprocess
import os

try:
    # This fails when the code is executed directly and not as a part of python package installation,
    # I definitely need a better way to handle this.
    from adbe.output_helper import print_message, print_error, print_error_and_exit, print_verbose
except ImportError:
    # This works when the code is executed directly.
    from output_helper import print_message, print_error, print_error_and_exit, print_verbose


_adb_prefix = 'adb'
_IGNORED_LINES = [
    'WARNING: linker: libdvm.so has text relocations. This is wasting memory and is a security risk. Please fix.'
]


def get_adb_prefix():
    return _adb_prefix


def set_adb_prefix(adb_prefix):
    global _adb_prefix
    _adb_prefix = adb_prefix


def execute_adb_shell_command(adb_cmd, piped_into_cmd=None, ignore_stderr=False):
    return execute_adb_command('shell %s' % adb_cmd, piped_into_cmd, ignore_stderr)


def execute_adb_command(adb_cmd, piped_into_cmd=None, ignore_stderr=False):
    final_cmd = ('%s %s' % (_adb_prefix, adb_cmd))
    if piped_into_cmd:
        final_cmd = '%s | %s' % (final_cmd, piped_into_cmd)

    print_verbose("Executing \"%s\"" % final_cmd)
    ps1 = subprocess.Popen(final_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_data, stderr_data = ps1.communicate()
    stdout_data = stdout_data.decode('utf-8')
    stderr_data = stderr_data.decode('utf-8')

    _check_for_more_than_one_device_error(stderr_data)
    _check_for_device_not_found_error(stderr_data)
    if not ignore_stderr and stderr_data and len(stderr_data) > 0:
        print_error(stderr_data)

    output = ''
    first_line = True
    if stdout_data:
        for line in stdout_data.split('\n'):
            line = line.strip()
            if not line or len(line) == 0:
                continue
            if line in _IGNORED_LINES:
                continue
            if first_line:
                output += line
                first_line = False
            else:
                output += '\n' + line
    print_verbose("Result is \"%s\"" % output)
    return output


def _check_for_more_than_one_device_error(stderr_data):
    if not stderr_data:
        return
    for line in stderr_data.split('\n'):
        line = line.strip()
        if line and len(line) > 0:
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
        if line and len(line) > 0:
            print_verbose(line)
        if line.find('error: device') > -1 and line.find('not found') > -1:
            print_error_and_exit(line)
