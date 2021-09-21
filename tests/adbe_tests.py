import functools
import re
import subprocess
import sys
import os
import time
import pytest

_SETTINGS_CMD_VERSION = 19
# Deut overdraw mode was added in API 19
_DEUT_ANDROID_VERSION = 19
# Doze mode was launched in API 23
_DOZE_MODE_ANDROID_VERSION = 23
# Runtime permissions were added in API 23
_RUNTIME_PERMISSIONS_SUPPORTED = 23

_PYTHON_CMD = 'python'
if sys.version_info >= (3, 0):
    _PYTHON_CMD = 'python%d.%d' % (sys.version_info.major, sys.version_info.minor)

_TEST_APP_ID = 'com.android.phone'
_DEBUG_APP = 'net.ashishb.deviceinformationhelper'
_TEST_NON_EXISTANT_APP_ID = 'com.android.nonexistant'
_DIR_PATH = '/data/data/%s' % _TEST_APP_ID
_TEST_PYTHON_INSTALLATION = False


# Source: https://gist.github.com/jasongrout/3804691
def run_once(f):
    """Runs a function (successfully) only once.
    The running can be reset by setting the `has_run` attribute to False
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            result = f(*args, **kwargs)
            wrapper.has_run = True
            return result
    wrapper.has_run = False
    return wrapper


# This method will be invoked only if testpythoninstallation is passed
def test_binary(testpythoninstallation):
    global _TEST_PYTHON_INSTALLATION
    if testpythoninstallation:
        _TEST_PYTHON_INSTALLATION = True


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

    # Only test with permissions which our test app com.android.phone has
    # or it fails
    # https://github.com/ashishb/adb-enhanced/pull/117/checks?check_run_id=655009375
    permissions_groups = ['phone']
    if _get_device_sdk_version() < 29:
        # This permissions group seems to have been removed in API 29 and beyond.
        # https://github.com/ashishb/adb-enhanced/runs/1799363523?check_suite_focus=true
        permissions_groups.append('contacts')
        permissions_groups.append('microphone')
        permissions_groups.append('location')
        permissions_groups.append('sms')

    for permission_group in permissions_groups:
        if _get_device_sdk_version() >= _RUNTIME_PERMISSIONS_SUPPORTED:
            _assert_success('permissions grant %s %s' % (test_app_id, permission_group))
            _assert_success('permissions revoke %s %s' % (test_app_id, permission_group))
        else:
            _assert_fail('permissions grant %s %s' % (test_app_id, permission_group))
            _assert_fail('permissions revoke %s %s' % (test_app_id, permission_group))

    _assert_fail('permissions grant %s %s' % (_TEST_NON_EXISTANT_APP_ID, 'sms'))
    _assert_fail('permissions revoke %s %s' % (_TEST_NON_EXISTANT_APP_ID, 'sms'))


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


def test_app_start_and_jank():
    _assert_success('start %s' % _TEST_APP_ID)
    # Jank requires app to be running.
    _assert_success('jank %s' % _TEST_APP_ID)
    # Command should fail for non-existant app
    _assert_fail('start %s' % _TEST_NON_EXISTANT_APP_ID)
    _assert_fail('jank %s' % _TEST_NON_EXISTANT_APP_ID)


def test_app_stop():
    _assert_success('stop %s' % _TEST_APP_ID)
    # Command should fail for non-existant app
    _assert_fail('stop %s' % _TEST_NON_EXISTANT_APP_ID)


def test_app_restart():
    _assert_success('restart %s' % _TEST_APP_ID)
    # Command should fail for non-existant app
    _assert_fail('restart %s' % _TEST_NON_EXISTANT_APP_ID)


def test_app_force_stop():
    _assert_success('force-stop %s' % _TEST_APP_ID)
    # Command should fail for non-existant app
    _assert_fail('force-stop %s' % _TEST_NON_EXISTANT_APP_ID)


def test_app_clear_data():
    _assert_success('clear-data %s' % _TEST_APP_ID)
    # Command should fail for non-existant app
    _assert_fail('clear-data %s' % _TEST_NON_EXISTANT_APP_ID)


@pytest.mark.skip("This fails on both Circle CI and Travis CI")
def test_app_backup_command():
    _assert_success('app backup %s %s-backup.tar' % (_TEST_APP_ID, _TEST_APP_ID))


def test_app_info_cmd():
    _assert_success('app info %s' % _TEST_APP_ID)
    # Command should fail for non-existant app
    _assert_fail('app info %s' % _TEST_NON_EXISTANT_APP_ID)


def test_app_signature_cmd():
    _assert_success('app signature %s' % _TEST_APP_ID)
    # Command should fail for non-existant app
    _assert_fail('app signature %s' % _TEST_NON_EXISTANT_APP_ID)


def test_app_path_cmd():
    app_path, _ = _assert_success('app path %s' % _TEST_APP_ID)
    print('app path is %s' % app_path)
    # Command should fail for non-existant app
    _assert_fail('app path %s' % _TEST_NON_EXISTANT_APP_ID)


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
    with subprocess.Popen('adb shell touch %s' % tmp_file,
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as ps:
        stdout, stderr = ps.communicate()
        assert ps.returncode == 0, 'File creation failed with stdout: "%s" and stderr: "%s"' % (stdout, stderr)
    _assert_success('rm %s' % tmp_file)
    _assert_fail('pull %s' % tmp_file)


def test_file_move1():
    tmp_file1 = '/data/local/tmp/tmp_file1'
    tmp_file2 = '/data/local/tmp/tmp_file2'

    dir_creation_cmd = 'adb shell mkdir /data/local/tmp'
    with subprocess.Popen(dir_creation_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as ps1:
        stdout, stderr = ps1.communicate()
        print('Stdout of \"%s\" is \"%s\"' % (dir_creation_cmd, stdout))
        print('Stderr of \"%s\" is \"%s\"' % (dir_creation_cmd, stderr))

    file_creation_cmd = 'adb shell touch %s' % tmp_file1

    with subprocess.Popen(file_creation_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as ps2:
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


@run_once
def _install_debug_apk():
    with subprocess.Popen('adb install -t -r ./tests/net.ashishb.deviceinformationhelper_debug_app.apk',
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as ps:
        stdout, stderr = ps.communicate()
        assert ps.returncode == 0, 'Install failed with stdout: "%s" and stderr: "%s"' % (stdout, stderr)


def test_file_move2():
    if _get_device_sdk_version() >= 29:
        pytest.skip('This test fails on API 29 and later as apps cannot move files from /data/ anymore, see https://github.com/ashishb/adb-enhanced/pull/141/checks?check_run_id=1723908892')

    _install_debug_apk()
    tmp_file1 = '/data/local/tmp/development.xml'
    tmp_file2_location = '/data/data/%s' % _DEBUG_APP
    with subprocess.Popen('adb shell touch %s' % tmp_file1,
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as ps1:
        stdout, stderr = ps1.communicate()
        assert ps1.returncode == 0, 'File creation failed with stdout: "%s" and stderr: "%s"' % (stdout, stderr)
    _assert_success('mv %s %s' % (tmp_file1, tmp_file2_location))
    _assert_fail('pull %s' % tmp_file1)
    _assert_success('pull %s/%s' % (tmp_file2_location, 'development.xml'))
    # Cleanup
    with subprocess.Popen('rm ./development.xml', shell=True) as ps2:
        ps2.communicate()
        assert ps2.returncode == 0, 'Failed to deleted pulled file development.xml'


def test_file_move3():
    _install_debug_apk()
    tmp_file1 = '/data/local/tmp/development2.xml'
    tmp_file2 = '/data/local/tmp/development.xml'
    with subprocess.Popen('adb shell touch %s' % tmp_file1,
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as ps1:
        stdout, stderr = ps1.communicate()
        assert ps1.returncode == 0, 'File creation failed with stdout: "%s" and stderr: "%s"' % (stdout, stderr)
        _assert_success('mv %s %s' % (tmp_file1, tmp_file2))
        _assert_fail('pull %s' % tmp_file1)
        _assert_success('pull %s' % tmp_file2)
    # Cleanup
    with subprocess.Popen('rm ./development.xml', shell=True) as ps2:
        ps2.communicate()
        assert ps2.returncode == 0, 'Failed to deleted pulled file development.xml'


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


def test_version():
    _assert_success('--version')


def test_wireless():
    # https://docs.github.com/en/actions/reference/environment-variables#default-environment-variables
    if os.environ.get('CI') == 'true':
        # https://github.com/ashishb/adb-enhanced/runs/1804885847?check_suite_focus=true
        pytest.skip('Emulator is not connected via wireless and thus, this test fails, so, skipping it')
    _assert_success('enable wireless debugging')
    # I hate this but without it disable fails due to race
    time.sleep(1)
    _assert_success('disable wireless debugging')


def test_screen_toggle():
    if _get_device_sdk_version() <= 16:
        pytest.skip('This test fails on API 16 and may be earlier, so, disable it https://github.com/ashishb/adb-enhanced/runs/1800432331?check_suite_focus=true')
    _assert_success('screen toggle')


def test_notifications():
    _assert_success('notifications list')


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
    if _TEST_PYTHON_INSTALLATION:
        cmd = 'adbe'
    else:
        dir_of_this_script = os.path.split(__file__)[0]
        adbe_py = os.path.join(dir_of_this_script, '../adbe/main.py')
        cmd = '%s %s' % (_PYTHON_CMD, adbe_py)
    with subprocess.Popen('%s %s' % (cmd, sub_cmd),
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as ps:
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
    with subprocess.Popen(cmd,
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as ps:
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
    test_app_start_and_jank()
    test_app_stop()
    test_app_restart()
    test_app_force_stop()
    test_app_clear_data()
    test_app_info_cmd()
    test_app_signature_cmd()
    test_app_path_cmd()

    # does not work on CircleCI or Travis CI
    # test_app_backup_command()

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
    test_version()
    test_wireless()
    test_screen_toggle()
    test_notifications()
    # TODO: Add a test for screen record after figuring out how to perform ^C while it is running.


if __name__ == '__main__':
    main()
