import re
import subprocess
import sys
import os

_SETTINGS_CMD_VERSION = 19
# Deut overdraw mode was added in API 19
_DEUT_ANDROID_VERSION = 19
# Doze mode was launched in API 23
_DOZE_MODE_ANDROID_VERSION = 23
# Runtime permissions were added in API 23
_RUNTIME_PERMISSIONS_SUPPORTED = 23

_PYTHON_CMD = 'python'
if sys.version_info >= (3, 0):
    _PYTHON_CMD = 'python3'

_TEST_APP_ID = 'com.android.phone'
_DIR_PATH = '/data/data/%s' % _TEST_APP_ID


def test_rotate():
    if _get_device_sdk_version() >= _SETTINGS_CMD_VERSION:
        check = _assert_success
    else:
        check = _assert_fail

    check('rotate landscape')
    check('rotate portrait')
    check('rotate left')
    check('rotate right')


def test_gfx():
    _assert_success('gfx on')
    _assert_success('gfx off')
    _assert_success('gfx lines')


def test_overdraw():
    _assert_success('overdraw on')
    _assert_success('overdraw off')
    if _get_device_sdk_version() >= _DEUT_ANDROID_VERSION:
        _assert_success('overdraw deut')
    else:
        _assert_fail('overdraw deut')
    _assert_success('overdraw off')


def test_layout():
    _assert_success('layout on')
    _assert_success('layout off')


def test_airplane():
    if _get_device_sdk_version() >= _SETTINGS_CMD_VERSION:
        check = _assert_success
    else:
        check = _assert_fail

    check('airplane on')
    check('airplane off')


def test_battery_sub_cmds():
    _assert_fail('battery level -1')
    _assert_fail('battery level 104')

    if _get_device_sdk_version() >= _SETTINGS_CMD_VERSION:
        check = _assert_success
    else:
        check = _assert_fail

    check('battery level 10')
    check('battery saver on')
    check('battery saver off')
    check('battery reset')


def test_doze():
    if _get_device_sdk_version() >= _DOZE_MODE_ANDROID_VERSION:
        check = _assert_success
    else:
        check = _assert_fail

    check('doze on')
    check('doze off')


def test_mobile_data():
    _assert_success('mobile-data on')
    _assert_success('mobile-data off')
    _assert_success('mobile-data saver on')
    _assert_success('mobile-data saver off')


def test_rtl():
    if _get_device_sdk_version() >= _SETTINGS_CMD_VERSION:
        check = _assert_success
    else:
        check = _assert_fail

    check('rtl on')
    check('rtl off')


def test_animations():
    if _get_device_sdk_version() >= _SETTINGS_CMD_VERSION:
        check = _assert_success
    else:
        check = _assert_fail

    check('animations on')
    check('animations off')


def test_permissions_list():
    _assert_success('permission-groups list all')
    _assert_success('permissions list all')
    _assert_success('permissions list dangerous')


def test_permissions_grant_revoke():
    test_app_id = _TEST_APP_ID

    permissions_groups = ['calendar', 'camera', 'contacts', 'location', 'microphone', 'phone', 'sensors',
                         'sms', 'storage']

    for permission_group in permissions_groups:
        if _get_device_sdk_version() >= _RUNTIME_PERMISSIONS_SUPPORTED:
            _assert_success('permissions grant %s %s' % (test_app_id, permission_group))
            _assert_success('permissions revoke %s %s' % (test_app_id, permission_group))
        else:
            _assert_fail('permissions grant %s %s' % (test_app_id, permission_group))
            _assert_fail('permissions revoke %s %s' % (test_app_id, permission_group))


def _get_device_sdk_version():
    stdout_data, _ = _assert_success('devices')
    regex_result = re.search('SDK version: ([0-9]+)', stdout_data)
    assert regex_result is not None
    sdk_version = int(regex_result.group(1))
    return sdk_version


def test_apps():
    _assert_success('apps list all')
    _assert_success('apps list system')
    _assert_success('apps list third-party')
    _assert_success('apps list debug')
    _assert_success('apps list backup-enabled')


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


# # TODO: For some reasons, these are not working. Disabled for now.
# # See https://circleci.com/gh/ashishb/adb-enhanced/106
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


def test_file_delete():
    tmp_file = '/data/local/tmp/tmp_file'
    ps = subprocess.Popen('adb shell touch %s' % tmp_file,
                          shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = ps.communicate()
    assert ps.returncode == 0, 'File creation failed with stdout: "%s" and stderr: "%s"' % (stdout, stderr)
    _assert_success('rm %s' % tmp_file)
    _assert_fail('pull %s' % tmp_file)


def test_file_move1():
    tmp_file1 = '/data/local/tmp/tmp_file1'
    tmp_file2 = '/data/local/tmp/tmp_file2'

    dir_creation_cmd = 'adb shell mkdir /data/local/tmp'
    ps1 = subprocess.Popen(dir_creation_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = ps1.communicate()
    print('Stdout of \"%s\" is \"%s\"' % (dir_creation_cmd, stdout))
    print('Stderr of \"%s\" is \"%s\"' % (dir_creation_cmd, stderr))

    file_creation_cmd = 'adb shell touch %s' % tmp_file1
    ps2 = subprocess.Popen(file_creation_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = ps2.communicate()
    assert ps2.returncode == 0, 'File creation failed with stdout: "%s" and stderr: "%s"' % (stdout, stderr)
    print('Stdout of \"%s\" is \"%s\"' % (file_creation_cmd, stdout))
    print('Stderr of \"%s\" is \"%s\"' % (file_creation_cmd, stderr))

    _assert_success('mv %s %s' % (tmp_file1, tmp_file2))
    _assert_fail('pull %s' % tmp_file1)
    stdout, stderr = _assert_success('ls /data/local/tmp')
    print('Stdout of "adbe ls /data/local/tmp" is \"%s\"' % stdout)
    print('Stderr of "adbe ls /data/local/tmp" is \"%s\"' % stderr)
    _assert_success('pull %s' % tmp_file2)
    # Cleanup
    _delete_local_file('tmp_file2')


def test_file_move2():
    tmp_file1 = '/data/local/tmp/development.xml'
    tmp_file2 = '/data/data/com.android.contacts'
    ps = subprocess.Popen('adb shell touch %s' % tmp_file1,
                          shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = ps.communicate()
    assert ps.returncode == 0, 'File creation failed with stdout: "%s" and stderr: "%s"' % (stdout, stderr)
    _assert_success('mv %s %s' % (tmp_file1, tmp_file2))
    _assert_fail('pull %s' % tmp_file1)
    _assert_success('pull %s' % tmp_file2)


def test_list_devices():
    _assert_success('devices')


def test_list_top_activity():
    _assert_success('top-activity')


def test_dump_ui():
    xml_file = 'tmp1.xml'
    _assert_success('dump-ui %s -v' % xml_file)
    # Cleanup
    _delete_local_file(xml_file)


def test_take_screenshot():
    png_file = 'tmp1.png'
    _assert_success('screenshot %s -v' % png_file)
    # Cleanup
    _delete_local_file(png_file)


def test_keep_activities():
    if _get_device_sdk_version() >= _SETTINGS_CMD_VERSION:
        check = _assert_success
    else:
        check = _assert_fail

    check('dont-keep-activities on')
    check('dont-keep-activities off')


def test_ls():
    _assert_success('ls -l -R /data/local/tmp')


def test_stay_awake_while_charging():
    if _get_device_sdk_version() >= _SETTINGS_CMD_VERSION:
        check = _assert_success
    else:
        check = _assert_fail

    check('stay-awake-while-charging on')
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
    adbe_py = os.path.join(dir_of_this_script, '../src/main.py')
    ps = subprocess.Popen('%s %s --no-python2-warn %s' % (_PYTHON_CMD, adbe_py, sub_cmd),
                          shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_data, stderr_data = ps.communicate()
    stdout_data = stdout_data.decode('utf-8').strip()
    stderr_data = stderr_data.decode('utf-8').strip()
    exit_code = ps.returncode
    print('Result is "%s"' % stdout_data)
    if exit_code != 0:
        print('Stderr is "%s"' % stderr_data)
    return exit_code, stdout_data, stderr_data


def _delete_local_file(local_file_path):
    cmd = 'rm %s' % local_file_path
    ps = subprocess.Popen(cmd,
                          shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_data, stderr_data = ps.communicate()
    stdout_data = stdout_data.decode('utf-8').strip()
    stderr_data = stderr_data.decode('utf-8').strip()
    exit_code = ps.returncode
    assert exit_code == 0, 'Command "%s" failed with stdout: "%s" and stderr: "%s"' % (
        cmd, stdout_data, stderr_data)


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
    test_permissions_list()
    test_permissions_grant_revoke()
    test_apps()
    test_app_start_related_cmds()
    test_app_info_related_cmds()
    test_file_delete()
    test_file_move1()
    test_file_move2()
    test_list_devices()
    test_list_top_activity()
    test_dump_ui()
    test_take_screenshot()
    test_keep_activities()
    test_ls()
    test_stay_awake_while_charging()
    test_input_test()
    test_press_back()
    test_open_url()
    # TODO: Add a test for screen record after figuring out how to perform ^C while it is running.


if __name__ == '__main__':
    main()

