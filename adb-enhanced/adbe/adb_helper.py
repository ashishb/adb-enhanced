import subprocess

try:
    # This fails when the code is executed directly and not as a part of python package installation,
    # I definitely need a better way to handle this.
    from adbe.output_helper import print_message, print_error, print_error_and_exit, print_verbose
except ImportError as e:
    # This works when the code is executed directly.
    from output_helper import print_message, print_error, print_error_and_exit, print_verbose


_adb_prefix = 'adb'

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
        print_verbose("Executing \"%s | %s\"" % (final_cmd, piped_into_cmd))
        ps1 = subprocess.Popen(final_cmd, shell=True, stdout=subprocess.PIPE,
                               stderr=None if ignore_stderr is False else open(os.devnull, 'w'))
        output = subprocess.check_output(
            piped_into_cmd, shell=True, stdin=ps1.stdout)
        print_message(output)
        return output
    else:
        print_verbose("Executing \"%s\"" % final_cmd)
        ps1 = subprocess.Popen(final_cmd, shell=True, stdout=subprocess.PIPE,
                               stderr=None if ignore_stderr is False else open(os.devnull, 'w'))
        output = ''
        first_line = True
        for line in ps1.stdout:
            if first_line:
                output += line.decode('utf-8').strip()
                first_line = False
            else:
                output += '\n' + line.decode('utf-8').strip()
        print_verbose("Result is \"%s\"" % output)
        return output