import functools
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

_SETTINGS_CMD_VERSION = 19
# Deut overdraw mode was added in API 19
_DEUT_ANDROID_VERSION = 19
# Doze mode was launched in API 23
_DOZE_MODE_ANDROID_VERSION = 23
# Runtime permissions were added in API 23
_RUNTIME_PERMISSIONS_SUPPORTED = 23
# Dark mode was added in API 29
_DARK_MODE_ANDROID_VERSION = 29
# The command to change location does not work below API 29
_LOCATION_CHANGE_ANDROID_VERSION = 29
# Navigation mode overlays were added in API 29
_NAVIGATION_MODE_ANDROID_VERSION = 29

_PYTHON_CMD = f"python{sys.version_info.major:d}.{sys.version_info.minor:d}"

_TEST_APP_ID = "com.android.phone"
_DEBUG_APP = "net.ashishb.deviceinformationhelper"
_TEST_NON_EXISTANT_APP_ID = "com.android.nonexistant"
_DIR_PATH = f"/data/data/{_TEST_APP_ID}"
_TEST_PYTHON_INSTALLATION = False


# Source: https://gist.github.com/jasongrout/3804691
def run_once(f: Callable) -> Callable[[tuple[Any, ...], dict[str, Any]], Any | None]:
    """Runs a function (successfully) only once.
    The running can be reset by setting the `has_run` attribute to False
    """
    @functools.wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Callable | None:
        if not wrapper.has_run:
            result = f(*args, **kwargs)
            wrapper.has_run = True
            return result
        return None
    wrapper.has_run = False
    return wrapper


# This method will be invoked only if testpythoninstallation is passed
def test_binary(testpythoninstallation: bool) -> None:
    global _TEST_PYTHON_INSTALLATION
    if testpythoninstallation:
        _TEST_PYTHON_INSTALLATION = True


def test_rotate() -> None:
    check = _assert_for_sdk(_SETTINGS_CMD_VERSION)

    check("rotate landscape")
    check("rotate portrait")
    check("rotate left")
    check("rotate right")


def test_gfx() -> None:
    _assert_success("gfx on")
    _assert_success("gfx off")
    _assert_success("gfx lines")


def test_overdraw() -> None:
    _assert_success("overdraw on")
    _assert_success("overdraw off")
    if _get_device_sdk_version() >= _DEUT_ANDROID_VERSION:
        _assert_success("overdraw deut")
    else:
        _assert_fail("overdraw deut")
    _assert_success("overdraw off")


def test_layout() -> None:
    _assert_success("layout on")
    _assert_success("layout off")


def test_airplane() -> None:
    check = _assert_for_sdk(_SETTINGS_CMD_VERSION)

    check("airplane on")
    check("airplane off")


def test_battery_sub_cmds() -> None:
    _assert_fail("battery level -1")
    _assert_fail("battery level 104")

    check = _assert_for_sdk(_SETTINGS_CMD_VERSION)

    check("battery level 10")
    check("battery saver on")
    check("battery saver off")
    check("battery reset")


def test_dark_mode() -> None:
    check = _assert_for_sdk(_DARK_MODE_ANDROID_VERSION)

    check("dark mode on")
    check("dark mode off")


def test_doze() -> None:
    check = _assert_for_sdk(_DOZE_MODE_ANDROID_VERSION)

    check("doze on")
    check("doze off")


def test_mobile_data() -> None:
    _assert_success("mobile-data on")
    _assert_success("mobile-data off")
    _assert_success("mobile-data saver on")
    _assert_success("mobile-data saver off")


def test_rtl() -> None:
    check = _assert_for_sdk(_SETTINGS_CMD_VERSION)

    check("rtl on")
    check("rtl off")


def test_animations() -> None:
    check = _assert_for_sdk(_SETTINGS_CMD_VERSION)

    check("animations on")
    check("animations off")


def test_permissions_list() -> None:
    _assert_success("permission-groups list all")
    _assert_success("permissions list all")
    _assert_success("permissions list dangerous")


def test_permissions_grant_revoke() -> None:
    test_app_id = _TEST_APP_ID

    # Only test with permissions which our test app com.android.phone has
    # or it fails
    # https://github.com/ashishb/adb-enhanced/pull/117/checks?check_run_id=655009375
    permissions_groups = ["phone"]
    if _get_device_sdk_version() < 29:
        # This permissions group seems to have been removed in API 29 and beyond.
        # https://github.com/ashishb/adb-enhanced/runs/1799363523?check_suite_focus=true
        permissions_groups.extend(("contacts", "microphone", "location", "sms"))
    if _get_device_sdk_version() >= 33:
        # Newly added permission in API 33
        # https://developer.android.com/develop/ui/views/notifications/notification-permission
        permissions_groups.append("notifications")

    for permission_group in permissions_groups:
        if _get_device_sdk_version() >= _RUNTIME_PERMISSIONS_SUPPORTED:
            _assert_success(f"permissions grant {test_app_id} {permission_group}")
            _assert_success(f"permissions revoke {test_app_id} {permission_group}")
        else:
            _assert_fail(f"permissions grant {test_app_id} {permission_group}")
            _assert_fail(f"permissions revoke {test_app_id} {permission_group}")

    _assert_fail(f"permissions grant {_TEST_NON_EXISTANT_APP_ID} sms")
    _assert_fail(f"permissions revoke {_TEST_NON_EXISTANT_APP_ID} sms")


# Cache the SDK version after first use
@functools.lru_cache(maxsize=1)
def _get_device_sdk_version() -> int:
    stdout_data, _ = _assert_success("devices")
    regex_result = re.search(r"SDK version: ([0-9]+)", stdout_data)
    assert regex_result is not None
    return int(regex_result.group(1))


def test_apps() -> None:
    _assert_success("apps list all")
    _assert_success("apps list system")
    _assert_success("apps list third-party")
    _assert_success("apps list debug")
    _assert_success("apps list backup-enabled")


def test_app_start_and_jank() -> None:
    _assert_success(f"start {_TEST_APP_ID}")
    # Jank requires app to be running.
    _assert_success(f"jank {_TEST_APP_ID}")
    # Command should fail for non-existant app
    _assert_fail(f"start {_TEST_NON_EXISTANT_APP_ID}")
    _assert_fail(f"jank {_TEST_NON_EXISTANT_APP_ID}")


def test_app_stop() -> None:
    _assert_success(f"stop {_TEST_APP_ID}")
    # Command should fail for non-existant app
    _assert_fail(f"stop {_TEST_NON_EXISTANT_APP_ID}")


def test_app_restart() -> None:
    _assert_success(f"restart {_TEST_APP_ID}")
    # Command should fail for non-existant app
    _assert_fail(f"restart {_TEST_NON_EXISTANT_APP_ID}")


def test_app_force_stop() -> None:
    _assert_success(f"force-stop {_TEST_APP_ID}")
    # Command should fail for non-existant app
    _assert_fail(f"force-stop {_TEST_NON_EXISTANT_APP_ID}")


def test_app_clear_data() -> None:
    _assert_success(f"clear-data {_TEST_APP_ID}")
    # Command should fail for non-existant app
    _assert_fail(f"clear-data {_TEST_NON_EXISTANT_APP_ID}")


@pytest.mark.skip("This fails on both Circle CI and Travis CI")
def test_app_backup_command() -> None:
    _assert_success(f"app backup {_TEST_APP_ID} {_TEST_APP_ID}-backup.tar")


def test_app_info_cmd() -> None:
    _assert_success(f"app info {_TEST_APP_ID}")
    # Command should fail for non-existant app
    _assert_fail(f"app info {_TEST_NON_EXISTANT_APP_ID}")


def test_app_signature_cmd() -> None:
    _assert_success(f"app signature {_TEST_APP_ID}")
    # Command should fail for non-existant app
    _assert_fail(f"app signature {_TEST_NON_EXISTANT_APP_ID}")


def test_app_path_cmd() -> None:
    app_path, _ = _assert_success(f"app path {_TEST_APP_ID}")
    print(f"app path is {app_path}")
    # Command should fail for non-existant app
    _assert_fail(f"app path {_TEST_NON_EXISTANT_APP_ID}")


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


def test_file_delete() -> None:
    tmp_file = "/data/local/tmp/tmp_file"
    _create_device_file(tmp_file)
    _assert_success(f"rm {tmp_file}")
    _assert_fail(f"pull {tmp_file}")


def test_file_move1() -> None:
    tmp_file1 = "/data/local/tmp/tmp_file1"
    tmp_file2 = "/data/local/tmp/tmp_file2"

    # The directory may already exist, so don't assert on the result.
    _run_shell_command("adb shell mkdir /data/local/tmp")
    _create_device_file(tmp_file1)

    _assert_success(f"mv {tmp_file1} {tmp_file2}")
    _assert_fail(f"pull {tmp_file1}")
    _assert_success("ls /data/local/tmp")
    _assert_success(f"pull {tmp_file2}")
    # Cleanup
    _delete_local_file("tmp_file2")


@run_once
def _install_debug_apk() -> None:
    _assert_shell_command("adb install -t -r ./tests/net.ashishb.deviceinformationhelper_debug_app.apk")


def test_file_move2() -> None:
    if _get_device_sdk_version() >= 29:
        pytest.skip("This test fails on API 29 and later as apps cannot move files from /data/ anymore, see https://github.com/ashishb/adb-enhanced/pull/141/checks?check_run_id=1723908892")

    _install_debug_apk()
    tmp_file1 = "/data/local/tmp/development.xml"
    tmp_file2_location = f"/data/data/{_DEBUG_APP}"
    _create_device_file(tmp_file1)
    _assert_success(f"mv {tmp_file1} {tmp_file2_location}")
    _assert_fail(f"pull {tmp_file1}")
    _assert_success(f"pull {tmp_file2_location}/development.xml")
    # Cleanup
    _delete_local_file("./development.xml")


def test_file_move3() -> None:
    _install_debug_apk()
    tmp_file1 = "/data/local/tmp/development2.xml"
    tmp_file2 = "/data/local/tmp/development.xml"
    _create_device_file(tmp_file1)
    _assert_success(f"mv {tmp_file1} {tmp_file2}")
    _assert_fail(f"pull {tmp_file1}")
    _assert_success(f"pull {tmp_file2}")
    # Cleanup
    _delete_local_file("./development.xml")


def test_list_devices() -> None:
    _assert_success("devices")


def test_list_top_activity() -> None:
    _assert_success("top-activity")


def test_dump_ui() -> None:
    xml_file = "tmp1.xml"
    _assert_success(f"dump-ui {xml_file} -v")
    # Cleanup
    _delete_local_file(xml_file)


def test_take_screenshot() -> None:
    png_file = "tmp1.png"
    _assert_success(f"screenshot {png_file} -v")
    # Cleanup
    _delete_local_file(png_file)


def test_keep_activities() -> None:
    check = _assert_for_sdk(_SETTINGS_CMD_VERSION)

    check("dont-keep-activities on")
    check("dont-keep-activities off")


def test_ls() -> None:
    _assert_success("ls -l -R /data/local/tmp")


def test_stay_awake_while_charging() -> None:
    check = _assert_for_sdk(_SETTINGS_CMD_VERSION)

    check("stay-awake-while-charging on")
    # This causes Circle CI to hang.
    # _assert_success('stay-awake-while-charging off')


def test_input_test() -> None:
    _assert_success('input-text "Hello"')


def test_press_back() -> None:
    _assert_success("press back")


def test_open_url() -> None:
    _assert_success("open-url google.com")


def test_version() -> None:
    _assert_success("--version")


def test_wireless() -> None:
    # https://docs.github.com/en/actions/reference/environment-variables#default-environment-variables
    if os.environ.get("CI") == "true":
        # https://github.com/ashishb/adb-enhanced/runs/1804885847?check_suite_focus=true
        pytest.skip("Emulator is not connected via wireless and thus, this test fails, so, skipping it")
    _assert_success("enable wireless debugging")
    # I hate this but without it disable fails due to race
    time.sleep(1)
    _assert_success("disable wireless debugging")


def test_screen_toggle() -> None:
    if _get_device_sdk_version() <= 16:
        pytest.skip("This test fails on API 16 and may be earlier, so, disable it https://github.com/ashishb/adb-enhanced/runs/1800432331?check_suite_focus=true")
    _assert_success("screen toggle")


def test_notifications() -> None:
    _assert_success("notifications list")


def test_location() -> None:
    check = _assert_for_sdk(_LOCATION_CHANGE_ANDROID_VERSION)
    check("location on")
    check("location off")


def test_navigation() -> None:
    check = _assert_for_sdk(_NAVIGATION_MODE_ANDROID_VERSION)

    original_mode, _ = check("navigation")
    try:
        check("navigation gestural")
        check("navigation twobutton")
        check("navigation threebutton")
    finally:
        if original_mode in {"gestural", "twobutton", "threebutton"}:
            _execute(f"navigation {original_mode}")


def test_debug_app() -> None:
    _assert_success(f"debug-app set {_TEST_APP_ID}")
    _assert_success("debug-app clear")


def _assert_for_sdk(min_sdk_version: int) -> Callable[[str], tuple[str, str]]:
    """Returns _assert_success when the device SDK supports the command, else _assert_fail."""
    return _assert_success if _get_device_sdk_version() >= min_sdk_version else _assert_fail


def _assert_fail(sub_cmd: str) -> tuple[str, str]:
    exit_code, stdout_data, stderr_data = _execute(sub_cmd)
    assert exit_code == 1, f'Command "{sub_cmd}" failed with stdout: "{stdout_data}" and stderr: "{stderr_data}"'
    return stdout_data, stderr_data


def _assert_success(sub_cmd: str) -> tuple[str, str]:
    exit_code, stdout_data, stderr_data = _execute(sub_cmd)
    assert exit_code == 0, f'Command "{sub_cmd}" failed with stdout: "{stdout_data}" and stderr: "{stderr_data}"'
    return stdout_data, stderr_data


def _execute(sub_cmd: str) -> tuple[int, str, str]:
    print(f"Executing cmd: {sub_cmd}")
    if _TEST_PYTHON_INSTALLATION:
        cmd = "adbe"
    else:
        adbe_py = Path(__file__).parent / "../adbe/main.py"
        cmd = f"{_PYTHON_CMD} {adbe_py}"
    exit_code, stdout_data, stderr_data = _run_shell_command(f"{cmd} {sub_cmd}")
    print(f'Result is "{stdout_data}"')
    if exit_code != 0:
        print(f'Stderr is "{stderr_data}"')
    return exit_code, stdout_data, stderr_data


def _run_shell_command(cmd: str) -> tuple[int, str, str]:
    """Runs a shell command and returns (exit_code, stdout, stderr) with output decoded and stripped."""
    with subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as ps:
        stdout_data, stderr_data = ps.communicate()
        exit_code = ps.returncode
    return exit_code, stdout_data.decode("utf-8").strip(), stderr_data.decode("utf-8").strip()


def _assert_shell_command(cmd: str) -> tuple[str, str]:
    """Runs a shell command, asserts it succeeds, and returns (stdout, stderr)."""
    exit_code, stdout_data, stderr_data = _run_shell_command(cmd)
    assert exit_code == 0, f'Command "{cmd}" failed with stdout: "{stdout_data}" and stderr: "{stderr_data}"'
    return stdout_data, stderr_data


def _create_device_file(remote_path: str) -> None:
    _assert_shell_command(f"adb shell touch {remote_path}")


def _delete_local_file(local_file_path: str) -> None:
    _assert_shell_command(f"rm {local_file_path}")


def main() -> None:
    test_rotate()
    test_gfx()
    test_overdraw()
    test_layout()
    test_airplane()
    test_battery_sub_cmds()
    test_dark_mode()
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
    test_file_move3()
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
    test_location()
    test_navigation()
    test_debug_app()
    # TODO: Add a test for screen record after figuring out how to perform ^C while it is running.


if __name__ == "__main__":
    main()
