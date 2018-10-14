import subprocess
import sys
import os

_PYTHON_CMD = 'python'
if sys.version_info >= (3, 0):
    _PYTHON_CMD = 'python3'


def test_rotate():
    _assert_success('rotate landscape')
    _assert_success('rotate portrait')
    _assert_success('rotate left')
    _assert_success('rotate right')


def test_gfx():
    _assert_success('gfx on')
    _assert_success('gfx off')
    _assert_success('gfx lines')


def test_overdraw():
    _assert_success('overdraw on')
    _assert_success('overdraw off')
    _assert_success('overdraw deut')
    _assert_success('overdraw off')


def test_layout():
    _assert_success('layout on')
    _assert_success('layout off')


def test_airplane():
    _assert_success('airplane on')
    _assert_success('airplane off')


def test_battery_sub_cmds():
    _assert_fail('battery level -1')
    _assert_success('battery level 10')
    _assert_fail('battery level 104')
    _assert_success('battery saver on')
    _assert_success('battery saver off')
    _assert_success('battery reset')


def test_doze():
    _assert_success('doze on')
    _assert_success('doze off')


def test_mobile_data():
    _assert_success('mobile-data on')
    _assert_success('mobile-data off')
    _assert_success('mobile-data saver on')
    _assert_success('mobile-data saver off')


def test_rtl():
    _assert_success('rtl on')
    _assert_success('rtl off')


def test_animations():
    _assert_success('animations on')
    _assert_success('animations off')


def test_permissions():
    _assert_success('permission-groups list all')
    _assert_success('permissions list all')
    _assert_success('permissions list dangerous')

    stdout_data, _ = _assert_success('devices')
    import re
    regex_result = re.search('SDK version: ([0-9]+)', stdout_data)
    assert regex_result is not None
    sdk_version = int(regex_result.group(1))
    test_app_id = 'com.android.phone'
    permissions_groups = ['calendar', 'camera', 'contacts', 'location', 'microphone', 'phone', 'sensors',
                         'sms', 'storage']
    for permission_group in permissions_groups:
        if sdk_version >= 23:
            _assert_success('permissions grant %s %s' % (test_app_id, permission_group))
            _assert_success('permissions revoke %s %s' % (test_app_id, permission_group))
        else:
            _assert_fail('permissions grant %s %s' % (test_app_id, permission_group))
            _assert_fail('permissions revoke %s %s' % (test_app_id, permission_group))


def test_apps():
    _assert_success('apps list all')
    _assert_success('apps list system')
    _assert_success('apps list third-party')
    _assert_success('apps list debug')
    _assert_success('apps list backup-enabled')


_TEST_APP_ID = 'com.android.phone'
_DIR_PATH = '/data/data/%s' % _TEST_APP_ID


def test_app_start_related_cmds():
    _assert_success('start %s' % _TEST_APP_ID)
    # Jank requires app to be running.
    _assert_success('jank %s' % _TEST_APP_ID)
    _assert_success('stop %s' % _TEST_APP_ID)
    _assert_success('restart %s' % _TEST_APP_ID)
    _assert_success('force-stop %s' % _TEST_APP_ID)
    _assert_success('clear-data %s' % _TEST_APP_ID)


def test_app_info_related_cmds():
    _assert_success('app info %s' % _TEST_APP_ID)
    _assert_success('app signature %s' % _TEST_APP_ID)
    # This fails on both Circle CI and Travis
    # _assert_success('app backup %s %s-backup.tar' % (_TEST_APP_ID, _TEST_APP_ID))
    app_path, _ = _assert_success('app path %s' % _TEST_APP_ID)
    print('app path is %s' % app_path)

# TODO: For some reasons, these are not working. Disabled for now.
# See https://circleci.com/gh/ashishb/adb-enhanced/106
# def test_file_related_cmds():
#     # Create a temporary file
#     tmp_file = ' /data/local/tmp/tmp_file'
#     ps = subprocess.Popen('adb shell touch %s' % tmp_file,
#                           shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#     stdout, stderr = ps.communicate()
#     print('File creation result stdout: "%s" and stderr: "%s"' % (stdout, stderr))
#     assert ps.returncode == 0, 'File creation failed with stdout: "%s" and stderr: "%s"' % (stdout, stderr)
#
#     _assert_success('pull %s' % tmp_file)
#     _assert_success('pull %s tmp2' % tmp_file)
#     _assert_success('cat %s' % tmp_file)


def test_list_devices():
    _assert_success('devices')


def test_list_top_activity():
    _assert_success('top-activity')


def test_dump_ui():
    _assert_success('dump-ui tmp1.xml -v')


def test_take_screenshot():
    _assert_success('screenshot tmp1.png -v')


def test_keep_acivities():
    _assert_success('dont-keep-activities on')
    _assert_success('dont-keep-activities off')


def test_misc():
    _assert_success('ls -l -R /data/local/tmp')
    _assert_success('rm -rf /data/local/tmp')
    # TODO: Add a test for screen record after figuring out how to perform ^C while it is running.
    _assert_success('stay-awake-while-charging on')
    # This causes Circle CI to hang.
    # _assert_success('stay-awake-while-charging off')


def test_input_test():
    _assert_success('input-text "Hello"')


def test_press_back():
    _assert_success('press back')


def test_open_url():
    _assert_success('open-url google.com')


def _assert_fail(sub_cmd):
    exit_code, stdout_data, stderr_data = _execute(sub_cmd)
    assert exit_code == 1, 'Command "%s" failed with stdout: "%s" and stderr: "%s"' %(sub_cmd, stdout_data, stderr_data)
    return stdout_data, stderr_data


def _assert_success(sub_cmd):
    exit_code, stdout_data, stderr_data = _execute(sub_cmd)
    assert exit_code == 0, 'Command "%s" failed with stdout: "%s" and stderr: "%s"' % (sub_cmd, stdout_data, stderr_data)
    return stdout_data, stderr_data


def _execute(sub_cmd):
    print('Executing cmd: %s' % sub_cmd)
    dir_of_this_script = os.path.split(__file__)[0]
    adbe_py = os.path.join(dir_of_this_script, '../src/adbe.py')
    ps = subprocess.Popen('%s %s %s' % (_PYTHON_CMD, adbe_py, sub_cmd),
                          shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_data, stderr_data = ps.communicate()
    stdout_data = stdout_data.decode('utf-8').strip()
    stderr_data = stderr_data.decode('utf-8').strip()
    exit_code = ps.returncode
    print('Result is "%s"' % stdout_data)
    if exit_code != 0:
        print('Stderr is "%s"' % stderr_data)
    return exit_code, stdout_data, stderr_data


def main():
    test_rotate()
    test_gfx()
    test_overdraw()
    test_layout()
    test_airplane()
    test_battery_sub_cmds()
    test_doze()
    test_mobile_data()
    test_rtl()
    test_animations()
    test_permissions()
    test_apps()
    test_app_related_cmds()
    test_misc()


if __name__ == '__main__':
    main()

