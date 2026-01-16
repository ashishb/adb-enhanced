#!/usr/bin/env python3
import dataclasses
import os
import re
import secrets
import signal
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from collections.abc import Callable
from enum import Enum
from functools import partial, wraps
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import psutil

try:
    # This fails when the code is executed directly and not as a part of python package installation,
    # I definitely need a better way to handle this.
    # asyncio was introduced in version 3.5
    from adbe import asyncio_helper
    from adbe.adb_helper import (
        CommandResult,
        execute_adb_command2,
        execute_adb_shell_command2,
        execute_adb_shell_command3,
        execute_file_related_adb_shell_command,
        get_adb_shell_property,
        get_device_android_api_version,
        get_package,
        root_required_to_access_file,
        toggle_screen,
    )
    from adbe.output_helper import (
        print_error,
        print_error_and_exit,
        print_message,
        print_verbose,
    )
# Python 3.6 onwards, this throws ModuleNotFoundError
except ModuleNotFoundError:
    # This works when the code is executed directly.
    # noinspection PyUnresolvedReferences
    import asyncio_helper
    from adb_helper import (
        CommandResult,
        execute_adb_command2,
        execute_adb_shell_command2,
        execute_adb_shell_command3,
        execute_file_related_adb_shell_command,
        get_adb_shell_property,
        get_device_android_api_version,
        get_package,
        root_required_to_access_file,
        toggle_screen,
    )

    # noinspection PyUnresolvedReferences
    from output_helper import (
        print_error,
        print_error_and_exit,
        print_message,
        print_verbose,
    )


_KEYCODE_BACK = 4
_MIN_API_FOR_RUNTIME_PERMISSIONS = 23
_MIN_API_FOR_DARK_MODE = 29
_MIN_API_FOR_LOCATION = 29

_REGEX_BACKUP_ALLOWED = "(pkgFlags|flags).*ALLOW_BACKUP"
_REGEX_DEBUGGABLE = "(pkgFlags|flags).*DEBUGGABLE"

# Value to be return as 'on' to the user
_USER_PRINT_VALUE_ON = "on"
# Value to be return as 'partially on' to the user
_USER_PRINT_VALUE_PARTIALLY_ON = "partially on"
# Value to be return as 'off' to the user
_USER_PRINT_VALUE_OFF = "off"
# Value to be return as 'unknown' to the user
_USER_PRINT_VALUE_UNKNOWN = "unknown"
# Value to be return as 'auto' to the user
_USER_PRINT_VALUE_AUTO = "auto"

SCREEN_ON = 1
SCREEN_OFF = 2
SCREEN_TOGGLE = 3


# A decorator to ensure package exists
# Note: This decorator assumes that the decorated func gets package_name as
# the first parameter
def ensure_package_exists(func: Callable) -> Callable:
    def func_wrapper(package_name: str, *args: Any, **kwargs: Any) -> Any:
        if not _package_exists(package_name):
            print_error_and_exit(f"Package {package_name} does not exist")
        return func(package_name, *args, **kwargs)
    return func_wrapper


def _package_exists(package_name: str) -> bool:
    cmd = f"pm path {package_name}"
    result = execute_adb_shell_command3(cmd)
    return result.return_code == 0 and result.stdout is not None and len(result.stdout.strip()) != 0


def print_state_change_decorator(fun: Callable, title: str, get_state_func: Callable[[], str | bool | int]) -> Callable:
    # magic sauce to lift the name and doc of the function
    @wraps(fun)
    def ret_fun(*args: Any, **kwargs: Any) -> Any:
        # Get state before execution
        current_state = get_state_func()
        # Call the function
        returned_value = fun(*args, **kwargs)
        # Get state after execution
        # sleep before getting the new value, or we might get a stale value in some cases
        # like mobile-data on/off
        time.sleep(1)
        new_state = get_state_func()
        print_state_change_info(title, old_state=current_state, new_state=new_state)
        return returned_value
    return ret_fun


# Source:
# https://github.com/dhelleberg/android-scripts/blob/master/src/devtools.groovy
def handle_gfx(value: Literal["on", "off", "lines"]) -> None:
    if value == "on":
        cmd = "setprop debug.hwui.profile visual_bars"
    elif value == "off":
        cmd = "setprop debug.hwui.profile false"
    elif value == "lines":
        cmd = "setprop debug.hwui.profile visual_lines"
    else:
        print_error_and_exit(f"Unexpected value for gfx {value}")
        return

    _execute_adb_shell_command_and_poke_activity_service(cmd)


# Source: https://github.com/dhelleberg/android-scripts/blob/master/src/devtools.groovy
# https://plus.google.com/+AladinQ/posts/dpidzto1b8B
def handle_overdraw(value: str) -> None:
    version = get_device_android_api_version()

    if version < 19:
        if value == "on":
            cmd = "setprop debug.hwui.show_overdraw true"
        elif value == "off":
            cmd = "setprop debug.hwui.show_overdraw false"
        elif value == "deut":
            print_error_and_exit(
                f"deut mode is available only on API 19 and above, your Android API version is {version:d}")
            return
        else:
            print_error_and_exit(f"Unexpected value for overdraw {value}")
            return
    elif value == "on":
        cmd = "setprop debug.hwui.overdraw show"
    elif value == "off":
        cmd = "setprop debug.hwui.overdraw false"
    elif value == "deut":
        cmd = "setprop debug.hwui.overdraw show_deuteranomaly"
    else:
        print_error_and_exit(f"Unexpected value for overdraw {value}")
        return

    _execute_adb_shell_command_and_poke_activity_service(cmd)


# Perform screen rotation. Accepts four direction types - left, right, portrait, and landscape.
# Source:
# https://stackoverflow.com/questions/25864385/changing-android-device-orientation-with-adb
def handle_rotate(direction: str) -> None:
    disable_acceleration = "put system accelerometer_rotation 0"
    _execute_adb_shell_settings_command3(disable_acceleration)

    if direction == "portrait":
        new_direction = 0
    elif direction == "landscape":
        new_direction = 1
    elif direction == "left":
        current_direction = get_current_rotation_direction()
        print_verbose(f"Current direction: {current_direction}")
        if current_direction is None:
            return
        new_direction = (current_direction + 1) % 4
    elif direction == "right":
        current_direction = get_current_rotation_direction()
        print_verbose(f"Current direction: {current_direction}")
        if current_direction is None:
            return
        new_direction = (current_direction - 1) % 4
    else:
        print_error_and_exit(f"Unexpected direction {direction}")
        return

    cmd = f"put system user_rotation {new_direction}"
    _execute_adb_shell_settings_command3(cmd)


def get_current_rotation_direction() -> int:
    cmd = "get system user_rotation"
    direction = _execute_adb_shell_settings_command3(cmd).stdout
    print_verbose(f"Return value is {direction}")
    if not direction or direction == "null":
        return 0  # default direction is 0, vertical straight

    try:
        return int(direction)
    except ValueError as e:
        print_error(f'Failed to get direction, error: "{e}"')
        return 0


def handle_layout(*, turn_on: bool) -> None:
    cmd = "setprop debug.layout true" if turn_on else "setprop debug.layout false"
    _execute_adb_shell_command_and_poke_activity_service(cmd)


# Source: https://stackoverflow.com/questions/10506591/turning-airplane-mode-on-via-adb
def handle_airplane(*, turn_on: bool) -> str | None:
    state = 1 if turn_on else 0
    return_code, su_path, _ = execute_adb_shell_command2("which su")
    if not return_code and su_path and len(su_path):
        cmd = f"put global airplane_mode_on {state:d}"
        broadcast_change_cmd = "am broadcast -a android.intent.action.AIRPLANE_MODE"
        # This is a protected intent which would require root to run
        # https://developer.android.com/reference/android/content/Intent.html#ACTION_AIRPLANE_MODE_CHANGED
        broadcast_change_cmd = f"su root {broadcast_change_cmd}"
        _execute_adb_shell_settings_command2(cmd)
        return_code, _, _ = execute_adb_shell_command2(broadcast_change_cmd)
        if return_code != 0:
            print_error_and_exit("Failed to change airplane mode")
        return _USER_PRINT_VALUE_UNKNOWN

    return_code_wifi, output_wifi, _ = _execute_adb_shell_settings_command2("get global wifi_on")
    return_code_data, output_data, _ = _execute_adb_shell_settings_command2("get global mobile_data")

    if return_code_wifi != 0:
        print_error("Failed to get wifi state")
        return _USER_PRINT_VALUE_UNKNOWN

    if return_code_data != 0:
        print_error("Failed to get mobile-data state")
        return _USER_PRINT_VALUE_UNKNOWN

    if turn_on:
        return_code_wifi, _, _ = _execute_adb_shell_settings_command2(f"put global adbe_wifi {output_wifi}")
        return_code_data, _, _ = _execute_adb_shell_settings_command2(f"put global adbe_data {output_data}")
        return_code_airplane, _, _ = _execute_adb_shell_settings_command2("put global airplane_mode_on 1")

        if return_code_wifi != 0 or return_code_data != 0 or return_code_airplane != 0:
            print_error('Failed to put "Global" settings states. Proceeding anyway ...')

        handle_mobile_data(turn_on=False)
        set_wifi(turn_on=False)
    else:
        return_code_wifi, last_wifi_state, _ = _execute_adb_shell_settings_command2("get global adbe_wifi")
        return_code_data, last_data_state, _ = _execute_adb_shell_settings_command2("get global adbe_data")
        return_code_airplane, _, _ = _execute_adb_shell_settings_command2("put global airplane_mode_on 0")

        if return_code_wifi != 0 or return_code_data != 0:
            print_error('Failed to get "Global" settings states. Enabling mobile-data and Wifi ...')

        if return_code_airplane != 0:
            print_error("Failed to change airplane mode.")

        if last_data_state:
            handle_mobile_data(turn_on=last_data_state == "1")
        else:
            handle_mobile_data(turn_on=True)

        if last_wifi_state:
            set_wifi(turn_on=last_wifi_state == "1")
        else:
            set_wifi(turn_on=True)
    return None


def get_battery_saver_state() -> str:
    _error_if_min_version_less_than(19)
    cmd = "get global low_power"
    return_code, stdout, _ = _execute_adb_shell_settings_command2(cmd)
    if return_code != 0:
        print_error("Failed to get battery saver state")
        return _USER_PRINT_VALUE_UNKNOWN
    if stdout.strip() == "null":
        return _USER_PRINT_VALUE_OFF

    try:
        state = int(stdout.strip())
    except ValueError:
        print_error(f'Unable to get int value from "{stdout.strip()}"')
        return _USER_PRINT_VALUE_UNKNOWN
    if state == 0:
        return _USER_PRINT_VALUE_OFF
    return _USER_PRINT_VALUE_ON


# Source:
# https://stackoverflow.com/questions/28234502/programmatically-enable-disable-battery-saver-mode
@partial(print_state_change_decorator, title="Battery saver", get_state_func=get_battery_saver_state)
def handle_battery_saver(*, turn_on: bool) -> None:
    _error_if_min_version_less_than(19)
    cmd = "put global low_power 1" if turn_on else "put global low_power 0"

    if turn_on:
        return_code, _, _ = execute_adb_shell_command2(get_battery_unplug_cmd())
        if return_code != 0:
            print_error_and_exit("Failed to unplug battery")
        return_code, _, _ = execute_adb_shell_command2(get_battery_discharging_cmd())
        if return_code != 0:
            print_error_and_exit("Failed to put battery in discharge mode")

    return_code, _, _ = _execute_adb_shell_settings_command2(cmd)
    if return_code != 0:
        print_error_and_exit("Failed to modify battery saver mode")


# Source:
# https://stackoverflow.com/questions/28234502/programmatically-enable-disable-battery-saver-mode
def handle_battery_level(level: int) -> None:
    _error_if_min_version_less_than(19)
    if level < 0 or level > 100:
        print_error_and_exit(f"Battery percentage {level:d} is outside the valid range of 0 to 100")
    cmd = f"dumpsys battery set level {level:d}"

    execute_adb_shell_command3(get_battery_unplug_cmd())
    execute_adb_shell_command3(get_battery_discharging_cmd())
    execute_adb_shell_command3(cmd)


# Source:
# https://stackoverflow.com/questions/28234502/programmatically-enable-disable-battery-saver-mode
def handle_battery_reset() -> None:
    # The battery related commands fail silently on API 16. I am not sure about 17 and 18.
    _error_if_min_version_less_than(19)
    cmd = get_battery_reset_cmd()
    execute_adb_shell_command3(cmd)


# https://developer.android.com/training/monitoring-device-state/doze-standby.html
def handle_doze(*, turn_on: bool) -> None:
    _error_if_min_version_less_than(23)

    enable_idle_mode_cmd = "dumpsys deviceidle enable"
    if turn_on:
        # Source: https://stackoverflow.com/a/42440619
        cmd = "dumpsys deviceidle force-idle"
        execute_adb_shell_command3(get_battery_unplug_cmd())
        execute_adb_shell_command3(get_battery_discharging_cmd())
        execute_adb_shell_command3(enable_idle_mode_cmd)
        execute_adb_shell_command3(cmd)
    else:
        cmd = "dumpsys deviceidle unforce"
        execute_adb_shell_command3(get_battery_reset_cmd())
        execute_adb_shell_command3(enable_idle_mode_cmd)
        execute_adb_shell_command3(cmd)


# Source: https://github.com/dhelleberg/android-scripts/blob/master/src/devtools.groovy
# Ref:
# https://gitlab.com/SaberMod/pa-android-frameworks-base/commit/a53de0629f3b94472c0f160f5bbe1090b020feab
def get_update_activity_service_cmd() -> str:
    # Note: 1599295570 == ('_' << 24) | ('S' << 16) | ('P' << 8) | 'R'
    return "service call activity 1599295570"


# This command puts the battery in discharging mode (most likely this is
# Android 6.0 onwards only)
def get_battery_discharging_cmd() -> str:
    return "dumpsys battery set status 3"


def get_battery_unplug_cmd() -> str:
    return "dumpsys battery unplug"


def get_battery_reset_cmd() -> str:
    return "dumpsys battery reset"


@ensure_package_exists
def handle_get_jank(app_name: str) -> None:
    running = _is_app_running(app_name)
    if not running:
        # Jank information cannot be fetched unless the app is running
        print_verbose(f"Starting the app {app_name} to get its jank information")
        launch_app(app_name)

    try:
        cmd = f"dumpsys gfxinfo {app_name} "
        return_code, result, _ = execute_adb_shell_command2(cmd)
        print_verbose(result)
        found = False
        if return_code == 0:
            for line in result.split("\n"):
                if line.find("Janky") != -1:
                    print(line)
                    found = True
                    break
        if not found:
            print_error(f"No jank information found for {app_name}")
    finally:
        # If app was not running then kill app after getting the jank information.
        if not running:
            print_verbose(f"Stopping the app {app_name} after getting its jank information")
            force_stop(app_name)


def _is_app_running(app_name: str) -> bool:
    return_code, result, _ = execute_adb_shell_command2("ps -o NAME")
    if return_code != 0 or not result:
        return False
    result = result.strip()
    return result.find(app_name) != -1


def handle_list_devices() -> None:
    device_serials = _get_device_serials()

    if not device_serials:
        print_error_and_exit("No attached Android device found")

    for device_serial in device_serials:
        _print_device_info(device_serial)


def _get_device_serials() -> list[str]:
    cmd = "devices -l"
    result = execute_adb_command2(cmd)
    assert result.return_code == 0, f"Failed to execute command {cmd}, error: {result.stderr}"

    device_serials = []
    # Skip the first line, it says "List of devices attached"
    device_infos = result.stdout.split("\n")[1:]

    if len(device_infos) == 0 or (
            len(device_infos) == 1 and len(device_infos[0]) == 0):
        return []

    if len(device_infos) == 1:
        device_serial = device_infos[0].split(" ")[0]
        device_serials.append(device_serial)
        return device_serials

    for device_info in device_infos:
        if not device_info:
            continue
        device_serial = device_info.split()[0]
        if "unauthorized" in device_info:
            print_error(
                f'Unlock Device "{device_serial}" and give USB debugging access to '
                "this PC/Laptop by unlocking and reconnecting "
                f'the device. More info about this device: "{" ".join(device_info.split()[1:])}"\n')
        else:
            device_serials.append(device_serial)
    return device_serials


def _print_device_info(device_serial: str | None = None) -> None:
    manufacturer = get_adb_shell_property("ro.product.manufacturer", device_serial=device_serial)
    model = get_adb_shell_property("ro.product.model", device_serial=device_serial)
    # This worked on 4.4.3 API 19 Moto E
    display_name = get_adb_shell_property("ro.product.display", device_serial=device_serial)

    # First fallback: undocumented
    if ((not display_name or display_name == "null")
            and get_device_android_api_version(device_serial=device_serial) >= 19):
        # This works on 4.4.4 API 19 Galaxy Grand Prime
        display_name = _execute_adb_shell_settings_command3("get system device_name", device_serial=device_serial).stdout

    # Second fallback, documented to work on API 25 and above
    # Source: https://developer.android.com/reference/android/provider/Settings.Global.html#DEVICE_NAME
    if (not display_name or display_name == "null") and get_device_android_api_version(device_serial=device_serial) >= 25:
        display_name = _execute_adb_shell_settings_command3("get global device_name", device_serial=device_serial).stdout

    # ABI info
    abi = get_adb_shell_property("ro.product.cpu.abi", device_serial=device_serial)
    release = get_adb_shell_property("ro.build.version.release", device_serial=device_serial)
    sdk = get_adb_shell_property("ro.build.version.sdk", device_serial=device_serial)
    print_message(
        f"Serial ID: {device_serial}\nManufacturer: {manufacturer}\nModel: {model} ({display_name})\nRelease: {release}\nSDK version: {sdk}\nCPU: {abi}\n")


@dataclasses.dataclass
class _TopActivityData:
    app_name: str
    activity_name: str


def print_top_activity() -> None:
    activity_data = _get_top_activity_data()
    app_name = activity_data.app_name
    activity_name = activity_data.activity_name
    if app_name:
        print_message(f"Application name: {app_name}")
    if activity_name:
        print_message(f"Activity name: {activity_name}")


def _get_top_activity_data() -> _TopActivityData | None:
    cmd = "dumpsys window windows"
    return_code, output, _ = execute_adb_shell_command2(cmd)
    if return_code != 0 and not output:
        print_error_and_exit("Device returned no response, is it still connected?")
    for line in output.split("\n"):
        regex_result = re.search(r"ActivityRecord{.* (\S+)/(\S+)", line.strip())
        if regex_result is None:
            continue
        app_name, activity_name = regex_result.group(1), regex_result.group(2)
        # If activity name is a shorthand then complete it.
        if activity_name.startswith("."):
            activity_name = f"{app_name}{activity_name}"
        return _TopActivityData(app_name=app_name, activity_name=activity_name)

    print_error("Unable to extract activity name")
    return None


def dump_ui(xml_file: str) -> None:
    tmp_file = _create_tmp_file("dump-ui", "xml")
    cmd1 = f"uiautomator dump {tmp_file}"
    cmd2 = f"pull {tmp_file} {xml_file}"
    cmd3 = f"rm {tmp_file}"

    print_verbose(f"Writing UI to {tmp_file}")
    result = execute_adb_shell_command3(cmd1)
    assert result.return_code == 0, f"Failed to execute command {cmd1}, error: {result.stderr}"

    print_verbose(f"Pulling file {xml_file}")
    result = execute_adb_command2(cmd2)
    assert result.return_code == 0, f"Failed to execute command {cmd2}, error: {result.stderr}"
    print_verbose(f"Deleting file {tmp_file}")
    result = execute_adb_shell_command3(cmd3)
    assert result.return_code == 0, f"Failed to execute command {cmd3}, error: {result.stderr}"
    print_message(f'XML UI dumped to {xml_file}, you might want to format it using "xmllint --format {xml_file}"')


@ensure_package_exists
def force_stop(app_name: str) -> None:
    cmd = f"am force-stop {app_name}"
    return_code, stdout, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit(f'Failed to stop "{app_name}"')
    else:
        print_message(stdout)


@ensure_package_exists
def clear_disk_data(app_name: str) -> None:
    cmd = f"pm clear {app_name}"
    return_code, _, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit(f'Failed to clear data of "{app_name}"')


def get_mobile_data_state() -> str:
    # Using "adb shell dumpsys telephony.registry | ag mDataConnectionState"
    cmd = "dumpsys telephony.registry"
    return_code, stdout, _ = execute_adb_shell_command2(cmd)
    if return_code != 0 or not stdout:
        print_error("Failed to get mobile data setting")
        return _USER_PRINT_VALUE_UNKNOWN
    m = re.search(r"mDataConnectionState=(\d+)", stdout)
    if not m:
        print_error(f'Failed to get mobile data setting from "{stdout}"')
        return _USER_PRINT_VALUE_UNKNOWN
    if int(m.group(1)) == 0:
        return _USER_PRINT_VALUE_OFF
    return _USER_PRINT_VALUE_ON


# Source: https://developer.android.com/reference/android/provider/Settings.Global#WIFI_ON
def get_wifi_state() -> str:
    _error_if_min_version_less_than(17)

    return_code, stdout, _ = _execute_adb_shell_settings_command2("get global wifi_on")
    if return_code != 0:
        print_error("Failed to get global Wi-Fi setting")
        return _USER_PRINT_VALUE_UNKNOWN

    if int(stdout.strip()) == 1:
        return _USER_PRINT_VALUE_ON
    return _USER_PRINT_VALUE_OFF


@partial(print_state_change_decorator, title="Wi-Fi", get_state_func=get_wifi_state)
def set_wifi(*, turn_on: bool) -> None:
    cmd = "svc wifi enable" if turn_on else "svc wifi disable"
    return_code, _, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit("Failed to change Wi-Fi setting")


# Source:
# https://stackoverflow.com/questions/26539445/the-setmobiledataenabled-method-is-no-longer-callable-as-of-android-l-and-later
@partial(print_state_change_decorator, title="Mobile data", get_state_func=get_mobile_data_state)
def handle_mobile_data(*, turn_on: bool) -> None:
    cmd = "svc data enable" if turn_on else "svc data disable"
    return_code, _, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit("Failed to change mobile data setting")


def force_rtl(*, turn_on: bool) -> None:
    _error_if_min_version_less_than(19)
    cmd = "put global debug.force_rtl 1" if turn_on else "put global debug.force_rtl 0"
    _execute_adb_shell_settings_command_and_poke_activity_service(cmd)


def dump_screenshot(filepath: str) -> None:
    screenshot_file_path_on_device = _create_tmp_file("screenshot", "png")
    dump_cmd = f"screencap -p {screenshot_file_path_on_device} "
    result = execute_adb_shell_command3(dump_cmd)
    assert result.return_code == 0, f"Failed to capture screenshot, error: {result.stderr}"
    pull_cmd = f"pull {screenshot_file_path_on_device} {filepath}"
    result = execute_adb_command2(pull_cmd)
    assert result.return_code == 0, f"Failed to pull screenshot file, error: {result.stderr}"
    del_cmd = f"rm {screenshot_file_path_on_device}"
    result = execute_adb_shell_command3(del_cmd)
    assert result.return_code == 0, f"Failed to delete screenshot file from device, error: {result.stderr}"


def dump_screenrecord(filepath: str) -> None:
    _error_if_min_version_less_than(19)
    api_version = get_device_android_api_version()

    # I have tested that on API 23 and above this works. Till Api 22, on emulator, it does not.
    if api_version < 23 and _is_emulator():
        print_error_and_exit("screenrecord is not supported on emulator below API 23\n"
                             "Source: https://issuetracker.google.com/issues/36982354")

    original_sigint_handler = None

    def _start_recording(screen_record_file_path: str) -> None:
        print_message("Recording video, press Ctrl+C to end...")
        dump_cmd = f"screenrecord --verbose {screen_record_file_path} "
        execute_adb_shell_command3(dump_cmd)

    def _pull_and_delete_file_from_device(screen_record_file_path: str) -> None:
        print_message(f"Saving recording to {filepath}")
        pull_cmd = f"pull {screen_record_file_path} {filepath}"
        execute_adb_command2(pull_cmd)
        del_cmd = f"rm {screen_record_file_path}"
        execute_adb_shell_command3(del_cmd)

    def _kill_all_child_processes() -> None:
        current_process = psutil.Process()
        children = current_process.children(recursive=True)
        for child in children:
            print_verbose(f"Child process is {child}")
            os.kill(child.pid, signal.SIGTERM)

    def _handle_recording_ended(screen_record_file_path: str) -> None:
        print_message("Finishing...")
        # Kill all child processes.
        # This is not neat, but it is OK for now since we know that we have only one adb child process which is
        # running screen recording.
        _kill_all_child_processes()
        # Wait for one second.
        time.sleep(1)
        # Finish rest of the processing.
        _pull_and_delete_file_from_device(screen_record_file_path)
        # And exit
        sys.exit(0)

    def signal_handler(_sig: int, _frame: Any) -> None:
        # Restore the original handler for Ctrl-C
        signal.signal(signal.SIGINT, original_sigint_handler)
        _handle_recording_ended(screen_record_file_path_on_device)

    original_sigint_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, signal_handler)

    screen_record_file_path_on_device = _create_tmp_file("screenrecord", "mp4")
    _start_recording(screen_record_file_path_on_device)


def get_mobile_data_saver_state() -> str:
    cmd = "cmd netpolicy get restrict-background"
    return_code, stdout, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error("Failed to get mobile data saver mode setting")
        return _USER_PRINT_VALUE_UNKNOWN
    enabled = stdout.strip().find("enabled") != -1
    if enabled:
        return _USER_PRINT_VALUE_ON
    return _USER_PRINT_VALUE_OFF


# https://developer.android.com/training/basics/network-ops/data-saver.html
@partial(print_state_change_decorator, title="Mobile data saver", get_state_func=get_mobile_data_saver_state)
def handle_mobile_data_saver(*, turn_on: bool) -> None:
    cmd = "cmd netpolicy set restrict-background true" if turn_on else "cmd netpolicy set restrict-background false"
    return_code, _, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit("Failed to modify data saver mode setting")


def get_dont_keep_activities_in_background_state() -> str:
    cmd = "get global always_finish_activities"
    return_code, stdout, _ = _execute_adb_shell_settings_command2(cmd)
    if return_code != 0:
        print_error("Failed to get don't keep activities in the background setting")
        return _USER_PRINT_VALUE_UNKNOWN

    if stdout is None or stdout.strip() == "null":
        return _USER_PRINT_VALUE_OFF

    enabled = int(stdout.strip()) != 0
    if enabled:
        return _USER_PRINT_VALUE_ON
    return _USER_PRINT_VALUE_OFF


# Ref: https://github.com/android/platform_packages_apps_settings/blob/4ce19f5c4fd40f3bedc41d3fbcbdede8b2614501/src/com/android/settings/DevelopmentSettings.java#L2123
# adb shell settings put global always_finish_activities true might not work on all Android versions.
# It was in system (not global before ICS)
# adb shell service call activity 43 i32 1 followed by that
@partial(print_state_change_decorator,
         title="Don't keep activities",
         get_state_func=get_dont_keep_activities_in_background_state)
def handle_dont_keep_activities_in_background(*, turn_on: bool) -> None:
    # Till Api 25, the value was True/False, above API 25, 1/0 work. Source: manual testing
    use_true_false_as_value = get_device_android_api_version() <= 25

    if turn_on:
        value = "true" if use_true_false_as_value else "1"
        cmd1 = f"put global always_finish_activities {value}"
        cmd2 = "service call activity 43 i32 1"
    else:
        value = "false" if use_true_false_as_value else "0"
        cmd1 = f"put global always_finish_activities {value}"
        cmd2 = "service call activity 43 i32 0"
    _execute_adb_shell_settings_command3(cmd1)
    _execute_adb_shell_command_and_poke_activity_service(cmd2)


def toggle_animations(*, turn_on: bool) -> None:
    value = 1 if turn_on else 0

    # Source: https://github.com/jaredsburrows/android-gif-example/blob/824c493285a2a2cf22f085662431cf0a7aa204b8/.travis.yml#L34
    cmd1 = f"put global window_animation_scale {value:d}"
    cmd2 = f"put global transition_animation_scale {value:d}"
    cmd3 = f"put global animator_duration_scale {value:d}"

    _execute_adb_shell_settings_command3(cmd1)
    _execute_adb_shell_settings_command3(cmd2)
    _execute_adb_shell_settings_command3(cmd3)


def get_show_taps_state() -> str:
    cmd = "get system show_touches"
    return_code, stdout, _ = _execute_adb_shell_settings_command2(cmd)
    if return_code != 0:
        print_error('Failed to get current state of "show user taps" setting')
        return _USER_PRINT_VALUE_UNKNOWN

    stdout = stdout.strip()
    if stdout == "null":
        return _USER_PRINT_VALUE_OFF
    if int(stdout) == 1:
        return _USER_PRINT_VALUE_ON
    return _USER_PRINT_VALUE_OFF


@partial(print_state_change_decorator, title="Show user taps", get_state_func=get_show_taps_state)
def toggle_show_taps(*, turn_on: bool) -> None:
    value = 1 if turn_on else 0

    # Source: https://stackoverflow.com/a/32621809/434196
    cmd = f"put system show_touches {value:d}"
    _execute_adb_shell_settings_command3(cmd)


def get_stay_awake_while_charging_state() -> str:
    cmd = "get global stay_on_while_plugged_in"
    return_code, stdout, _ = _execute_adb_shell_settings_command2(cmd)
    if return_code != 0:
        print_error('Failed to get "stay awake while plugged in" in the background setting')
        return _USER_PRINT_VALUE_UNKNOWN
    value = int(stdout.strip())
    if value == 0:
        return _USER_PRINT_VALUE_OFF
    if value == 7:
        return _USER_PRINT_VALUE_ON
    return _USER_PRINT_VALUE_PARTIALLY_ON


# Source: https://developer.android.com/reference/android/provider/Settings.Global.html#STAY_ON_WHILE_PLUGGED_IN
@partial(print_state_change_decorator,
         title="Stay awake while charging",
         get_state_func=get_stay_awake_while_charging_state)
def stay_awake_while_charging(*, turn_on: bool) -> None:
    # 1 for USB charging, 2 for AC charging, 4 for wireless charging. Add them together to get 7.
    value = 7 if turn_on else 0
    cmd = f"put global stay_on_while_plugged_in {value:d}"
    _execute_adb_shell_settings_command_and_poke_activity_service(cmd)


def input_text(text: str) -> None:
    # Replace whitespaces to %s which gets translated by Android back to whitespaces.
    cmd = "input text {}".format(text.replace(" ", "%s"))
    return_code, _, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit(f'Failed to input text "{text}"')


# https://developer.android.com/reference/android/view/KeyEvent#KEYCODE_BACK
def press_back() -> None:
    press_key("KEYCODE_BACK")


# Ref: https://developer.android.com/reference/android/view/KeyEvent#KEYCODE_MEDIA_NEXT
def press_media_next() -> None:
    press_key("KEYCODE_MEDIA_NEXT")


def press_key(keycode: str | int) -> None:
    cmd = f"input keyevent {keycode}"
    return_code, _, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit(f"Failed to press {keycode}")


def open_url(url: str) -> None:
    # Let's not do any URL encoding for now, if required, we will add that in the future.
    parsed_url = urlparse(url=url)
    if not parsed_url.scheme:
        parsed_url2 = urlparse(url=url, scheme="http")
        url = parsed_url2.geturl()
    cmd = f"am start -a android.intent.action.VIEW -d {url}"
    return_code, _, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit(f'Failed to open url "{url}"')


def list_permission_groups() -> None:
    cmd = "pm list permission-groups"
    return_code, stdout, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit("Failed to list permission groups")
    else:
        print_message(stdout)


def list_permissions(*, dangerous_only_permissions: bool) -> None:
    # -g is to group permissions by permission groups.
    cmd = "pm list permissions -g -d" if dangerous_only_permissions else "pm list permissions -g"
    return_code, stdout, stderr = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit(f"Failed to list permissions: (stdout: {stdout}, stderr: {stderr})")
    else:
        print_message(stdout)


# Creates a tmp file on Android device
def _create_tmp_file(filename_prefix: str | None = None, filename_suffix: str | None = None) -> str | None:
    if filename_prefix is None:
        filename_prefix = "file"
    if filename_suffix is None:
        filename_suffix = "tmp"
    if filename_prefix.find("/") != -1:
        print_error_and_exit(f'Filename prefix "{filename_prefix}" contains illegal character: "/"')
    if filename_suffix.find("/") != -1:
        print_error_and_exit(f'Filename suffix "{filename_suffix}" contains illegal character: "/"')

    tmp_dir = "/data/local/tmp"

    filepath_on_device = (
        f"{tmp_dir}/{filename_prefix}-{secrets.randbelow(1000 * 1000 * 1000):d}.{filename_suffix}")
    if _file_exists(filepath_on_device):
        # Retry if the file already exists
        print_verbose(f"Tmp File {filepath_on_device} already exists, trying a new random name")
        return _create_tmp_file(filename_prefix, filename_suffix)

    # Create the file
    return_code, stdout, stderr = execute_adb_shell_command2(f"touch {filepath_on_device}")
    if return_code != 0:
        print_error(f"Failed to create tmp file {filepath_on_device}: (stdout: {stdout}, stderr: {stderr})")
        return None

    # Make the tmp file world-writable or else, run-as command might fail to write on it.
    return_code, stdout, stderr = execute_adb_shell_command2(f"chmod 666 {filepath_on_device}")
    if return_code != 0:
        print_error(f"Failed to chmod tmp file {filepath_on_device}: (stdout: {stdout}, stderr: {stderr})")
        return None

    return filepath_on_device


# Returns true if the file_path exists on the device, false if it does not exists or is inaccessible.
def _file_exists(file_path: str) -> bool:
    exists_cmd = f'"ls {file_path} 1>/dev/null 2>/dev/null && echo exists"'
    stdout = execute_file_related_adb_shell_command(exists_cmd, file_path)
    return stdout is not None and stdout.find("exists") != -1


def _is_sqlite_database(file_path: str) -> bool:
    return file_path.endswith(".db")


# Returns a fully-qualified permission group name.
def get_permission_group(args: dict[str, Any]) -> str | None:
    result_map = {
        "contacts": "android.permission-group.CONTACTS",
        "phone": "android.permission-group.PHONE",
        "calendar": "android.permission-group.CALENDAR",
        "camera": "android.permission-group.CAMERA",
        "sensors": "android.permission-group.SENSORS",
        "location": "android.permission-group.LOCATION",
        "storage": "android.permission-group.STORAGE",
        "microphone": "android.permission-group.MICROPHONE",
        "notifications": "android.special-permission-group.NOTIFICATIONS",
        "sms": "android.permission-group.SMS",
    }

    for key, value in result_map.items():
        if args[key]:
            return value

    print_error_and_exit(f"Unexpected permission group: {args}")
    return None


# Android keeps emptying these groups so that granted permissions are denied
# but the expectation of this tool is to do the right mapping
def _get_hardcoded_permissions_for_group(permission_group: str) -> list[str]:
    result_map = {
        "android.permission-group.CONTACTS": [
            "android.permission.READ_CONTACTS",
            "android.permission.WRITE_CONTACTS",
        ],
        "android.permission-group.PHONE": [
            "android.permission.READ_PHONE_STATE",
            "android.permission.READ_PHONE_NUMBERS",
            "android.permission.CALL_PHONE",
            "android.permission.ANSWER_PHONE_CALLS",
        ],
        "android.permission-group.CALENDAR": [
            "android.permission.READ_CALENDAR",
            "android.permission.WRITE_CALENDAR",
        ],
        "android.permission-group.CAMERA": [
            "android.permission.CAMERA",
        ],
        "android.permission-group.SENSORS": [
            "android.permission.BODY_SENSORS",
        ],
        "android.permission-group.LOCATION": [
            "android.permission.ACCESS_FINE_LOCATION",
            "android.permission.ACCESS_COARSE_LOCATION",
        ],
        "android.permission-group.STORAGE": [
            "android.permission.READ_EXTERNAL_STORAGE",
            "android.permission.WRITE_EXTERNAL_STORAGE",
        ],
        "android.permission-group.MICROPHONE": [
            "android.permission.RECORD_AUDIO",
        ],
        "android.special-permission-group.NOTIFICATIONS": [
            "android.permission.POST_NOTIFICATIONS",
        ],
        "android.permission-group.SMS": [
            "android.permission.READ_SMS",
            "android.permission.RECEIVE_SMS",
            "android.permission.SEND_SMS",
        ],
    }

    result = result_map.get(permission_group, [])
    if not result:
        print_error(f"Unexpected permission group: {permission_group}")

    return result


# Pass the full-qualified permission group name to this method.
def get_permissions_in_permission_group(permission_group: str) -> list[str] | list | None:
    # List permissions by group
    cmd = "pm list permissions -g"
    return_code, stdout, stderr = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit(f"Failed to run command {cmd} (stdout: {stdout}, stderr: {stderr})")
        return None

    permission_output = stdout
    # Remove ungrouped permissions section completely.
    if "ungrouped:" in permission_output:
        permission_output, _ = permission_output.split("ungrouped:")
    splits = permission_output.split("group:")
    for split in splits:
        if split.startswith(permission_group):
            potential_permissions = split.split("\n")
            # Ignore the first entry which is the group name
            potential_permissions = potential_permissions[1:]
            # Filter out empty lines.
            permissions = filter(
                lambda x: len(
                    x.strip()) > 0,
                potential_permissions)
            permissions = [x.replace("permission:", "") for x in permissions]
            permissions = list(set(permissions + _get_hardcoded_permissions_for_group(permission_group)))
            print_message(
                f"Permissions in {permission_group} group are {permissions}")
            return permissions
    return _get_hardcoded_permissions_for_group(permission_group)


@ensure_package_exists
def grant_or_revoke_runtime_permissions(package_name: str, action_type: Literal["grant", "revoke"], permissions: list[str]) -> None:
    _error_if_min_version_less_than(23)

    app_info_dump = execute_adb_shell_command3(f"dumpsys package {package_name}").stdout
    permissions_formatted_dump = _get_permissions_info_above_api_23(app_info_dump).split("\n")

    if action_type == "grant":
        base_cmd = f"pm grant {package_name}"
    elif action_type == "revoke":
        base_cmd = f"pm revoke {package_name}"
    else:
        print_error_and_exit(f"Invalid action type: {action_type}")
        return

    num_permissions_granted = 0
    for permission in permissions:
        if permission not in permissions_formatted_dump:
            print_message(f"Permission {permission} is not requested by {package_name}, skipping")
            continue
        if permission == "android.permission.POST_NOTIFICATIONS":
            _error_if_min_version_less_than(33)
        num_permissions_granted += 1
        print_message(f"{action_type} {permission} permission to {package_name}")
        execute_adb_shell_command3(base_cmd + " " + permission)
    if num_permissions_granted == 0:
        print_error_and_exit(f"None of these permissions were granted to {package_name}: {permissions}")


def _get_all_packages(pm_cmd: str) -> list:
    return_code, result, _ = execute_adb_shell_command2(pm_cmd)
    if return_code != 0:
        print_error_and_exit(f'Command "{pm_cmd}" failed, something is wrong')
    packages = []
    if result:
        for line in result.split("\n"):
            _, package_name = line.split(":", 2)
            packages.append(package_name)
    return packages


# "dumpsys package" is more accurate than "pm list packages" but that means the results of
# list_all_apps are now different from list_system_apps, print_list_non_system_apps, and
# list_debug_apps
# For now, we can live with this discrepancy but in the longer run we want to fix those
# other functions as well
# https://stackoverflow.com/questions/63416599/adb-shell-pm-list-packages-missing-some-packages
def get_list_all_apps() -> tuple | tuple[None, str, bytes | str]:
    """This function return a list of installed applications, error message and command
    execution error
    :returns: tuple(all_apps, err_msg, error)
        WHERE
        list[str] all_apps is a string list of all installed packages
        str err_msg is the error message to display
        str error is the command execution error message
    :Example:
    >>> import adbe.adb_enhanced as adb_e
    >>> import adbe.adb_helper as adb_h
    >>> adb_h.set_device_id("emulator-5554")
    >>> list_apps, err_msg, err = adb_e.get_list_all_apps()
    """
    # https://developer.android.com/studio/command-line/dumpsys
    cmd = "dumpsys package"
    pattern_packages = re.compile(r"Package \[(.*?)]")
    return_code, result, err = execute_adb_shell_command2(cmd)
    if return_code != 0:
        err_msg = f'Command "{cmd}" failed, something is wrong'
        return None, err_msg, err
    all_apps = re.findall(pattern_packages, result)
    # Get the unique results
    all_apps = sorted(dict.fromkeys(all_apps))
    return all_apps, None, None


def print_list_all_apps() -> None:
    """This function print list of all installed packages or error message if an error
    occurred
    :returns: None
    """
    all_apps, err_msg, err = get_list_all_apps()
    if err:
        print_error_and_exit(err_msg)
        return
    print_message("\n".join(all_apps))


def get_list_system_apps() -> list:
    """This function return a list of installed system applications
    :returns: system_apps_packages
        WHERE
        list[str] system_apps_packages is a strings list of installed system packages
    :Example:
    >>> import adbe.adb_enhanced as adb_e
    >>> import adbe.adb_helper as adb_h
    >>> adb_h.set_device_id("DEVICE_ID")
    >>> list_sys_apps = adb_e.get_list_system_apps()
    """
    cmd = "pm list packages -s"
    return _get_all_packages(cmd)


def list_system_apps() -> None:
    """This function print list of installed system packages
    :returns: None
    """
    packages = get_list_system_apps()
    print("\n".join(packages))


def get_list_non_system_apps() -> list:
    """Return a list of installed third party applications.
    :returns: third_party_pkgs
        WHERE
        list[str] third_party_pkgs is a strings list of installed third party packages
    :Example:
    >>> import adbe.adb_enhanced as adb_e
    >>> import adbe.adb_helper as adb_h
    >>> adb_h.set_device_id("DEVICE_ID")
    >>> list_sys_apps = adb_e.get_list_non_system_apps()
    """
    cmd = "pm list packages -3"
    return _get_all_packages(cmd)


def print_list_non_system_apps() -> None:
    """Print list of installed third party packages.
    :returns: None
    """
    print("\n".join(get_list_non_system_apps()))


def get_list_debug_apps() -> list:
    """Return a list of installed debug applications.
    :returns: debug_packages
        WHERE
        list[str] debug_packages is a strings list of debuggable packages
    :Example:
    >>> import adbe.adb_enhanced as adb_e
    >>> import adbe.adb_helper as adb_h
    >>> adb_h.set_device_id("DEVICE_ID")
    >>> list_debug_apps = adb_e.get_list_debug_apps()
    """
    cmd = "pm list packages"
    packages = _get_all_packages(cmd)
    debug_packages = []

    method_to_call = _is_debug_package
    params_list = packages
    result_list = asyncio_helper.execute_in_parallel(method_to_call, params_list)

    for (package_name, debuggable) in result_list:
        if debuggable:
            debug_packages.append(package_name)
    return debug_packages


def print_list_debug_apps() -> None:
    """Print installed applications that have debug enabled.
        :returns: None
        :Example:
        >>> import adbe.adb_enhanced as adb_e
        >>> import adbe.adb_helper as adb_h
        >>> adb_h.set_device_id("DEVICE_ID")
        >>> list_debug_apps = adb_e.adb_print_list_debug_apps()
    """
    print("\n".join(get_list_debug_apps()))


def _is_debug_package(app_name: str) -> tuple[str | None, bool]:
    """Return true if the application have the debug flag set to true else return false
        :returns: None
            WHERE
            str app_name is a string of the package name
    """
    return _package_contains_flag(app_name, _REGEX_DEBUGGABLE)


def list_allow_backup_apps() -> list:
    """Return list of applications that can be backed up (flag backup set to true)
        :returns: list[str] packages that have backup flag set to true
        :Example:
        >>> import adbe.adb_enhanced as adb_e
        >>> import adbe.adb_helper as adb_h
        >>> adb_h.set_device_id("DEVICE_ID")
        >>> adb_e.list_allow_backup_apps()
    """
    cmd = "pm list packages"
    packages = _get_all_packages(cmd)

    method_to_call = _is_allow_backup_package
    params_list = packages
    result_list = asyncio_helper.execute_in_parallel(method_to_call, params_list)
    debug_packages = []
    for (package_name, debuggable) in result_list:
        if debuggable:
            debug_packages.append(package_name)
    return debug_packages


def print_allow_backup_apps() -> None:
    """Print list of applications that can be backed up (flag backup set to true)
        :returns: None
        :Example:
        >>> import adbe.adb_enhanced as adb_e
        >>> import adbe.adb_helper as adb_h
        >>> adb_h.set_device_id("DEVICE_ID")
        >>> adb_e.print_allow_backup_apps()
    """
    print("\n".join(list_allow_backup_apps()))


def _is_allow_backup_package(app_name: str) -> tuple[str | None, bool]:
    return _package_contains_flag(app_name, _REGEX_BACKUP_ALLOWED)


def _package_contains_flag(app_name: str, flag_regex: str) -> tuple[str | None, bool]:
    pm_cmd = f"dumpsys package {app_name}"
    grep_cmd = f"(grep -c -E '{flag_regex}' || true)"
    app_info_dump = execute_adb_shell_command3(pm_cmd, piped_into_cmd=grep_cmd).stdout
    if app_info_dump is None or app_info_dump.strip() == "0":
        return app_name, False
    try:
        val = int(app_info_dump.strip())
        if val > 0:
            return app_name, True
        return None, False
    except ValueError:
        print_error_and_exit(f'Unexpected output for {pm_cmd} | {grep_cmd} = "{app_info_dump}"')
        return None, False


# Source: https://developer.android.com/reference/android/app/usage/UsageStatsManager#STANDBY_BUCKET_ACTIVE
_APP_STANDBY_BUCKETS = {
    10: "active",
    20: "working",
    30: "frequent",
    40: "rare",
}


# Source: https://developer.android.com/preview/features/power#buckets
@ensure_package_exists
def get_standby_bucket(package_name: str) -> None:
    _error_if_min_version_less_than(28)
    cmd = f"am get-standby-bucket {package_name}"
    result = execute_adb_shell_command3(cmd).stdout
    if result is None:
        print_error_and_exit(_USER_PRINT_VALUE_UNKNOWN)
    print_verbose(f'App standby bucket for "{package_name}" is {_APP_STANDBY_BUCKETS.get(int(result), _USER_PRINT_VALUE_UNKNOWN)}')
    print(_APP_STANDBY_BUCKETS.get(int(result), _USER_PRINT_VALUE_UNKNOWN))


@ensure_package_exists
def set_standby_bucket(package_name: str, mode: str) -> None:
    _error_if_min_version_less_than(28)
    cmd = f"am set-standby-bucket {package_name} {mode}"
    result = execute_adb_shell_command3(cmd).stdout
    if result is not None:  # Expected
        print_error_and_exit(result)


def calculate_standby_mode(args: dict[str, Any]) -> str:
    if args["active"]:
        return "active"
    if args["working_set"]:
        return "working_set"
    if args["frequent"]:
        return "frequent"
    if args["rare"]:
        return "rare"

    raise ValueError(f"Illegal argument: {args}")


# Source: https://developer.android.com/preview/features/power
@ensure_package_exists
def apply_or_remove_background_restriction(package_name: str, *, set_restriction: bool) -> None:
    _error_if_min_version_less_than(28)
    appops_cmd = f"cmd appops set {package_name} RUN_ANY_IN_BACKGROUND {'ignore' if set_restriction else 'allow'}"
    execute_adb_shell_command3(appops_cmd)


def list_directory(file_path: str, *, long_format: bool, recursive: bool, include_hidden_files: bool) -> None:
    cmd_prefix = "ls"
    if long_format:
        cmd_prefix += " -l"
    if recursive:
        cmd_prefix += " -R"
    if include_hidden_files:
        cmd_prefix += " -a"
    cmd = f'{cmd_prefix} "{file_path}"'
    print_message(execute_file_related_adb_shell_command(cmd, file_path))


def delete_file(file_path: str, *, force: bool, recursive: bool) -> None:
    cmd_prefix = "rm"
    if force:
        cmd_prefix += " -f"
    if recursive:
        cmd_prefix += " -r"
    cmd = f"{cmd_prefix} {file_path}"
    print_message(execute_file_related_adb_shell_command(cmd, file_path))


# Limitation: This command will only do run-as for the src file so, if a file is being copied from pkg1 to pkg2
# on a non-rooted device with both pkg1 and pkg2 being debuggable, this will fail. This can be improved by
# first copying the file to /data/local/tmp but as of now, I don't think that's required.
def move_file(src_path: str, dest_path: str, *, force: bool) -> None:
    cmd_prefix = "mv"
    if force:
        cmd_prefix += "-f"
    cmd = f"{cmd_prefix} {src_path} {dest_path}"
    if get_package(src_path) and get_package(dest_path) and get_package(src_path) != get_package(dest_path):
        print_error_and_exit("Cannot copy a file from one package into another, copy it via /data/local/tmp instead")
        return

    file_path = None
    if get_package(src_path):
        file_path = src_path
    elif get_package(dest_path):
        file_path = dest_path
    move_stdout = execute_file_related_adb_shell_command(cmd, file_path)
    if move_stdout:
        print_message(move_stdout)
    print_verbose(f'Moved "{src_path}" to "{dest_path}"')


# Copies from remote_file_path on Android to local_file_path on the disk
# local_file_path can be None
def pull_file(remote_file_path: str, local_file_path: str, *, copy_ancillary: bool = False) -> None:
    if not _file_exists(remote_file_path):
        print_error_and_exit(f"File {remote_file_path} does not exist")

    if local_file_path is None:
        local_file_path = remote_file_path.split("/")[-1]
        print_verbose(f'Local file path not provided, using "{local_file_path}" for that')

    remote_file_path_package = get_package(remote_file_path)
    if remote_file_path_package is None and not root_required_to_access_file(remote_file_path):
        print_verbose(f"File {remote_file_path_package} is not inside a package, no temporary file required")
        pull_cmd = f"pull {remote_file_path} {local_file_path}"
        execute_adb_command2(pull_cmd)
    else:
        # First copy the files to sdcard, then pull them out, and then delete them from sdcard.
        tmp_file = _create_tmp_file()
        cp_cmd = f"cp -r {remote_file_path} {tmp_file}"
        execute_file_related_adb_shell_command(cp_cmd, remote_file_path)
        pull_cmd = f"pull {tmp_file} {local_file_path}"
        execute_adb_command2(pull_cmd)
        del_cmd = f"rm -r {tmp_file}"
        execute_adb_shell_command3(del_cmd)

    if Path(local_file_path).exists():
        print_message(
            f'Copied remote file "{remote_file_path}" to local file "{local_file_path}"'
            f' (Size: {Path(local_file_path).stat().st_size:d} bytes)')
    else:
        print_error_and_exit(f'Failed to copy remote file "{remote_file_path}" to local file "{local_file_path}"')

    if _is_sqlite_database(remote_file_path):
        # Copy temporary Sqlite files
        # Source :https://ashishb.net/all/android-the-right-way-to-pull-sqlite-database-from-the-device/
        for suffix in ["wal", "journal", "shm"]:
            tmp_db_file = f"{remote_file_path}-{suffix}"
            if not _file_exists(tmp_db_file):
                continue
            if copy_ancillary:
                pull_file(tmp_db_file, f"{local_file_path}-{suffix}", copy_ancillary=True)
            else:
                print_error(f'File "{remote_file_path}" has an ancillary file "{tmp_db_file}" which should be copied.\n'
                            'See "https://ashishb.net/all/android-the-right-way-to-pull-sqlite-database-from-the-device/'
                            "for details")


# Limitation: It seems that pushing to a directory on some versions of Android fail silently.
# It is safer to push to a full path containing the filename.
def push_file(local_file_path: str, remote_file_path: str) -> None:
    if not Path(local_file_path).exists():
        print_error_and_exit(f"Local file {local_file_path} does not exist")
    if Path(local_file_path).is_dir():
        print_error_and_exit(f"This tool does not support pushing a directory yet: {local_file_path}")

    # First push to tmp file in /data/local/tmp and then move that
    tmp_file = _create_tmp_file()
    push_cmd = f"push {local_file_path} {tmp_file}"
    # "mv" from /data/local/tmp with run-as <app_id> does not always work even when the underlying
    # dir has mode set to 777. Therefore, do a two-step cp and rm.
    cp_cmd = f"cp {tmp_file} {remote_file_path}"
    rm_cmd = f"rm {tmp_file}"

    result = execute_adb_command2(push_cmd)
    if result.return_code != 0:
        print_error_and_exit(f"Failed to push file, error: {result.stderr}")
        return

    execute_file_related_adb_shell_command(cp_cmd, remote_file_path)
    execute_adb_shell_command3(rm_cmd)


def cat_file(file_path: str) -> None:
    cmd_prefix = "cat"
    cmd = f"{cmd_prefix} {file_path}"
    cat_stdout = execute_file_related_adb_shell_command(cmd, file_path)
    # Don't print "None" for an empty file
    if cat_stdout:
        print_message(execute_file_related_adb_shell_command(cmd, file_path))


# Source: https://stackoverflow.com/a/25398877
@ensure_package_exists
def launch_app(app_name: str) -> None:
    # `--pct-syskeys 0` is needed on devices without physical keys.
    # See https://github.com/ARM-software/lisa/pull/408 for details.
    adb_shell_cmd = f"monkey --pct-syskeys 0 -p {app_name} -c android.intent.category.LAUNCHER 1"
    execute_adb_shell_command3(adb_shell_cmd)


@ensure_package_exists
def stop_app(app_name: str) -> None:
    # Below API 21, stop does not kill app in the foreground.
    # Above API 21, it seems it does.
    if get_device_android_api_version() < 21:
        force_stop(app_name)
    else:
        adb_shell_cmd = f"am kill {app_name}"
        execute_adb_shell_command3(adb_shell_cmd)


def _regex_extract(regex: str, data: str) -> str | None:
    regex_object = re.search(regex, data, re.IGNORECASE)
    if regex_object:
        return regex_object.group(1)
    return None


# adb shell pm dump <app_name> produces about 1200 lines, mostly useless,
# compared to this.
@ensure_package_exists
def print_app_info(app_name: str) -> None:
    app_info_dump = execute_adb_shell_command3(f"dumpsys package {app_name}").stdout
    version_code = _regex_extract("versionCode=(\\d+)?", app_info_dump)
    version_name = _regex_extract("versionName=([\\d.]+)?", app_info_dump)
    min_sdk_version = _regex_extract("minSdk=(\\d+)?", app_info_dump)
    target_sdk_version = _regex_extract("targetSdk=(\\d+)?", app_info_dump)
    max_sdk_version = _regex_extract("maxSdk=(\\d+)?", app_info_dump)
    installer_package_name = _regex_extract("installerPackageName=(\\S+)?", app_info_dump)
    is_debuggable = re.search(
        _REGEX_DEBUGGABLE,
        app_info_dump,
        re.IGNORECASE) is not None

    msg = ""
    msg += f"App name: {app_name}\n"
    msg += f"Version: {version_name}\n"
    msg += f"Version Code: {version_code}\n"
    msg += f"Is debuggable: {is_debuggable!r}\n"
    msg += f"Min SDK version: {min_sdk_version}\n"
    msg += f"Target SDK version: {target_sdk_version}\n"
    if max_sdk_version is not None:
        msg += f"Max SDK version: {max_sdk_version}\n"

    if get_device_android_api_version() >= 23:
        msg += _get_permissions_info_above_api_23(app_info_dump)
    else:
        msg += _get_permissions_info_below_api_23(app_info_dump)

    msg += f"Installer package name: {installer_package_name}\n"
    print_message(msg)


# API < 23 have no runtime permissions
def _get_permissions_info_below_api_23(app_info_dump: str) -> str:
    install_time_permissions_regex = re.search(r"grantedPermissions:(.*)", app_info_dump,
                                               re.IGNORECASE | re.DOTALL)
    install_time_permissions_string = [] if install_time_permissions_regex is None else install_time_permissions_regex.group(1).split("\n")

    install_time_permissions_string = filter(None, install_time_permissions_string)
    install_time_granted_permissions = list(install_time_permissions_string)

    permissions_info_msg = ""
    if install_time_granted_permissions:
        permissions_info_msg += "Install time granted permissions:\n{}\n\n".format("\n".join(
            install_time_granted_permissions))
    return permissions_info_msg


# API 23 and have runtime permissions
def _get_permissions_info_above_api_23(app_info_dump: str) -> str:
    requested_permissions = _extract_requested_permissions_above_api_23(app_info_dump)

    install_time_permissions_string = _extract_install_time_permissions_above_api_23(app_info_dump)
    install_time_denied_permissions, install_time_granted_permissions = \
        _get_install_time_granted_denied_permissions(install_time_permissions_string)

    runtime_denied_permissions = []
    runtime_granted_permissions = []
    for permission in requested_permissions:
        if permission in install_time_granted_permissions:
            continue
        if permission in install_time_denied_permissions:
            continue
        granted_pattern = f"{permission}: granted=true"
        denied_pattern = f"{permission}: granted=false"
        if app_info_dump.find(granted_pattern) >= 0:
            runtime_granted_permissions.append(permission)
        elif app_info_dump.find(denied_pattern) >= 0:
            runtime_denied_permissions.append(permission)
    runtime_not_granted_permissions = list(filter(
        lambda p: p not in runtime_granted_permissions
        and p not in runtime_denied_permissions
        and p not in install_time_granted_permissions
        and p not in install_time_denied_permissions, requested_permissions))

    permissions_info_msg = ""
    permissions_info_msg += "\nPermissions:\n\n"
    if install_time_granted_permissions:
        permissions_info_msg += "Install time granted permissions:\n{}\n\n".format("\n".join(
            install_time_granted_permissions))
    if install_time_denied_permissions:
        permissions_info_msg += "Install time denied permissions:\n{}\n\n".format("\n".join(
            install_time_denied_permissions))
    if runtime_granted_permissions:
        permissions_info_msg += "Runtime granted permissions:\n{}\n\n".format("\n".join(
            runtime_granted_permissions))
    if runtime_denied_permissions:
        permissions_info_msg += "Runtime denied permissions:\n{}\n\n".format("\n".join(
            runtime_denied_permissions))
    if runtime_not_granted_permissions:
        permissions_info_msg += "Runtime Permissions not granted and not yet requested:\n{}\n\n".format("\n".join(
            runtime_not_granted_permissions))
    return permissions_info_msg


def _get_install_time_granted_denied_permissions(
        install_time_permissions_string: list[str]) -> tuple[list[str], list[str]]:
    granted_permissions = []
    # This will most likely remain empty
    denied_permissions = []
    for permission_string in install_time_permissions_string:
        if permission_string.find("granted=true") >= 0:
            permission, _ = permission_string.split(":")
            granted_permissions.append(permission)
        elif permission_string.find("granted=false") >= 0:
            permission, _ = permission_string.split(":")
            denied_permissions.append(permission)
    return denied_permissions, granted_permissions


def _extract_requested_permissions_above_api_23(app_info_dump: str) -> list[str] | None:
    requested_permissions_regex = \
        re.search(r"requested permissions:(.*?)install permissions:", app_info_dump, re.IGNORECASE | re.DOTALL)
    # Fallback
    if requested_permissions_regex is None:
        requested_permissions_regex = re.search(
            r"requested permissions:(.*?)runtime permissions:", app_info_dump, re.IGNORECASE | re.DOTALL)

    if requested_permissions_regex is None:
        # No permissions requested by the app
        return []
    requested_permissions = requested_permissions_regex.group(1).split("\n")
    # Remove empty entries
    return list(filter(None, requested_permissions))


def _extract_install_time_permissions_above_api_23(app_info_dump: str) -> list[str] | None:
    install_time_permissions_regex = re.search(
        r"install permissions:(.*?)runtime permissions:", app_info_dump, re.IGNORECASE | re.DOTALL)
    if install_time_permissions_regex is None:
        return []
    install_time_permissions_string = install_time_permissions_regex.group(1).split("\n")
    # Remove empty entries
    return list(filter(None, install_time_permissions_string))


def _get_apk_path(app_name: str) -> str:
    adb_shell_cmd = f"pm path {app_name}"
    result = execute_adb_shell_command3(adb_shell_cmd)
    return result.stdout.split(":", 2)[1]


@ensure_package_exists
def print_app_path(app_name: str) -> None:
    apk_path = _get_apk_path(app_name)
    print_verbose(f"Path for {app_name} is {apk_path}")
    print_message(apk_path)


@ensure_package_exists
def print_app_signature(app_name: str) -> None:
    apk_path = _get_apk_path(app_name)
    # Copy apk to a temp file on the disk
    with tempfile.NamedTemporaryFile(prefix=app_name, suffix=".apk") as tmp_apk_file:
        tmp_apk_file_name = tmp_apk_file.name
        adb_cmd = f"pull {apk_path} {tmp_apk_file_name}"
        result = execute_adb_command2(adb_cmd)
        if result.return_code != 0:
            print_error_and_exit(f"Failed to pull file {apk_path}, stderr: {result.stderr}")
            return

        dir_of_this_script = os.path.split(__file__)[0]
        apk_signer_jar_path = Path(dir_of_this_script) / "apksigner.jar"
        if not Path(apk_signer_jar_path).exists():
            print_error_and_exit("apksigner.jar is missing, your adb-enhanced installation is corrupted")

        print_signature_cmd = f"java -jar {apk_signer_jar_path} verify --print-certs {tmp_apk_file_name}"
        print_verbose(f"Executing command {print_signature_cmd}")
        with subprocess.Popen(print_signature_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as ps1:
            for line in ps1.stdout:
                print_message(line.decode("utf-8").strip())
            for line in ps1.stderr:
                print_error(line.decode("utf-8").strip())


# Uses abe.jar taken from https://sourceforge.net/projects/adbextractor/
@ensure_package_exists
def perform_app_backup(app_name: str, backup_tar_file: str) -> None:
    # TODO: Add a check to ensure that the screen is unlocked
    password = "00"
    print_verbose("Performing backup to backup.ab file")
    print_message(
        f'you might have to confirm the backup manually on your device\'s screen, enter "{password}" as password...')

    def backup_func() -> None:
        # Create backup.ab
        adb_backup_cmd = f"backup -noapk {app_name}"
        execute_adb_command2(adb_backup_cmd)

    backup_thread = threading.Thread(target=backup_func)
    backup_thread.start()
    while _get_top_activity_data()[1].find("com.android.backupconfirm") == -1:
        print_verbose("Waiting for the backup activity to start")
        time.sleep(1)
    time.sleep(1)

    # Commented out since this does not always work and can sometimes lead to random clicks on some devices
    # making backups impossible.
    # # Tap the backup button
    # # Get the location of "backup data" button and tap it.
    # window_size_x, window_size_y = _get_window_size()
    # # These numbers are purely derived from heuristics and can be improved.
    # _perform_tap(window_size_x - 200, window_size_y - 100)

    backup_thread.join(timeout=10)
    if backup_thread.is_alive():
        print_error("Backup failed in first attempt, trying again...")
        # _perform_tap(window_size_x - 200, window_size_y - 100)
        backup_thread.join(timeout=10)
        if backup_thread.is_alive():
            print_error_and_exit("Backup failed")

    # Convert ".ab" to ".tar" using Android Backup Extractor (ABE)
    try:
        dir_of_this_script = os.path.split(__file__)[0]
        abe_jar_path = Path(dir_of_this_script) / "abe.jar"
        if not Path(abe_jar_path).exists():
            print_error_and_exit("Abe.jar is missing, your adb-enhanced installation is corrupted")
        abe_cmd = f"java -jar {abe_jar_path} unpack backup.ab {backup_tar_file} {password}"
        print_verbose(f"Executing command {abe_cmd}")
        with subprocess.Popen(abe_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as ps:
            ps.communicate()
            if ps.returncode == 0:
                print_message(f"Successfully backed up data of app {app_name} to {backup_tar_file}")
            else:
                print_error("Failed to convert backup.ab to tar file. Please ensure that it is not password protected")
    finally:
        print_verbose("Deleting backup.ab")
        with subprocess.Popen("rm backup.ab", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as ps2:
            ps2.communicate()


def perform_install(file_path: str) -> None:
    if not Path(file_path).exists():
        print_error_and_exit(f"File {file_path} does not exist")

    if file_path.endswith(".xapk"):
        _perform_xapk_install(file_path)
        return

    print_verbose(f"Installing {file_path}")
    # -r: replace existing application
    result = execute_adb_command2(f"install -r {file_path}")
    if result.return_code != 0:
        print_error(f"Failed to install {file_path}, stderr: {result.stderr}")


# Note this does not handle the obb files, which are deprecated
# https://android-developers.googleblog.com/2020/11/new-android-app-bundle-and-target-api.html
def _perform_xapk_install(file_path: str) -> None:
    # Unzip the xapk file
    with tempfile.TemporaryDirectory() as temp_dir:
        print_verbose(f"Unzipping {file_path} to {temp_dir}")
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        result = execute_adb_command2(f"install-multiple -r {temp_dir}/*.apk")
        if result.return_code != 0:
            print_error_and_exit(f"Failed to install xapk {file_path}, stderr: {result.stderr}")


@ensure_package_exists
def perform_uninstall(app_name: str, *, first_user: bool) -> None:
    print_verbose(f"Uninstalling {app_name}")
    cmd = ""
    if first_user:
        # For system apps, that cannot be uninstalled,
        # this command uninstalls them for user 0 without doing a system uninstall
        # since that would fail.
        # https://www.xda-developers.com/uninstall-carrier-oem-bloatware-without-root-access/
        cmd = "--user 0"
    return_code, _, stderr = execute_adb_shell_command2(f"pm uninstall {cmd} {app_name}")
    if return_code == 0:
        return

    if not cmd:
        print_message("Uninstall failed, trying to uninstall for user 0...")
        cmd = "--user 0"
        return_code, _, stderr = execute_adb_shell_command2(f"pm uninstall {cmd} {app_name}")

    if return_code != 0:
        print_error(f"Failed to uninstall {app_name}, stderr: {stderr}")


def _perform_tap(x: int, y: int) -> None:
    adb_shell_cmd = f"input tap {x:d} {y:d}"
    execute_adb_shell_command3(adb_shell_cmd)


# Deprecated use execute_adb_shell_settings_command3
def _execute_adb_shell_settings_command2(settings_cmd: str, device_serial: str | None = None) -> tuple[int, str | None, str]:
    result = _execute_adb_shell_settings_command3(settings_cmd, device_serial)
    return result.return_code, result.stdout, result.stderr


def _execute_adb_shell_settings_command3(settings_cmd: str, device_serial: str | None = None) -> CommandResult:
    _error_if_min_version_less_than(19)
    return execute_adb_shell_command3(f"settings {settings_cmd}", device_serial)


def _execute_adb_shell_settings_command_and_poke_activity_service(settings_cmd: str) -> str:
    return_value = _execute_adb_shell_settings_command3(settings_cmd).stdout
    _poke_activity_service()
    return return_value


def _execute_adb_shell_command_and_poke_activity_service(adb_cmd: str) -> str:
    result = execute_adb_shell_command3(adb_cmd)
    _poke_activity_service()
    return result.stdout


def _poke_activity_service() -> CommandResult:
    return execute_adb_shell_command3(get_update_activity_service_cmd())


def _error_if_min_version_less_than(min_acceptable_version: int, device_serial: str | None = None) -> None:
    api_version = get_device_android_api_version(device_serial)
    if api_version < min_acceptable_version:
        cmd = " ".join(sys.argv[1:])
        print_error_and_exit(
            f'"{cmd}" can only be executed on API {min_acceptable_version:d} and above,'
            f' your device version is {api_version:d}')


def _is_emulator() -> bool:
    qemu = get_adb_shell_property("ro.kernel.qemu")
    return qemu is not None and qemu.strip() == "1"


def enable_wireless_debug() -> bool:
    code, result, stderr = execute_adb_shell_command2("ip address")
    if code != 0:
        print_error_and_exit("Failed to switch device to wireless debug mode, stderr: "
                             f"{stderr}")

    # Check, that phone connected to wlan
    matching = re.findall(r"inet ([\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}).*wlan0$",
                          result, re.MULTILINE)
    if matching is None or not matching:
        print_error_and_exit("Failed to switch device to wireless debug mode")

    ip = matching[0]

    result = execute_adb_command2("tcpip 5555")
    if result.return_code != 0:
        print_error_and_exit(f"Failed to switch device {ip} to wireless debug mode, "
                             f"stderr: {result.stderr}")

    result = execute_adb_command2(f"connect {ip}")
    if result.return_code != 0:
        print_error_and_exit(f"Cannot enable wireless debugging. Error: {result.stderr}")
        return False
    print_message(f"Connected via IP now you can disconnect the cable\nIP: {ip}")
    return True


def disable_wireless_debug() -> None:
    device_serials = _get_device_serials()

    if not device_serials:
        print_error_and_exit("No connected device found")
        return

    ip_list = []
    for device_serial in device_serials:
        ips = re.findall(r"([\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}:[\d]{1,5})", device_serial, 0)
        if not ips:
            print_verbose(f"Not a IP connect device, serial: {device_serial}")
            continue
        if len(ips) > 1:
            print_error(f"Malformed device IP: {device_serial}")
        print_verbose(f"Found an IP connected ADB session: {ips[0]}")
        ip_list.append(ips[0])

    result = True

    for ip in ip_list:
        result = execute_adb_command2(f"disconnect {ip}")
        if result.return_code != 0:
            print_error(f"Failed to disconnect {ip}: {result.stderr}")
            result = False
        else:
            print_message(f"Disconnected {ip}")

    if not result:
        print_error_and_exit("")


def switch_screen(switch_type: int) -> str | None:
    if switch_type == SCREEN_TOGGLE:
        result = toggle_screen()

        if result.return_code != 0:
            print_error_and_exit(f"Something gone wrong on screen control operation. Error: {result.stderr}")
        return result.stdout

    result = execute_adb_shell_command3("dumpsys display")
    if result.return_code != 0:
        print_error_and_exit(f"Something gone wrong on screen control operation. Error: {result.stderr}")

    state = re.findall(r"^\s*mScreenState=(\w*)$", result.stdout, re.MULTILINE)[0]

    if (state == "ON" and switch_type == SCREEN_OFF) or \
            (state in {"OFF", "DOZE"} and switch_type == SCREEN_ON):
        result = toggle_screen()
        if result.return_code != 0:
            print_error_and_exit(f"Something gone wrong on screen control operation. Error: {result.stderr}")

    return result.stdout


def get_dark_mode() -> str:
    _error_if_min_version_less_than(_MIN_API_FOR_DARK_MODE)
    return_code, stdout, stderr = _execute_adb_shell_settings_command2("get secure ui_night_mode")
    if return_code != 0:
        print_error(f"Failed to get current UI mode: {stderr}")
        return _USER_PRINT_VALUE_UNKNOWN
    if stdout == "null":
        return _USER_PRINT_VALUE_UNKNOWN
    val = int(stdout)
    if val == 2:
        return _USER_PRINT_VALUE_ON
    if val == 1:
        return _USER_PRINT_VALUE_OFF
    if val == 0:
        return _USER_PRINT_VALUE_AUTO
    return f"Unknown: {val:d}"


# This code worked for emulator on API 29.
# It didn't work for unrooted device on API 30.
# I am not sure if the problem is rooting or API version
def set_dark_mode(*, force: bool) -> None:
    """
    :param force: if true, force dark mode, if false don't
    """
    _error_if_min_version_less_than(_MIN_API_FOR_DARK_MODE)

    if force:
        # Ref: https://twitter.com/petedoyle_/status/1502008461080490006
        execute_adb_shell_command3("cmd uimode night yes")
        # There are reports of the following command, it didn't work for me
        # even on a rooted device when ran as a super-user
        # execute_adb_shell_command2('setprop persist.hwui.force_dark true')
    else:
        execute_adb_shell_command3("cmd uimode night no")


def print_notifications() -> None:
    # Noredact is required on Android >= 6.0 to see title and text
    code, output, err = execute_adb_shell_command2("dumpsys notification --noredact")
    if code != 0:
        print_error_and_exit("Something gone wrong on "
                             f"fetching notification info. Error: {err}")
    notification_records = re.findall(r"\s*NotificationRecord\(.*", output, re.MULTILINE)
    for i, notification_record in enumerate(notification_records):
        output_for_this_notification = output.split(notification_record)[1]
        if i + 1 < len(notification_records):
            output_for_this_notification = output_for_this_notification.split(notification_records[i + 1])[0]
        notification_package = re.findall(r"pkg=(\S*)", notification_record)[0]
        titles = re.findall(r"android.title=(.*)", output_for_this_notification)
        notification_title = titles[0] if len(titles) > 0 else None
        texts = re.findall(r"android.text=(.*)", output_for_this_notification)
        notification_text = texts[0] if len(texts) > 0 else None
        notification_actions = []
        action_strings = re.findall(r"actions=\{(.*?)\n\}", output_for_this_notification, re.MULTILINE | re.DOTALL)
        if len(action_strings) > 0 and (
                i + 1 >= len(notification_records)
                or output_for_this_notification.find(action_strings[0])
                > output_for_this_notification.find(notification_records[i + 1])):
            for actions in action_strings[0].split("\n"):
                notification_actions += re.findall(r"\".*?\"", actions)

        print_message(f"Package: {notification_package}")
        if notification_title:
            print_message(f"Title: {notification_title}")
        if notification_text and notification_text != "null":
            print_message(f"Text: {notification_text}")
        for action in notification_actions:
            print_message(f"Action: {action}")
        print_message("")


# Alarm Enum
class AlarmEnum(Enum):
    TOP = "t"
    PENDING = "p"
    HISTORY = "h"
    ALL = "a"


def print_history_alarms(output_dump_alarm: str, padding: int) -> None:
    print("App Alarm history")

    pattern_pending_alarm = \
        re.compile(r"(?<=App Alarm history:)"
                   r".*?(?=Past-due non-wakeup alarms)",
                   re.DOTALL)
    alarm_to_parse = re.sub(r" +", " ",
                            re.search(pattern_pending_alarm, output_dump_alarm).
                            group(0)).split("\n")[1:-1]

    for line in alarm_to_parse:
        package_name = line[0:line.find(",")]
        # +1 to escape ',' before user id
        fields = line[line.find(",") + 1:].split(":")
        user_id = fields[0]
        print(f"{padding}Package name: {package_name}")
        print(f"{padding * 2}User ID: {user_id}")
        # History might be missing for new alarms
        if len(fields) >= 2:
            history = fields[1]
            print(f"{padding * 2}history: {history}")


def print_top_alarms(output_dump_alarm: str, padding: str) -> None:
    print("Top Alarms:")
    pattern_top_alarm = re.compile(r"(?<=Top Alarms:\n).*?(?=Alarm Stats:)",
                                   re.DOTALL)
    alarm_to_parse = re.sub(
        r" +", " ",
        re.search(pattern_top_alarm, output_dump_alarm).group(0)).split("\n")
    temp_dict = {}
    for i, alarm_i in enumerate(alarm_to_parse):
        if re.match(r"^\+", alarm_i):
            temp_dict[alarm_i] = alarm_to_parse[i + 1]
            i += 1

    for key, value in temp_dict.items():
        # key example: +2m19s468ms running, 0 wakeups, 708 alarms: 1000:android
        # value example: *alarm*:com.android.server.action.NETWORK_STATS_POLL
        temp = key.split(",")
        running_time = temp[0].split(" ")[0]
        nb_woke_up = temp[1].strip().split(" ")[0]
        nb_alarms = temp[2].strip().split(" ")[0]
        uid = temp[2].strip().split(":")[1].strip()
        package_name = temp[2].strip().split(":")[2].strip()
        action = value.split(":")[1]
        print(f"{padding}Package name: {package_name}")
        print(f"{padding * 2}Action: {action}")
        print(f"{padding * 2}Running time: {running_time}")
        print(f"{padding * 2}Number of device woke up: {nb_woke_up}")
        print(f"{padding * 2}Number of alarms: {nb_alarms}")
        print(f"{padding * 2}User ID: {uid}")


def print_pending_alarms(output_dump_alarm: str, padding: int) -> None:
    print("Pending Alarms:")
    pattern_pending_alarm = \
        re.compile(
            r"(?<=Pending alarm batches:)"
            r".*?(?=(Pending user blocked background alarms|Past-due non-wakeup alarms))",
            re.DOTALL)
    alarm_to_parse = re.sub(
        r" +", " ",
        re.search(pattern_pending_alarm, output_dump_alarm).group(0)).split("\n")[1:-1]
    for line in alarm_to_parse:
        line = line.strip()
        if not line.startswith("Batch"):
            continue

        pattern_batch_info = re.compile(r"(?<=Batch\{).*?(?=\}:)",
                                        re.DOTALL)
        info = re.search(pattern_batch_info, line).group(0).split(" ")
        print(f"{padding}ID: {info[0]}")
        print("{}Number of alarms: {}".format(padding * 2, info[1].split("=")[1]))
        print_verbose("{}Start: {}".format(padding * 2, info[2].split("=")[1]))
        print_verbose("{}End: {}".format(padding * 2, info[3].split("=")[1]))
        if "flgs" in line:
            # TO-DO: translate the flags
            print_verbose("{}flag: {}".format(padding * 2, info[4].split("=")[1]))

        if line.startswith(("RTC", "RTC_WAKEUP", "ELAPSED", "ELAPSED_WAKEUP")):
            pattern_between_brackets = re.compile(r"(?<=\{).*?(?=\})",
                                                  re.DOTALL)
            info = re.search(pattern_between_brackets, line).group(0).split(" ")
            print("{}Alarm #{}:".format(padding * 2, line.split("#")[1].split(":")[0]))
            print_verbose("{}Type: {}".format(padding * 2, line.split("#")[0]))
            print_verbose(f"{padding * 2}ID: {info[0]}")
            print_verbose(f"{padding * 2}Type: {info[2]}")
            print_verbose(f"{padding * 2}When: {info[4]}")
            print(f"{padding * 2}Package: {info[5]}")


def alarm_manager(param: AlarmEnum) -> None:
    cmd = "dumpsys alarm"
    api_version = get_device_android_api_version()
    err_msg_api = "Your Android version (API 28 and bellow) does not support listing pending alarm"

    result = execute_adb_shell_command3(cmd)
    if result.return_code != 0:
        print_error_and_exit(f"Something gone wrong on dumping alarms. Error: {result.stderr}")
        return

    if not isinstance(param, AlarmEnum):
        print_error("Not supported parameter")
        return

    run_all = 0
    padding = ""
    if param == AlarmEnum.ALL:
        run_all = 1
        padding = "\t"

    if param == AlarmEnum.TOP or run_all == 1:
        print_top_alarms(result.stdout, padding)

    if param == AlarmEnum.PENDING or run_all == 1:
        if api_version > 28:
            print_pending_alarms(result.stdout, padding)
        else:
            print_error(err_msg_api)

    if param == AlarmEnum.HISTORY or run_all == 1:
        if api_version > 28:
            print_history_alarms(result.stdout, padding)
        else:
            print_error(err_msg_api)


def toggle_location(*, turn_on: bool) -> None:
    _error_if_min_version_less_than(_MIN_API_FOR_LOCATION)
    cmd = "put secure location_mode 3" if turn_on else "put secure location_mode 0"
    _execute_adb_shell_settings_command3(cmd)


@ensure_package_exists
def set_debug_app(app_name: str, *, wait_for_debugger: bool, persistent: bool) -> None:
    cmd = "am set-debug-app"
    if wait_for_debugger:
        cmd += " -w"
    if persistent:
        cmd += " --persistent"
    cmd += f" {app_name}"
    execute_adb_shell_command3(cmd)


def clear_debug_app() -> None:
    cmd = "am clear-debug-app"
    execute_adb_shell_command3(cmd)


# This permissions group seems to have been removed in API 29 and beyond.
# https://github.com/ashishb/adb-enhanced/runs/1799363523?check_suite_focus=true
def is_permission_group_unavailable_after_api_29(permission_group: str) -> bool:
    return permission_group in {
        "android.permission-group.CONTACTS",
        "android.permission-group.MICROPHONE",
        "android.permission-group.LOCATION",
        "android.permission-group.SMS",
    }


def print_state_change_info(state_name: str, *, old_state: str | int | bool, new_state: str | int | bool) -> None:
    if old_state != new_state:
        print_message(f'"{state_name}" state changed from "{old_state}" -> "{new_state}"')
    else:
        print_message(f'"{state_name}" state unchanged ({old_state})')


def print_display_size() -> None:
    # Ref: https://developer.android.com/training/multiscreen/screendensities
    cmd = "wm density"
    result = execute_adb_shell_command3(cmd)
    assert result.return_code == 0, f"Failed to get display size, stderr: {result.stderr}"
    display_size = re.search(r"Physical density: (\d+)", result.stdout)
    if display_size is None:
        print_error_and_exit("Failed to get display size")

    display_size = int(display_size.group(1))
    if display_size < 120:
        print_message("Display size is ldpi (120 dpi)")
    elif display_size < 160:
        print_message("Display size is mdpi (160 dpi)")
    elif display_size < 240:
        print_message("Display size is hdpi (240 dpi)")
    elif display_size < 320:
        print_message("Display size is xhdpi (320 dpi)")
    elif display_size < 480:
        print_message("Display size is xxhdpi (480 dpi)")
    else:
        print_message("Display size is xxxhdpi (640 dpi)")


def set_display_size(size: int) -> None:
    """
    Set the display size to the given value.
    :param size: The display size in dpi.
    """
    cmd = f"wm density {size:d}"
    result = execute_adb_shell_command3(cmd)
    if result.return_code != 0:
        print_error_and_exit(f"Failed to set display size, stderr: {result.stderr}")

    print_verbose(f"Display size set to {size:d} dpi")
