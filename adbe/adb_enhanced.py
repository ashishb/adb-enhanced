#!/usr/bin/env python3

import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
import os
import random
import typing
from functools import wraps, partial
from urllib.parse import urlparse
from enum import Enum
import psutil

# asyncio was introduced in version 3.5
if sys.version_info >= (3, 5):
    try:
        import asyncio_helper

        _ASYNCIO_AVAILABLE = True
    except ImportError:
        # This is to deal with python versions below 3.5
        _ASYNCIO_AVAILABLE = False
else:
    _ASYNCIO_AVAILABLE = False

try:
    # This fails when the code is executed directly and not as a part of python package installation,
    # I definitely need a better way to handle this.
    from adbe.adb_helper import (get_adb_shell_property, execute_adb_command2,
                                 execute_adb_shell_command, execute_adb_shell_command2,
                                 execute_file_related_adb_shell_command, get_package,
                                 root_required_to_access_file,
                                 get_device_android_api_version, toggle_screen)
    from adbe.output_helper import (print_message, print_error, print_error_and_exit,
                                    print_verbose)
except ImportError:
    # This works when the code is executed directly.
    # noinspection PyUnresolvedReferences
    from adb_helper import (get_adb_shell_property, execute_adb_command2,
                            execute_adb_shell_command, execute_adb_shell_command2,
                            execute_file_related_adb_shell_command, get_package,
                            root_required_to_access_file,
                            get_device_android_api_version, toggle_screen)

    # noinspection PyUnresolvedReferences
    from output_helper import (print_message, print_error, print_error_and_exit,
                               print_verbose)

_KEYCODE_BACK = 4
_MIN_API_FOR_RUNTIME_PERMISSIONS = 23
_MIN_API_FOR_DARK_MODE = 29
_MIN_API_FOR_LOCATION = 29

_REGEX_BACKUP_ALLOWED = '(pkgFlags|flags).*ALLOW_BACKUP'
_REGEX_DEBUGGABLE = '(pkgFlags|flags).*DEBUGGABLE'

# Value to be return as 'on' to the user
_USER_PRINT_VALUE_ON = 'on'
# Value to be return as 'partially on' to the user
_USER_PRINT_VALUE_PARTIALLY_ON = 'partially on'
# Value to be return as 'off' to the user
_USER_PRINT_VALUE_OFF = 'off'
# Value to be return as 'unknown' to the user
_USER_PRINT_VALUE_UNKNOWN = 'unknown'
# Value to be return as 'auto' to the user
_USER_PRINT_VALUE_AUTO = 'auto'

SCREEN_ON = 1
SCREEN_OFF = 2
SCREEN_TOGGLE = 3


# A decorator to ensure package exists
# Note: This decorator assumes that the decorated func gets package_name as
# the first parameter
def ensure_package_exists(func):
    def func_wrapper(package_name, *args, **kwargs):
        if not _package_exists(package_name):
            print_error_and_exit("Package %s does not exist" % package_name)
        return func(package_name, *args, **kwargs)
    return func_wrapper


def _package_exists(package_name):
    cmd = 'pm path %s' % package_name
    return_code, response, _ = execute_adb_shell_command2(cmd)
    return return_code == 0 and response is not None and len(response.strip()) != 0


def print_state_change_decorator(fun, title, get_state_func):
    # magic sauce to lift the name and doc of the function
    @wraps(fun)
    def ret_fun(*args, **kwargs):
        # Get state before execution
        current_state = get_state_func()
        # Call the function
        returned_value = fun(*args, **kwargs)
        # Get state after execution
        # sleep before getting the new value or we might get a stale value in some cases
        # like mobile-data on/off
        time.sleep(1)
        new_state = get_state_func()
        print_state_change_info(title, current_state, new_state)
        return returned_value
    return ret_fun


# Source:
# https://github.com/dhelleberg/android-scripts/blob/master/src/devtools.groovy
def handle_gfx(value):
    if value == 'on':
        cmd = 'setprop debug.hwui.profile visual_bars'
    elif value == 'off':
        cmd = 'setprop debug.hwui.profile false'
    elif value == 'lines':
        cmd = 'setprop debug.hwui.profile visual_lines'
    else:
        print_error_and_exit('Unexpected value for gfx %s' % value)
        return

    execute_adb_shell_command_and_poke_activity_service(cmd)


# Source: https://github.com/dhelleberg/android-scripts/blob/master/src/devtools.groovy
# https://plus.google.com/+AladinQ/posts/dpidzto1b8B
def handle_overdraw(value):
    version = get_device_android_api_version()

    if version < 19:
        if value == 'on':
            cmd = 'setprop debug.hwui.show_overdraw true'
        elif value == 'off':
            cmd = 'setprop debug.hwui.show_overdraw false'
        elif value == 'deut':
            print_error_and_exit(
                'deut mode is available only on API 19 and above, your Android API version is %d' % version)
            return
        else:
            print_error_and_exit('Unexpected value for overdraw %s' % value)
            return
    else:
        if value == 'on':
            cmd = 'setprop debug.hwui.overdraw show'
        elif value == 'off':
            cmd = 'setprop debug.hwui.overdraw false'
        elif value == 'deut':
            cmd = 'setprop debug.hwui.overdraw show_deuteranomaly'
        else:
            print_error_and_exit('Unexpected value for overdraw %s' % value)
            return

    execute_adb_shell_command_and_poke_activity_service(cmd)


# Perform screen rotation. Accepts four direction types - left, right, portrait, and landscape.
# Source:
# https://stackoverflow.com/questions/25864385/changing-android-device-orientation-with-adb
def handle_rotate(direction):
    disable_acceleration = 'put system accelerometer_rotation 0'
    execute_adb_shell_settings_command(disable_acceleration)

    if direction == 'portrait':
        new_direction = 0
    elif direction == 'landscape':
        new_direction = 1
    elif direction == 'left':
        current_direction = get_current_rotation_direction()
        print_verbose("Current direction: %s" % current_direction)
        if current_direction is None:
            return
        new_direction = (current_direction + 1) % 4
    elif direction == 'right':
        current_direction = get_current_rotation_direction()
        print_verbose("Current direction: %s" % current_direction)
        if current_direction is None:
            return
        new_direction = (current_direction - 1) % 4
    else:
        print_error_and_exit('Unexpected direction %s' % direction)
        return

    cmd = 'put system user_rotation %s' % new_direction
    execute_adb_shell_settings_command(cmd)


def get_current_rotation_direction():
    cmd = 'get system user_rotation'
    direction = execute_adb_shell_settings_command(cmd)
    print_verbose("Return value is %s" % direction)
    if not direction or direction == 'null':
        return 0  # default direction is 0, vertical straight
    try:
        return int(direction)
    except ValueError as e:
        print_error("Failed to get direction, error: \"%s\"" % e)


def handle_layout(value):
    if value:
        cmd = 'setprop debug.layout true'
    else:
        cmd = 'setprop debug.layout false'
    execute_adb_shell_command_and_poke_activity_service(cmd)


# Source: https://stackoverflow.com/questions/10506591/turning-airplane-mode-on-via-adb
# This is incomplete
def handle_airplane(turn_on):
    if turn_on:
        cmd = 'put global airplane_mode_on 1'
    else:
        cmd = 'put global airplane_mode_on 0'

    # At some version, this became a protected intent, so, it might require root to succeed.
    broadcast_change_cmd = 'am broadcast -a android.intent.action.AIRPLANE_MODE'
    # This is a protected intent which would require root to run
    # https://developer.android.com/reference/android/content/Intent.html#ACTION_AIRPLANE_MODE_CHANGED
    broadcast_change_cmd = 'su root %s' % broadcast_change_cmd
    execute_adb_shell_settings_command2(cmd)
    return_code, _, _ = execute_adb_shell_command2(broadcast_change_cmd)
    if return_code != 0:
        print_error_and_exit('Failed to change airplane mode')
    else:
        print_message('Airplane mode changed successfully')


def get_battery_saver_state():
    _error_if_min_version_less_than(19)
    cmd = 'get global low_power'
    return_code, stdout, _ = execute_adb_shell_settings_command2(cmd)
    if return_code != 0:
        print_error('Failed to get battery saver state')
        return _USER_PRINT_VALUE_UNKNOWN
    if stdout.strip() == 'null':
        return _USER_PRINT_VALUE_OFF

    try:
        state = int(stdout.strip())
    except ValueError:
        print_error('Unable to get int value from "%s"' % stdout.strip())
        return _USER_PRINT_VALUE_UNKNOWN
    if state == 0:
        return _USER_PRINT_VALUE_OFF
    else:
        return _USER_PRINT_VALUE_ON


# Source:
# https://stackoverflow.com/questions/28234502/programmatically-enable-disable-battery-saver-mode
@partial(print_state_change_decorator, title="Battery saver", get_state_func=get_battery_saver_state)
def handle_battery_saver(turn_on):
    _error_if_min_version_less_than(19)
    if turn_on:
        cmd = 'put global low_power 1'
    else:
        cmd = 'put global low_power 0'

    if turn_on:
        return_code, _, _ = execute_adb_shell_command2(get_battery_unplug_cmd())
        if return_code != 0:
            print_error_and_exit('Failed to unplug battery')
        return_code, _, _ = execute_adb_shell_command2(get_battery_discharging_cmd())
        if return_code != 0:
            print_error_and_exit('Failed to put battery in discharge mode')

    return_code, _, _ = execute_adb_shell_settings_command2(cmd)
    if return_code != 0:
        print_error_and_exit('Failed to modify battery saver mode')


# Source:
# https://stackoverflow.com/questions/28234502/programmatically-enable-disable-battery-saver-mode
def handle_battery_level(level):
    _error_if_min_version_less_than(19)
    if level < 0 or level > 100:
        print_error_and_exit(
            'Battery percentage %d is outside the valid range of 0 to 100' %
            level)
    cmd = 'dumpsys battery set level %d' % level

    execute_adb_shell_command2(get_battery_unplug_cmd())
    execute_adb_shell_command2(get_battery_discharging_cmd())
    execute_adb_shell_command2(cmd)


# Source:
# https://stackoverflow.com/questions/28234502/programmatically-enable-disable-battery-saver-mode
def handle_battery_reset():
    # The battery related commands fail silently on API 16. I am not sure about 17 and 18.
    _error_if_min_version_less_than(19)
    cmd = get_battery_reset_cmd()
    execute_adb_shell_command2(cmd)


# https://developer.android.com/training/monitoring-device-state/doze-standby.html
def handle_doze(turn_on):
    _error_if_min_version_less_than(23)

    enable_idle_mode_cmd = 'dumpsys deviceidle enable'
    if turn_on:
        # Source: https://stackoverflow.com/a/42440619
        cmd = 'dumpsys deviceidle force-idle'
        execute_adb_shell_command2(get_battery_unplug_cmd())
        execute_adb_shell_command2(get_battery_discharging_cmd())
        execute_adb_shell_command2(enable_idle_mode_cmd)
        execute_adb_shell_command2(cmd)
    else:
        cmd = 'dumpsys deviceidle unforce'
        execute_adb_shell_command2(get_battery_reset_cmd())
        execute_adb_shell_command2(enable_idle_mode_cmd)
        execute_adb_shell_command2(cmd)


# Source: https://github.com/dhelleberg/android-scripts/blob/master/src/devtools.groovy
# Ref:
# https://gitlab.com/SaberMod/pa-android-frameworks-base/commit/a53de0629f3b94472c0f160f5bbe1090b020feab
def get_update_activity_service_cmd():
    # Note: 1599295570 == ('_' << 24) | ('S' << 16) | ('P' << 8) | 'R'
    return 'service call activity 1599295570'


# This command puts the battery in discharging mode (most likely this is
# Android 6.0 onwards only)
def get_battery_discharging_cmd():
    return 'dumpsys battery set status 3'


def get_battery_unplug_cmd():
    return 'dumpsys battery unplug'


def get_battery_reset_cmd():
    return 'dumpsys battery reset'


@ensure_package_exists
def handle_get_jank(app_name):
    running = _is_app_running(app_name)
    if not running:
        # Jank information cannot be fetched unless the app is running
        print_verbose('Starting the app %s to get its jank information' % app_name)
        launch_app(app_name)

    try:
        cmd = 'dumpsys gfxinfo %s ' % app_name
        return_code, result, _ = execute_adb_shell_command2(cmd)
        print_verbose(result)
        found = False
        if return_code == 0:
            for line in result.split('\n'):
                if line.find('Janky') != -1:
                    print(line)
                    found = True
                    break
        if not found:
            print_error('No jank information found for %s' % app_name)
    finally:
        # If app was not running then kill app after getting the jank information.
        if not running:
            print_verbose('Stopping the app %s after getting its jank information' % app_name)
            force_stop(app_name)


def _is_app_running(app_name):
    return_code, result, _ = execute_adb_shell_command2('ps -o NAME')
    if return_code != 0 or not result:
        return False
    result = result.strip()
    return result.find(app_name) != -1


def handle_list_devices():
    device_serials = _get_device_serials()

    if not device_serials:
        print_error_and_exit('No attached Android device found')

    for device_serial in device_serials:
        _print_device_info(device_serial)


def _get_device_serials() -> [str]:
    cmd = 'devices -l'
    return_code, stdout, stderr = execute_adb_command2(cmd)
    if return_code != 0:
        print_error_and_exit('Failed to execute command %s, error: %s ' % (cmd, stderr))

    device_serials = []
    # Skip the first line, it says "List of devices attached"
    device_infos = stdout.split('\n')[1:]

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
        if 'unauthorized' in device_info:
            device_info = ' '.join(device_info.split()[1:])
            print_error(
                ('Unlock Device "%s" and give USB debugging access to ' +
                 'this PC/Laptop by unlocking and reconnecting ' +
                 'the device. More info about this device: "%s"\n') % (
                    device_serial, device_info))
        else:
            device_serials.append(device_serial)
    return device_serials


def _print_device_info(device_serial=None):
    manufacturer = get_adb_shell_property('ro.product.manufacturer', device_serial=device_serial)
    model = get_adb_shell_property('ro.product.model', device_serial=device_serial)
    # This worked on 4.4.3 API 19 Moto E
    display_name = get_adb_shell_property('ro.product.display', device_serial=device_serial)
    # First fallback: undocumented
    if not display_name or display_name == 'null':
        # This works on 4.4.4 API 19 Galaxy Grand Prime
        if get_device_android_api_version(device_serial=device_serial) >= 19:
            display_name = execute_adb_shell_settings_command('get system device_name', device_serial=device_serial)
    # Second fallback, documented to work on API 25 and above
    # Source: https://developer.android.com/reference/android/provider/Settings.Global.html#DEVICE_NAME
    if not display_name or display_name == 'null':
        if get_device_android_api_version(device_serial=device_serial) >= 25:
            display_name = execute_adb_shell_settings_command('get global device_name', device_serial=device_serial)

    # ABI info
    abi = get_adb_shell_property('ro.product.cpu.abi', device_serial=device_serial)
    release = get_adb_shell_property('ro.build.version.release', device_serial=device_serial)

    release = get_adb_shell_property('ro.build.version.release', device_serial=device_serial)
    sdk = get_adb_shell_property('ro.build.version.sdk', device_serial=device_serial)
    print_message(
        'Serial ID: %s\nManufacturer: %s\nModel: %s (%s)\nRelease: %s\nSDK version: %s\nCPU: %s\n' %
        (device_serial, manufacturer, model, display_name, release, sdk, abi))


def print_top_activity():
    app_name, activity_name = _get_top_activity_data()
    if app_name:
        print_message('Application name: %s' % app_name)
    if activity_name:
        print_message('Activity name: %s' % activity_name)


def _get_top_activity_data():
    cmd = 'dumpsys window windows'
    return_code, output, _ = execute_adb_shell_command2(cmd)
    if return_code != 0 and not output:
        print_error_and_exit('Device returned no response, is it still connected?')
    for line in output.split('\n'):
        line = line.strip()
        regex_result = re.search(r'ActivityRecord{.* (\S+)/(\S+)', line)
        if regex_result is None:
            continue
        app_name, activity_name = regex_result.group(1), regex_result.group(2)
        # If activity name is a short hand then complete it.
        if activity_name.startswith('.'):
            activity_name = '%s%s' % (app_name, activity_name)
        return app_name, activity_name

    print_error('Unable to extract activity name')
    return None, None


def dump_ui(xml_file):
    tmp_file = _create_tmp_file('dump-ui', 'xml')
    cmd1 = 'uiautomator dump %s' % tmp_file
    cmd2 = 'pull %s %s' % (tmp_file, xml_file)
    cmd3 = 'rm %s' % tmp_file

    print_verbose('Writing UI to %s' % tmp_file)
    return_code, _, stderr = execute_adb_shell_command2(cmd1)
    if return_code != 0:
        print_error_and_exit('Failed to execute \"%s\", stderr: \"%s\"' % (cmd1, stderr))

    print_verbose('Pulling file %s' % xml_file)
    return_code, _, stderr = execute_adb_command2(cmd2)
    print_verbose('Deleting file %s' % tmp_file)
    execute_adb_shell_command2(cmd3)
    if return_code != 0:
        print_error_and_exit('Failed to fetch file %s' % tmp_file)
    else:
        print_message('XML UI dumped to %s, you might want to format it using \"xmllint --format %s\"' %
                      (xml_file, xml_file))


@ensure_package_exists
def force_stop(app_name):
    cmd = 'am force-stop %s' % app_name
    return_code, stdout, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit('Failed to stop \"%s\"' % app_name)
    else:
        print_message(stdout)


@ensure_package_exists
def clear_disk_data(app_name):
    cmd = 'pm clear %s' % app_name
    return_code, _, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit('Failed to clear data of \"%s\"' % app_name)


def get_mobile_data_state():
    # Using "adb shell dumpsys telephony.registry | ag mDataConnectionState"
    cmd = 'dumpsys telephony.registry'
    return_code, stdout, _ = execute_adb_shell_command2(cmd)
    if return_code != 0 or not stdout:
        print_error('Failed to get mobile data setting')
        return _USER_PRINT_VALUE_UNKNOWN
    m = re.search(r'mDataConnectionState=(\d+)', stdout)
    if not m:
        print_error('Failed to get mobile data setting from "%s"' % stdout)
        return _USER_PRINT_VALUE_UNKNOWN
    if int(m.group(1)) == 0:
        return _USER_PRINT_VALUE_OFF
    else:
        return _USER_PRINT_VALUE_ON


# Source: https://developer.android.com/reference/android/provider/Settings.Global#WIFI_ON
def get_wifi_state():
    _error_if_min_version_less_than(17)

    return_code, stdout, _ = execute_adb_shell_settings_command2('get global wifi_on')
    if return_code != 0:
        print_error('Failed to get global Wi-Fi setting')
        return _USER_PRINT_VALUE_UNKNOWN

    if int(stdout.strip()) == 1:
        return _USER_PRINT_VALUE_ON
    return _USER_PRINT_VALUE_OFF


@partial(print_state_change_decorator, title="Wi-Fi", get_state_func=get_wifi_state)
def set_wifi(turn_on):
    if turn_on:
        cmd = 'svc wifi enable'
    else:
        cmd = 'svc wifi disable'
    return_code, _, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit('Failed to change Wi-Fi setting')


# Source:
# https://stackoverflow.com/questions/26539445/the-setmobiledataenabled-method-is-no-longer-callable-as-of-android-l-and-later
@partial(print_state_change_decorator, title="Mobile data", get_state_func=get_mobile_data_state)
def handle_mobile_data(turn_on):
    if turn_on:
        cmd = 'svc data enable'
    else:
        cmd = 'svc data disable'
    return_code, _, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit('Failed to change mobile data setting')


def force_rtl(turn_on):
    _error_if_min_version_less_than(19)
    if turn_on:
        cmd = 'put global debug.force_rtl 1'
    else:
        cmd = 'put global debug.force_rtl 0'
    execute_adb_shell_settings_command_and_poke_activity_service(cmd)


def dump_screenshot(filepath):
    screenshot_file_path_on_device = _create_tmp_file('screenshot', 'png')
    dump_cmd = 'screencap -p %s ' % screenshot_file_path_on_device
    return_code, stdout, stderr = execute_adb_shell_command2(dump_cmd)
    if return_code != 0:
        print_error_and_exit(
            'Failed to capture the screenshot: (stdout: %s, stderr: %s)' % (stdout, stderr))
    pull_cmd = 'pull %s %s' % (screenshot_file_path_on_device, filepath)
    execute_adb_command2(pull_cmd)
    del_cmd = 'rm %s' % screenshot_file_path_on_device
    execute_adb_shell_command2(del_cmd)


def dump_screenrecord(filepath):
    _error_if_min_version_less_than(19)
    api_version = get_device_android_api_version()

    # I have tested that on API 23 and above this works. Till Api 22, on emulator, it does not.
    if api_version < 23 and _is_emulator():
        print_error_and_exit('screenrecord is not supported on emulator below API 23\n' +
                             'Source: %s ' % 'https://issuetracker.google.com/issues/36982354')

    screen_record_file_path_on_device = None
    original_sigint_handler = None

    def _start_recording():
        global screen_record_file_path_on_device
        print_message('Recording video, press Ctrl+C to end...')
        screen_record_file_path_on_device = _create_tmp_file('screenrecord', 'mp4')
        dump_cmd = 'screenrecord --verbose %s ' % screen_record_file_path_on_device
        execute_adb_shell_command2(dump_cmd)

    def _pull_and_delete_file_from_device():
        global screen_record_file_path_on_device
        print_message('Saving recording to %s' % filepath)
        pull_cmd = 'pull %s %s' % (screen_record_file_path_on_device, filepath)
        execute_adb_command2(pull_cmd)
        del_cmd = 'rm %s' % screen_record_file_path_on_device
        execute_adb_shell_command2(del_cmd)

    def _kill_all_child_processes():
        current_process = psutil.Process()
        children = current_process.children(recursive=True)
        for child in children:
            print_verbose('Child process is %s' % child)
            os.kill(child.pid, signal.SIGTERM)

    def _handle_recording_ended():
        print_message('Finishing...')
        # Kill all child processes.
        # This is not neat but it is OK for now since we know that we have only one adb child process which is
        # running screen recording.
        _kill_all_child_processes()
        # Wait for one second.
        time.sleep(1)
        # Finish rest of the processing.
        _pull_and_delete_file_from_device()
        # And exit
        sys.exit(0)

    def signal_handler(unused_sig, unused_frame):
        # Restore the original handler for Ctrl-C
        signal.signal(signal.SIGINT, original_sigint_handler)
        _handle_recording_ended()

    original_sigint_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, signal_handler)

    _start_recording()


def get_mobile_data_saver_state():
    cmd = 'cmd netpolicy get restrict-background'
    return_code, stdout, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error('Failed to get mobile data saver mode setting')
        return _USER_PRINT_VALUE_UNKNOWN
    enabled = stdout.strip().find('enabled') != -1
    if enabled:
        return _USER_PRINT_VALUE_ON
    else:
        return _USER_PRINT_VALUE_OFF


# https://developer.android.com/training/basics/network-ops/data-saver.html
@partial(print_state_change_decorator, title="Mobile data saver", get_state_func=get_mobile_data_saver_state)
def handle_mobile_data_saver(turn_on):
    if turn_on:
        cmd = 'cmd netpolicy set restrict-background true'
    else:
        cmd = 'cmd netpolicy set restrict-background false'
    return_code, _, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit('Failed to modify data saver mode setting')


def get_dont_keep_activities_in_background_state():
    cmd = 'get global always_finish_activities'
    return_code, stdout, _ = execute_adb_shell_settings_command2(cmd)
    if return_code != 0:
        print_error('Failed to get don\'t keep activities in the background setting')
        return _USER_PRINT_VALUE_UNKNOWN

    if stdout is None or stdout.strip() == 'null':
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
         title="Don\'t keep activities",
         get_state_func=get_dont_keep_activities_in_background_state)
def handle_dont_keep_activities_in_background(turn_on):
    # Till Api 25, the value was True/False, above API 25, 1/0 work. Source: manual testing
    use_true_false_as_value = get_device_android_api_version() <= 25

    if turn_on:
        value = 'true' if use_true_false_as_value else '1'
        cmd1 = 'put global always_finish_activities %s' % value
        cmd2 = 'service call activity 43 i32 1'
    else:
        value = 'false' if use_true_false_as_value else '0'
        cmd1 = 'put global always_finish_activities %s' % value
        cmd2 = 'service call activity 43 i32 0'
    execute_adb_shell_settings_command(cmd1)
    execute_adb_shell_command_and_poke_activity_service(cmd2)


def toggle_animations(turn_on):
    if turn_on:
        value = 1
    else:
        value = 0

    # Source: https://github.com/jaredsburrows/android-gif-example/blob/824c493285a2a2cf22f085662431cf0a7aa204b8/.travis.yml#L34
    cmd1 = 'put global window_animation_scale %d' % value
    cmd2 = 'put global transition_animation_scale %d' % value
    cmd3 = 'put global animator_duration_scale %d' % value

    execute_adb_shell_settings_command(cmd1)
    execute_adb_shell_settings_command(cmd2)
    execute_adb_shell_settings_command(cmd3)


def get_show_taps_state():
    cmd = 'get system show_touches'
    return_code, stdout, _ = execute_adb_shell_settings_command2(cmd)
    if return_code != 0:
        print_error('Failed to get current state of "show user taps" setting')
        return _USER_PRINT_VALUE_UNKNOWN

    stdout = stdout.strip()
    if stdout == 'null':
        return _USER_PRINT_VALUE_OFF
    if int(stdout) == 1:
        return _USER_PRINT_VALUE_ON
    return _USER_PRINT_VALUE_OFF


@partial(print_state_change_decorator, title="Show user taps", get_state_func=get_show_taps_state)
def toggle_show_taps(turn_on):
    if turn_on:
        value = 1
    else:
        value = 0

    # Source: https://stackoverflow.com/a/32621809/434196
    cmd = 'put system show_touches %d' % value
    execute_adb_shell_settings_command(cmd)


def get_stay_awake_while_charging_state():
    cmd = 'get global stay_on_while_plugged_in'
    return_code, stdout, _ = execute_adb_shell_settings_command2(cmd)
    if return_code != 0:
        print_error('Failed to get "stay awake while plugged in" in the background setting')
        return _USER_PRINT_VALUE_UNKNOWN
    value = int(stdout.strip())
    if value == 0:
        return _USER_PRINT_VALUE_OFF
    elif value == 7:
        return _USER_PRINT_VALUE_ON
    return _USER_PRINT_VALUE_PARTIALLY_ON


# Source: https://developer.android.com/reference/android/provider/Settings.Global.html#STAY_ON_WHILE_PLUGGED_IN
@partial(print_state_change_decorator,
         title="Stay awake while charging",
         get_state_func=get_stay_awake_while_charging_state)
def stay_awake_while_charging(turn_on):
    if turn_on:
        # 1 for USB charging, 2 for AC charging, 4 for wireless charging. Or them together to get 7.
        value = 7
    else:
        value = 0

    cmd1 = 'put global stay_on_while_plugged_in %d' % value
    execute_adb_shell_settings_command_and_poke_activity_service(cmd1)


def input_text(text):
    # Replace whitespaces to %s which gets translated by Android back to whitespaces.
    cmd = 'input text %s' % text.replace(' ', '%s')
    return_code, _, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit('Failed to input text \"%s\"' % text)


def press_back():
    cmd = 'input keyevent 4'
    return_code, _, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit('Failed to press back')


def open_url(url):
    # Let's not do any URL encoding for now, if required, we will add that in the future.
    parsed_url = urlparse(url=url)
    if not parsed_url.scheme:
        parsed_url2 = urlparse(url=url, scheme='http')
        url = parsed_url2.geturl()
    cmd = 'am start -a android.intent.action.VIEW -d %s' % url
    return_code, _, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit('Failed to open url \"%s\"' % url)


def list_permission_groups():
    cmd = 'pm list permission-groups'
    return_code, stdout, _ = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit('Failed to list permission groups')
    else:
        print_message(stdout)


def list_permissions(dangerous_only_permissions):
    # -g is to group permissions by permission groups.
    if dangerous_only_permissions:
        # -d => dangerous only permissions
        cmd = 'pm list permissions -g -d'
    else:
        cmd = 'pm list permissions -g'
    return_code, stdout, stderr = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit('Failed to list permissions: (stdout: %s, stderr: %s)' % (stdout, stderr))
    else:
        print_message(stdout)


# Creates a tmp file on Android device
def _create_tmp_file(filename_prefix=None, filename_suffix=None):
    if filename_prefix is None:
        filename_prefix = 'file'
    if filename_suffix is None:
        filename_suffix = 'tmp'
    if filename_prefix.find('/') != -1:
        print_error_and_exit('Filename prefix "%s" contains illegal character: "/"' % filename_prefix)
    if filename_suffix.find('/') != -1:
        print_error_and_exit('Filename suffix "%s" contains illegal character: "/"' % filename_suffix)

    tmp_dir = '/data/local/tmp'

    filepath_on_device = '%s/%s-%d.%s' % (
        tmp_dir, filename_prefix, random.randint(1, 1000 * 1000 * 1000), filename_suffix)
    if _file_exists(filepath_on_device):
        # Retry if the file already exists
        print_verbose('Tmp File %s already exists, trying a new random name' % filepath_on_device)
        return _create_tmp_file(filename_prefix, filename_suffix)

    # Create the file
    return_code, stdout, stderr = execute_adb_shell_command2('touch %s' % filepath_on_device)
    if return_code != 0:
        print_error('Failed to create tmp file %s: (stdout: %s, stderr: %s)' % (filepath_on_device, stdout, stderr))
        return None

    # Make the tmp file world-writable or else, run-as command might fail to write on it.
    return_code, stdout, stderr = execute_adb_shell_command2('chmod 666 %s' % filepath_on_device)
    if return_code != 0:
        print_error('Failed to chmod tmp file %s: (stdout: %s, stderr: %s)' % (filepath_on_device, stdout, stderr))
        return None

    return filepath_on_device


# Returns true if the file_path exists on the device, false if it does not exists or is inaccessible.
def _file_exists(file_path):
    exists_cmd = "\"ls %s 1>/dev/null 2>/dev/null && echo exists\"" % file_path
    stdout = execute_file_related_adb_shell_command(exists_cmd, file_path)
    return stdout is not None and stdout.find('exists') != -1


def _is_sqlite_database(file_path):
    return file_path.endswith('.db')


# Returns a fully-qualified permission group name.
def get_permission_group(args):
    if args['contacts']:
        return 'android.permission-group.CONTACTS'
    elif args['phone']:
        return 'android.permission-group.PHONE'
    elif args['calendar']:
        return 'android.permission-group.CALENDAR'
    elif args['camera']:
        return 'android.permission-group.CAMERA'
    elif args['sensors']:
        return 'android.permission-group.SENSORS'
    elif args['location']:
        return 'android.permission-group.LOCATION'
    elif args['storage']:
        return 'android.permission-group.STORAGE'
    elif args['microphone']:
        return 'android.permission-group.MICROPHONE'
    elif args['sms']:
        return 'android.permission-group.SMS'
    else:
        print_error_and_exit('Unexpected permission group: %s' % args)
        return None


# Android keeps emptying these groups so that granted permissions are denied
# but the expectation of this tool is to do the right mapping
def _get_hardcoded_permissions_for_group(permission_group) -> typing.List[str]:
    if permission_group == 'android.permission-group.CONTACTS':
        return ['android.permission.READ_CONTACTS', 'android.permission.WRITE_CONTACTS']
    elif permission_group == 'android.permission-group.PHONE':
        return ['android.permission.READ_PHONE_STATE', 'android.permission.READ_PHONE_NUMBERS',
                'android.permission.CALL_PHONE', 'android.permission.ANSWER_PHONE_CALLS']
    elif permission_group == 'android.permission-group.CALENDAR':
        return ['android.permission.READ_CALENDAR', 'android.permission.WRITE_CALENDAR']
    elif permission_group == 'android.permission-group.CAMERA':
        return ['android.permission.CAMERA']
    elif permission_group == 'android.permission-group.SENSORS':
        return ['android.permission.BODY_SENSORS']
    elif permission_group == 'android.permission-group.LOCATION':
        return ['android.permission.ACCESS_FINE_LOCATION', 'android.permission.ACCESS_COARSE_LOCATION']
    elif permission_group == 'android.permission-group.STORAGE':
        return ['android.permission.READ_EXTERNAL_STORAGE', 'android.permission.WRITE_EXTERNAL_STORAGE']
    elif permission_group == 'android.permission-group.MICROPHONE':
        return ['android.permission.RECORD_AUDIO']
    elif permission_group == 'android.permission-group.SMS':
        return ['android.permission.READ_SMS', 'android.permission.RECEIVE_SMS', 'android.permission.SEND_SMS']
    else:
        print_verbose('Unexpected permission group: %s' % permission_group)
        return []


# Pass the full-qualified permission group name to this method.
def get_permissions_in_permission_group(permission_group):
    # List permissions by group
    cmd = 'pm list permissions -g'
    return_code, stdout, stderr = execute_adb_shell_command2(cmd)
    if return_code != 0:
        print_error_and_exit('Failed to run command %s (stdout: %s, stderr: %s)' % (cmd, stdout, stderr))
        return None

    permission_output = stdout
    # Remove ungrouped permissions section completely.
    if 'ungrouped:' in permission_output:
        permission_output, _ = permission_output.split('ungrouped:')
    splits = permission_output.split('group:')
    for split in splits:
        if split.startswith(permission_group):
            potential_permissions = split.split('\n')
            # Ignore the first entry which is the group name
            potential_permissions = potential_permissions[1:]
            # Filter out empty lines.
            permissions = filter(
                lambda x: len(
                    x.strip()) > 0,
                potential_permissions)
            permissions = list(map(
                lambda x: x.replace(
                    'permission:', ''), permissions))
            permissions = list(set(permissions + _get_hardcoded_permissions_for_group(permission_group)))
            print_message(
                'Permissions in %s group are %s' %
                (permission_group, permissions))
            return permissions
    return _get_hardcoded_permissions_for_group(permission_group)


@ensure_package_exists
def grant_or_revoke_runtime_permissions(package_name, action_grant, permissions):
    _error_if_min_version_less_than(23)

    app_info_dump = execute_adb_shell_command('dumpsys package %s' % package_name)
    permissions_formatted_dump = _get_permissions_info_above_api_23(app_info_dump).split('\n')

    if action_grant:
        base_cmd = 'pm grant %s' % package_name
        action_display_name = 'Granting'
    else:
        base_cmd = 'pm revoke %s' % package_name
        action_display_name = 'Revoking'
    num_permissions_granted = 0
    for permission in permissions:
        if permission not in permissions_formatted_dump:
            print_message('Permission %s is not requested by %s, skipping' % (permission, package_name))
            continue
        num_permissions_granted += 1
        print_message('%s %s permission to %s' % (action_display_name, permission, package_name))
        execute_adb_shell_command(base_cmd + ' ' + permission)
    if num_permissions_granted == 0:
        print_error_and_exit('None of these permissions were granted to %s: %s' %(package_name, permissions))


def _get_all_packages(pm_cmd):
    return_code, result, _ = execute_adb_shell_command2(pm_cmd)
    if return_code != 0:
        print_error_and_exit('Command "%s" failed, something is wrong' % pm_cmd)
    packages = []
    if result:
        for line in result.split('\n'):
            _, package_name = line.split(':', 2)
            packages.append(package_name)
    return packages


# "dumpsys package" is more accurate than "pm list packages" but that means the results of
# list_all_apps are now different from list_system_apps, print_list_non_system_apps, and
# list_debug_apps
# For now, we can live with this discrepancy but in the longer run we want to fix those
# other functions as well
# https://stackoverflow.com/questions/63416599/adb-shell-pm-list-packages-missing-some-packages
def get_list_all_apps():
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
    cmd = 'dumpsys package'
    pattern_packages = re.compile('Package \\[(.*?)\\]')
    return_code, result, err = execute_adb_shell_command2(cmd)
    if return_code != 0:
        err_msg = 'Command "%s" failed, something is wrong' % cmd
        return None, err_msg, err
    all_apps = re.findall(pattern_packages, result)
    # Get the unique results
    all_apps = sorted(list(dict.fromkeys(all_apps)))
    return all_apps, None, None


def print_list_all_apps():
    """This function print list of all installed packages or error message if an error
    occurred
    :returns: None
    """
    all_apps, err_msg, err = get_list_all_apps()
    if err:
        print_error_and_exit(err_msg)
        return
    print_message('\n'.join(all_apps))


def get_list_system_apps():
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
    cmd = 'pm list packages -s'
    system_apps_packages = _get_all_packages(cmd)
    return system_apps_packages


def list_system_apps():
    """This function print list of installed system packages
    :returns: None
    """
    packages = get_list_system_apps()
    print('\n'.join(packages))


def get_list_non_system_apps():
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
    cmd = 'pm list packages -3'
    return _get_all_packages(cmd)


def print_list_non_system_apps():
    """Print list of installed third party packages.
    :returns: None
    """
    print('\n'.join(get_list_non_system_apps()))


def get_list_debug_apps():
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
    cmd = 'pm list packages'
    packages = _get_all_packages(cmd)
    debug_packages = []

    if _ASYNCIO_AVAILABLE:
        method_to_call = _is_debug_package
        params_list = packages
        result_list = asyncio_helper.execute_in_parallel(method_to_call, params_list)

        for (package_name, debuggable) in result_list:
            if debuggable:
                debug_packages.append(package_name)
    else:
        debug_packages = _list_debug_apps_no_async(packages)
    return debug_packages


def print_list_debug_apps():
    """Print installed applications that have debug enabled.
        :returns: None
        :Example:
        >>> import adbe.adb_enhanced as adb_e
        >>> import adbe.adb_helper as adb_h
        >>> adb_h.set_device_id("DEVICE_ID")
        >>> list_debug_apps = adb_e.adb_print_list_debug_apps()
    """
    if not _ASYNCIO_AVAILABLE:
        print_message('Use python3 for faster execution of this call')

    print('\n'.join(get_list_debug_apps()))


def _list_debug_apps_no_async(packages):
    """Return a list of applications that have debug enabled without asynchronous enabled (less faster).
        :returns: None
            WHERE
            list[str] packages is a strings list of installed packages names
    """
    debug_packages = []
    count = 0
    num_packages = len(packages)
    for package in packages:
        count += 1
        print_verbose("Checking package: %d/%s" % (count, num_packages))
        # No faster way to do this except to check each and every package individually
        if _is_debug_package(package)[1]:
            debug_packages.append(package)

    return debug_packages


def _is_debug_package(app_name):
    """Return true if the application have the debug flag set to true else return false
        :returns: None
            WHERE
            str app_name is a string of the package name
    """
    return _package_contains_flag(app_name, _REGEX_DEBUGGABLE)


def list_allow_backup_apps():
    """Return list of applications that can be backed up (flag backup set to true)
        :returns: list[str] packages that have backup flag set to true
        :Example:
        >>> import adbe.adb_enhanced as adb_e
        >>> import adbe.adb_helper as adb_h
        >>> adb_h.set_device_id("DEVICE_ID")
        >>> adb_e.list_allow_backup_apps()
    """
    cmd = 'pm list packages'
    packages = _get_all_packages(cmd)

    if _ASYNCIO_AVAILABLE:
        method_to_call = _is_allow_backup_package
        params_list = packages
        result_list = asyncio_helper.execute_in_parallel(method_to_call, params_list)
        debug_packages = []
        for (package_name, debuggable) in result_list:
            if debuggable:
                debug_packages.append(package_name)
        return debug_packages
    else:
        print_message('Use python3 with Async IO package for faster execution of this call')
        return _list_allow_backup_apps_no_async(packages)


def print_allow_backup_apps():
    """Print list of applications that can be backed up (flag backup set to true)
        :returns: None
        :Example:
        >>> import adbe.adb_enhanced as adb_e
        >>> import adbe.adb_helper as adb_h
        >>> adb_h.set_device_id("DEVICE_ID")
        >>> adb_e.print_allow_backup_apps()
    """
    print('\n'.join(list_allow_backup_apps()))


def _list_allow_backup_apps_no_async(packages):
    """Return list of applications that can be backed up (flag backup set to true) without
       asynchronous enabled (less faster).
            :returns: list[str] packages that have backup flag set to true
    """
    debug_packages = []
    count = 0
    num_packages = len(packages)
    for package in packages:
        count += 1
        print_verbose("Checking package: %d/%s" % (count, num_packages))
        # No faster way to do this except to check each and every package individually
        if _is_allow_backup_package(package)[1]:
            debug_packages.append(package)
    return debug_packages


def _is_allow_backup_package(app_name):
    return _package_contains_flag(app_name, _REGEX_BACKUP_ALLOWED)


def _package_contains_flag(app_name, flag_regex):
    pm_cmd = 'dumpsys package %s' % app_name
    grep_cmd = '(grep -c -E \'%s\' || true)' % flag_regex
    app_info_dump = execute_adb_shell_command(pm_cmd, piped_into_cmd=grep_cmd)
    if app_info_dump is None or app_info_dump.strip() == '0':
        return app_name, False
    try:
        val = int(app_info_dump.strip())
        if val > 0:
            return app_name, True
        return None, False
    except ValueError:
        print_error_and_exit('Unexpected output for %s | %s = "%s"' % (pm_cmd, grep_cmd, app_info_dump))
        return None, False


# Source: https://developer.android.com/reference/android/app/usage/UsageStatsManager#STANDBY_BUCKET_ACTIVE
_APP_STANDBY_BUCKETS = {
    10: 'active',
    20: 'working',
    30: 'frequent',
    40: 'rare',
}


# Source: https://developer.android.com/preview/features/power#buckets
@ensure_package_exists
def get_standby_bucket(package_name):
    _error_if_min_version_less_than(28)
    cmd = 'am get-standby-bucket %s' % package_name
    result = execute_adb_shell_command(cmd)
    if result is None:
        print_error_and_exit(_USER_PRINT_VALUE_UNKNOWN)
    print_verbose('App standby bucket for \"%s\" is %s' % (
        package_name, _APP_STANDBY_BUCKETS.get(int(result), _USER_PRINT_VALUE_UNKNOWN)))
    print(_APP_STANDBY_BUCKETS.get(int(result), _USER_PRINT_VALUE_UNKNOWN))


@ensure_package_exists
def set_standby_bucket(package_name, mode):
    _error_if_min_version_less_than(28)
    cmd = 'am set-standby-bucket %s %s' % (package_name, mode)
    result = execute_adb_shell_command(cmd)
    if result is not None:  # Expected
        print_error_and_exit(result)


def calculate_standby_mode(args):
    if args['active']:
        return 'active'
    elif args['working_set']:
        return 'working_set'
    elif args['frequent']:
        return 'frequent'
    elif args['rare']:
        return 'rare'

    raise ValueError('Illegal argument: %s' % args)


# Source: https://developer.android.com/preview/features/power
@ensure_package_exists
def apply_or_remove_background_restriction(package_name, set_restriction):
    _error_if_min_version_less_than(28)
    appops_cmd = 'cmd appops set %s RUN_ANY_IN_BACKGROUND %s' % (
        package_name, 'ignore' if set_restriction else 'allow')
    execute_adb_shell_command(appops_cmd)


def list_directory(file_path, long_format, recursive, include_hidden_files):
    cmd_prefix = 'ls'
    if long_format:
        cmd_prefix += ' -l'
    if recursive:
        cmd_prefix += ' -R'
    if include_hidden_files:
        cmd_prefix += ' -a'
    cmd = '%s \"%s\"' % (cmd_prefix, file_path)
    print_message(execute_file_related_adb_shell_command(cmd, file_path))


def delete_file(file_path, force, recursive):
    cmd_prefix = 'rm'
    if force:
        cmd_prefix += ' -f'
    if recursive:
        cmd_prefix += ' -r'
    cmd = '%s %s' % (cmd_prefix, file_path)
    print_message(execute_file_related_adb_shell_command(cmd, file_path))


# Limitation: This command will only do run-as for the src file so, if a file is being copied from pkg1 to pkg2
# on a non-rooted device with both pkg1 and pkg2 being debuggable, this will fail. This can be improved by
# first copying the file to /data/local/tmp but as of now, I don't think that's required.
def move_file(src_path, dest_path, force):
    cmd_prefix = 'mv'
    if force:
        cmd_prefix += '-f'
    cmd = '%s %s %s' % (cmd_prefix, src_path, dest_path)
    if get_package(src_path) and get_package(dest_path) and get_package(src_path) != get_package(dest_path):
        print_error_and_exit('Cannot copy a file from one package into another, copy it via /data/local/tmp instead')
        return

    file_path = None
    if get_package(src_path):
        file_path = src_path
    elif get_package(dest_path):
        file_path = dest_path
    move_stdout = execute_file_related_adb_shell_command(cmd, file_path)
    if move_stdout:
        print_message(move_stdout)
    print_verbose('Moved "%s" to "%s"' % (src_path, dest_path))


# Copies from remote_file_path on Android to local_file_path on the disk
# local_file_path can be None
def pull_file(remote_file_path, local_file_path, copy_ancillary=False):
    if not _file_exists(remote_file_path):
        print_error_and_exit('File %s does not exist' % remote_file_path)

    if local_file_path is None:
        local_file_path = remote_file_path.split('/')[-1]
        print_verbose('Local file path not provided, using \"%s\" for that' % local_file_path)

    remote_file_path_package = get_package(remote_file_path)
    if remote_file_path_package is None and not root_required_to_access_file(remote_file_path):
        print_verbose('File %s is not inside a package, no temporary file required' % remote_file_path_package)
        pull_cmd = 'pull %s %s' % (remote_file_path, local_file_path)
        execute_adb_command2(pull_cmd)
    else:
        # First copy the files to sdcard, then pull them out, and then delete them from sdcard.
        tmp_file = _create_tmp_file()
        cp_cmd = 'cp -r %s %s' % (remote_file_path, tmp_file)
        execute_file_related_adb_shell_command(cp_cmd, remote_file_path)
        pull_cmd = 'pull %s %s' % (tmp_file, local_file_path)
        execute_adb_command2(pull_cmd)
        del_cmd = 'rm -r %s' % tmp_file
        execute_adb_shell_command(del_cmd)

    if os.path.exists(local_file_path):
        print_message('Copied remote file \"%s\" to local file \"%s\" (Size: %d bytes)' % (
            remote_file_path,
            local_file_path,
            os.path.getsize(local_file_path)))
    else:
        print_error_and_exit('Failed to copy remote file \"%s\" to local file \"%s\"' % (
            remote_file_path,
            local_file_path))

    if _is_sqlite_database(remote_file_path):
        # Copy temporary Sqlite files
        # Source :https://ashishb.net/all/android-the-right-way-to-pull-sqlite-database-from-the-device/
        for suffix in ['wal', 'journal', 'shm']:
            tmp_db_file = '%s-%s' % (remote_file_path, suffix)
            if not _file_exists(tmp_db_file):
                continue
            if copy_ancillary:
                pull_file(tmp_db_file, '%s-%s' % (local_file_path, suffix), copy_ancillary=True)
            else:
                print_error('File \"%s\" has an ancillary file \"%s\" which should be copied.\nSee %s for details'
                            % (remote_file_path, tmp_db_file,
                               'https://ashishb.net/all/android-the-right-way-to-pull-sqlite-database-from-the-device/'))


# Limitation: It seems that pushing to a directory on some versions of Android fail silently.
# It is safer to push to a full path containing the filename.
def push_file(local_file_path, remote_file_path):
    if not os.path.exists(local_file_path):
        print_error_and_exit('Local file %s does not exist' % local_file_path)
    if os.path.isdir(local_file_path):
        print_error_and_exit('This tool does not support pushing a directory yet: %s' % local_file_path)

    # First push to tmp file in /data/local/tmp and then move that
    tmp_file = _create_tmp_file()
    push_cmd = 'push %s %s' % (local_file_path, tmp_file)
    # "mv" from /data/local/tmp with run-as <app_id> does not always work even when the underlying
    # dir has mode set to 777. Therefore, do a two-step cp and rm.
    cp_cmd = 'cp %s %s' % (tmp_file, remote_file_path)
    rm_cmd = 'rm %s' % tmp_file

    return_code, _, stderr = execute_adb_command2(push_cmd)
    if return_code != 0:
        print_error_and_exit('Failed to push file, error: %s' % stderr)
        return

    execute_file_related_adb_shell_command(cp_cmd, remote_file_path)
    execute_adb_shell_command(rm_cmd)


def cat_file(file_path):
    cmd_prefix = 'cat'
    cmd = '%s %s' % (cmd_prefix, file_path)
    cat_stdout = execute_file_related_adb_shell_command(cmd, file_path)
    # Don't print "None" for an empty file
    if cat_stdout:
        print_message(execute_file_related_adb_shell_command(cmd, file_path))


# Source: https://stackoverflow.com/a/25398877
@ensure_package_exists
def launch_app(app_name):
    adb_shell_cmd = 'monkey -p %s -c android.intent.category.LAUNCHER 1' % app_name
    execute_adb_shell_command(adb_shell_cmd)


@ensure_package_exists
def stop_app(app_name):
    # Below API 21, stop does not kill app in the foreground.
    # Above API 21, it seems it does.
    if get_device_android_api_version() < 21:
        force_stop(app_name)
    else:
        adb_shell_cmd = 'am kill %s' % app_name
        execute_adb_shell_command(adb_shell_cmd)


def _regex_extract(regex, data):
    regex_object = re.search(regex, data, re.IGNORECASE)
    if regex_object:
        return regex_object.group(1)
    return None


# adb shell pm dump <app_name> produces about 1200 lines, mostly useless,
# compared to this.
@ensure_package_exists
def print_app_info(app_name):
    app_info_dump = execute_adb_shell_command('dumpsys package %s' % app_name)
    version_code = _regex_extract('versionCode=(\\d+)?', app_info_dump)
    version_name = _regex_extract('versionName=([\\d.]+)?', app_info_dump)
    min_sdk_version = _regex_extract('minSdk=(\\d+)?', app_info_dump)
    target_sdk_version = _regex_extract('targetSdk=(\\d+)?', app_info_dump)
    max_sdk_version = _regex_extract('maxSdk=(\\d+)?', app_info_dump)
    installer_package_name = _regex_extract('installerPackageName=(\\S+)?', app_info_dump)
    is_debuggable = re.search(
        _REGEX_DEBUGGABLE,
        app_info_dump,
        re.IGNORECASE) is not None

    msg = ''
    msg += 'App name: %s\n' % app_name
    msg += 'Version: %s\n' % version_name
    msg += 'Version Code: %s\n' % version_code
    msg += 'Is debuggable: %r\n' % is_debuggable
    msg += 'Min SDK version: %s\n' % min_sdk_version
    msg += 'Target SDK version: %s\n' % target_sdk_version
    if max_sdk_version is not None:
        msg += 'Max SDK version: %s\n' % max_sdk_version

    if get_device_android_api_version() >= 23:
        msg += _get_permissions_info_above_api_23(app_info_dump)
    else:
        msg += _get_permissions_info_below_api_23(app_info_dump)

    msg += 'Installer package name: %s\n' % installer_package_name
    print_message(msg)


# API < 23 have no runtime permissions
def _get_permissions_info_below_api_23(app_info_dump):
    install_time_permissions_regex = re.search('grantedPermissions:(.*)', app_info_dump,
                                               re.IGNORECASE | re.DOTALL)
    if install_time_permissions_regex is None:
        install_time_permissions_string = []
    else:
        install_time_permissions_string = install_time_permissions_regex.group(1).split('\n')

    install_time_granted_permissions = []
    install_time_permissions_string = filter(None, install_time_permissions_string)
    for permission_string in install_time_permissions_string:
        install_time_granted_permissions.append(permission_string)

    permissions_info_msg = ''
    if install_time_granted_permissions:
        permissions_info_msg += 'Install time granted permissions:\n%s\n\n' % '\n'.join(
            install_time_granted_permissions)
    return permissions_info_msg


# API 23 and have runtime permissions
def _get_permissions_info_above_api_23(app_info_dump):
    requested_permissions_regex = \
        re.search('requested permissions:(.*?)install permissions:', app_info_dump, re.IGNORECASE | re.DOTALL)
    if requested_permissions_regex is None:
        requested_permissions_regex = re.search('requested permissions:(.*?)runtime permissions:', app_info_dump,
                                                re.IGNORECASE | re.DOTALL)
    if requested_permissions_regex is None:
        requested_permissions = []  # No permissions requested by the app.
    else:
        requested_permissions = requested_permissions_regex.group(1).split('\n')
    install_time_permissions_regex = re.search('install permissions:(.*?)runtime permissions:', app_info_dump,
                                               re.IGNORECASE | re.DOTALL)
    if install_time_permissions_regex is None:
        install_time_permissions_string = []
    else:
        install_time_permissions_string = install_time_permissions_regex.group(1).split('\n')
    # Remove empty entries
    requested_permissions = list(filter(None, requested_permissions))
    install_time_permissions_string = filter(None, install_time_permissions_string)
    install_time_granted_permissions = []
    install_time_denied_permissions = []  # This will most likely remain empty
    for permission_string in install_time_permissions_string:
        if permission_string.find('granted=true') >= 0:
            permission, _ = permission_string.split(':')
            install_time_granted_permissions.append(permission)
        elif permission_string.find('granted=false') >= 0:
            permission, _ = permission_string.split(':')
            install_time_denied_permissions.append(permission)
    runtime_denied_permissions = []
    runtime_granted_permissions = []
    for permission in requested_permissions:
        if permission in install_time_granted_permissions or permission in install_time_denied_permissions:
            continue
        granted_pattern = '%s: granted=true' % permission
        denied_pattern = '%s: granted=false' % permission
        if app_info_dump.find(granted_pattern) >= 0:
            runtime_granted_permissions.append(permission)
        elif app_info_dump.find(denied_pattern) >= 0:
            runtime_denied_permissions.append(permission)
    runtime_not_granted_permissions = list(filter(
        lambda p: p not in runtime_granted_permissions and
                  p not in runtime_denied_permissions and
                  p not in install_time_granted_permissions and
                  p not in install_time_denied_permissions, requested_permissions))

    permissions_info_msg = ''
    permissions_info_msg += '\nPermissions:\n\n'
    if install_time_granted_permissions:
        permissions_info_msg += 'Install time granted permissions:\n%s\n\n' % '\n'.join(
            install_time_granted_permissions)
    if install_time_denied_permissions:
        permissions_info_msg += 'Install time denied permissions:\n%s\n\n' % '\n'.join(
            install_time_denied_permissions)
    if runtime_granted_permissions:
        permissions_info_msg += 'Runtime granted permissions:\n%s\n\n' % '\n'.join(
            runtime_granted_permissions)
    if runtime_denied_permissions:
        permissions_info_msg += 'Runtime denied permissions:\n%s\n\n' % '\n'.join(
            runtime_denied_permissions)
    if runtime_not_granted_permissions:
        permissions_info_msg += 'Runtime Permissions not granted and not yet requested:\n%s\n\n' % '\n'.join(
            runtime_not_granted_permissions)
    return permissions_info_msg


def _get_apk_path(app_name):
    adb_shell_cmd = 'pm path %s' % app_name
    result = execute_adb_shell_command(adb_shell_cmd)
    apk_path = result.split(':', 2)[1]
    return apk_path


@ensure_package_exists
def print_app_path(app_name):
    apk_path = _get_apk_path(app_name)
    print_verbose('Path for %s is %s' % (app_name, apk_path))
    print_message(apk_path)


@ensure_package_exists
def print_app_signature(app_name):
    apk_path = _get_apk_path(app_name)
    # Copy apk to a temp file on the disk
    with tempfile.NamedTemporaryFile(prefix=app_name, suffix='.apk') as tmp_apk_file:
        tmp_apk_file_name = tmp_apk_file.name
        adb_cmd = 'pull %s %s' % (apk_path, tmp_apk_file_name)
        return_code, _, stderr = execute_adb_command2(adb_cmd)
        if return_code != 0:
            print_error_and_exit('Failed to pull file %s, stderr: %s' % (apk_path, stderr))
            return

        dir_of_this_script = os.path.split(__file__)[0]
        apk_signer_jar_path = os.path.join(dir_of_this_script, 'apksigner.jar')
        if not os.path.exists(apk_signer_jar_path):
            print_error_and_exit('apksigner.jar is missing, your adb-enhanced installation is corrupted')

        print_signature_cmd = 'java -jar %s verify --print-certs %s' % (apk_signer_jar_path, tmp_apk_file_name)
        print_verbose('Executing command %s' % print_signature_cmd)
        with subprocess.Popen(print_signature_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as ps1:
            for line in ps1.stdout:
                line = line.decode('utf-8').strip()
                print_message(line)
            for line in ps1.stderr:
                line = line.decode('utf-8').strip()
                print_error(line)


# Uses abe.jar taken from https://sourceforge.net/projects/adbextractor/
@ensure_package_exists
def perform_app_backup(app_name, backup_tar_file):
    # TODO: Add a check to ensure that the screen is unlocked
    password = '00'
    print_verbose('Performing backup to backup.ab file')
    print_message(
        'you might have to confirm the backup manually on your device\'s screen, enter \"%s\" as password...' % password)

    def backup_func():
        # Create backup.ab
        adb_backup_cmd = 'backup -noapk %s' % app_name
        execute_adb_command2(adb_backup_cmd)

    backup_thread = threading.Thread(target=backup_func)
    backup_thread.start()
    while _get_top_activity_data()[1].find('com.android.backupconfirm') == -1:
        print_verbose('Waiting for the backup activity to start')
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
        print_error('Backup failed in first attempt, trying again...')
        # _perform_tap(window_size_x - 200, window_size_y - 100)
        backup_thread.join(timeout=10)
        if backup_thread.is_alive():
            print_error_and_exit('Backup failed')

    # Convert ".ab" to ".tar" using Android Backup Extractor (ABE)
    try:
        dir_of_this_script = os.path.split(__file__)[0]
        abe_jar_path = os.path.join(dir_of_this_script, 'abe.jar')
        if not os.path.exists(abe_jar_path):
            print_error_and_exit('Abe.jar is missing, your adb-enhanced installation is corrupted')
        abe_cmd = 'java -jar %s unpack backup.ab %s %s' % (abe_jar_path, backup_tar_file, password)
        print_verbose('Executing command %s' % abe_cmd)
        with subprocess.Popen(abe_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as ps:
            ps.communicate()
            if ps.returncode == 0:
                print_message('Successfully backed up data of app %s to %s' % (app_name, backup_tar_file))
            else:
                print_error('Failed to convert backup.ab to tar file. Please ensure that it is not password protected')
    finally:
        print_verbose('Deleting backup.ab')
        with subprocess.Popen('rm backup.ab', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as ps2:
            ps2.communicate()


def perform_install(file_path):
    print_verbose('Installing %s' % file_path)
    # -r: replace existing application
    return_code, _, stderr = execute_adb_command2('install -r %s' % file_path)
    if return_code != 0:
        print_error('Failed to install %s, stderr: %s' % (file_path, stderr))


@ensure_package_exists
def perform_uninstall(app_name, first_user):
    print_verbose('Uninstalling %s' % app_name)
    cmd = ""
    if first_user:
        # For system apps, that cannot uninstalled,
        # this command uninstalls them for user 0 without doing a system uninstall
        # since that would fail.
        # https://www.xda-developers.com/uninstall-carrier-oem-bloatware-without-root-access/
        cmd = "--user 0"
    return_code, _, stderr = execute_adb_shell_command2('pm uninstall %s %s' % (cmd, app_name))
    if return_code == 0:
        return

    if not cmd:
        print_message("Uninstall failed, trying to uninstall for user 0...")
        cmd = "--user 0"
        return_code, _, stderr = execute_adb_shell_command2('pm uninstall %s %s' % (cmd, app_name))

    if return_code != 0:
        print_error('Failed to uninstall %s, stderr: %s' % (app_name, stderr))


def _get_window_size():
    adb_cmd = 'shell wm size'
    _, result, _ = execute_adb_command2(adb_cmd)

    if result is None:
        return -1, -1

    regex_data = re.search('size: ([0-9]+)x([0-9]+)', result)
    if regex_data is None:
        return -1, -1

    return int(regex_data.group(1)), int(regex_data.group(2))


def _perform_tap(x, y):
    adb_shell_cmd = 'input tap %d %d' % (x, y)
    execute_adb_shell_command2(adb_shell_cmd)


# Deprecated
def execute_adb_shell_settings_command(settings_cmd, device_serial=None):
    _error_if_min_version_less_than(19, device_serial=device_serial)
    return execute_adb_shell_command('settings %s' % settings_cmd, device_serial=device_serial)


def execute_adb_shell_settings_command2(settings_cmd, device_serial=None):
    _error_if_min_version_less_than(19)
    return execute_adb_shell_command2('settings %s' % settings_cmd, device_serial)


def execute_adb_shell_settings_command_and_poke_activity_service(settings_cmd):
    return_value = execute_adb_shell_settings_command(settings_cmd)
    _poke_activity_service()
    return return_value


def execute_adb_shell_command_and_poke_activity_service(adb_cmd):
    return_value = execute_adb_shell_command(adb_cmd)
    _poke_activity_service()
    return return_value


def _poke_activity_service():
    return execute_adb_shell_command(get_update_activity_service_cmd())


def _error_if_min_version_less_than(min_acceptable_version, device_serial=None):
    api_version = get_device_android_api_version(device_serial)
    if api_version < min_acceptable_version:
        cmd = ' '.join(sys.argv[1:])
        print_error_and_exit(
            '\"%s\" can only be executed on API %d and above, your device version is %d' %
            (cmd, min_acceptable_version, api_version))


def _is_emulator():
    qemu = get_adb_shell_property('ro.kernel.qemu')
    return qemu is not None and qemu.strip() == '1'


def enable_wireless_debug():
    code, result, stderr = execute_adb_shell_command2("ip address")
    if code != 0:
        print_error_and_exit('Failed to switch device to wireless debug mode, stderr: '
                             '%s' % stderr)

    # Check, that phone connected to wlan
    matching = re.findall(r"inet ([\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}).*wlan0$",
                          result, re.MULTILINE)
    if matching is None or not matching:
        print_error_and_exit('Failed to switch device to wireless debug mode')

    ip = matching[0]

    code, _, stderr = execute_adb_command2("tcpip 5555")
    if code != 0:
        print_error_and_exit('Failed to switch device %s to wireless debug mode, '
                             'stderr: %s' % (ip, stderr))

    code, _, stderr = execute_adb_command2("connect %s" % ip)
    if code != 0:
        print_error_and_exit('Cannot enable wireless debugging. Error: %s' % stderr)
        return False
    print_message('Connected via IP now you can disconnect the cable\nIP: %s' % ip)
    return True


def disable_wireless_debug():
    device_serials = _get_device_serials()

    if not device_serials:
        print_error_and_exit('No connected device found')
        return

    ip_list = []
    for device_serial in device_serials:
        ips = re.findall(r"([\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}:[\d]{1,5})", device_serial, 0)
        if not ips:
            print_verbose('Not a IP connect device, serial: %s' % device_serial)
            continue
        if len(ips) > 1:
            print_error('Malformed device IP: %s' % device_serial)
        print_verbose('Found an IP connected ADB session: %s' % ips[0])
        ip_list.append(ips[0])

    result = True

    for ip in ip_list:
        code, _, stderr = execute_adb_command2('disconnect %s' % ip)
        if code != 0:
            print_error('Failed to disconnect %s: %s' % (ip, stderr))
            result = False
        else:
            print_message('Disconnected %s' % ip)

    if not result:
        print_error_and_exit('')


def switch_screen(switch_type):
    if switch_type == SCREEN_TOGGLE:
        c, o, e = toggle_screen()

        if c != 0:
            print_error_and_exit("Something gone wrong on "
                                 "screen control operation. Error: %s" % e)
        return o

    c, o, e = execute_adb_shell_command2("dumpsys display")
    if c != 0:
        print_error_and_exit("Something gone wrong on "
                             "screen control operation. Error: %s" % e)

    state = re.findall(r"^\s*mScreenState=(\w*)$", o, re.MULTILINE)[0]

    if (state == "ON" and switch_type == SCREEN_OFF) or \
            (state in ["OFF", "DOZE"] and switch_type == SCREEN_ON):
        c, o, e = toggle_screen()

        if c != 0:
            print_error_and_exit("Something gone wrong on "
                                 "screen control operation. Error: %s" % e)

    return o


def get_dark_mode() -> str:
    _error_if_min_version_less_than(_MIN_API_FOR_DARK_MODE)
    return_code, stdout, stderr = execute_adb_shell_settings_command2('get secure ui_night_mode')
    if return_code != 0:
        print_error('Failed to get current UI mode: %s' % stderr)
        return _USER_PRINT_VALUE_UNKNOWN
    if stdout == 'null':
        return _USER_PRINT_VALUE_UNKNOWN
    val = int(stdout)
    if val == 2:
        return _USER_PRINT_VALUE_ON
    elif val == 1:
        return _USER_PRINT_VALUE_OFF
    elif val == 0:
        return _USER_PRINT_VALUE_AUTO
    else:
        return 'Unknown: %d' % val


# This code worked for emulator on API 29.
# It didn't work for unrooted device on API 30.
# I am not sure if the problem is rooting or API version
def set_dark_mode(force: bool) -> None:
    """
    :param force: if true, force dark mode, if false don't
    """
    _error_if_min_version_less_than(_MIN_API_FOR_DARK_MODE)

    if force:
        # Ref: https://twitter.com/petedoyle_/status/1502008461080490006
        execute_adb_shell_command2('cmd uimode night yes')
        # There are reports of the following command, it didn't work for me
        # even on a rooted device when ran as a super-user
        # execute_adb_shell_command2('setprop persist.hwui.force_dark true')
    else:
        execute_adb_shell_command2('cmd uimode night no')


def print_notifications():
    # Noredact is required on Android >= 6.0 to see title and text
    code, output, err = execute_adb_shell_command2("dumpsys notification --noredact")
    if code != 0:
        print_error_and_exit("Something gone wrong on "
                             "fetching notification info. Error: %s" % err)
    notification_records = re.findall(r"\s*NotificationRecord\(.*", output, re.MULTILINE)
    for i, notification_record in enumerate(notification_records):
        output_for_this_notification = output.split(notification_record)[1]
        if i + 1 < len(notification_records):
            output_for_this_notification = output_for_this_notification.split(notification_records[i + 1])[0]
        notification_package = re.findall(r"pkg=(\S*)", notification_record)[0]
        titles = re.findall("android.title=(.*)", output_for_this_notification)
        if len(titles) > 0:
            notification_title = titles[0]
        else:
            notification_title = None
        texts = re.findall("android.text=(.*)", output_for_this_notification)
        if len(texts) > 0:
            notification_text = texts[0]
        else:
            notification_text = None
        notification_actions = []
        action_strings = re.findall(r"actions=\{(.*?)\n\}", output_for_this_notification, re.MULTILINE | re.DOTALL)
        if len(action_strings) > 0 and (i + 1 >= len(notification_records) or
                                        output_for_this_notification.find(
                                            action_strings[0]) > output_for_this_notification.find(
                    notification_records[i + 1])):
            for actions in action_strings[0].split('\n'):
                notification_actions += re.findall(r"\".*?\"", actions)

        print_message('Package: %s' % notification_package)
        if notification_title:
            print_message('Title: %s' % notification_title)
        if notification_text and notification_text != 'null':
            print_message('Text: %s' % notification_text)
        for action in notification_actions:
            print_message('Action: %s' % action)
        print_message('')


# Alarm Enum
class AlarmEnum(Enum):
    TOP = 't'
    PENDING = 'p'
    HISTORY = 'h'
    ALL = 'a'


def print_history_alarms(output_dump_alarm, padding):
    print("App Alarm history")

    pattern_pending_alarm = \
        re.compile(r'(?<=App Alarm history:)'
                   r'.*?(?=Past-due non-wakeup alarms)',
                   re.DOTALL)
    alarm_to_parse = re.sub(r' +', ' ',
                            re.search(pattern_pending_alarm, output_dump_alarm).
                            group(0)).split("\n")[1:-1]

    for line in alarm_to_parse:
        package_name = line[0:line.find(",")]
        # +1 to escape ',' before user id
        fields = line[line.find(",") + 1:].split(":")
        user_id = fields[0]
        print("%sPackage name: %s" % (padding, package_name))
        print("%sUser ID: %s" % (padding * 2, user_id))
        # History might be missing for new alarms
        if len(fields) >= 2:
            history = fields[1]
            print("%shistory: %s" % (padding * 2, history))


def print_top_alarms(output_dump_alarm, padding):
    print("Top Alarms:")
    pattern_top_alarm = re.compile(r'(?<=Top Alarms:\n).*?(?=Alarm Stats:)',
                                   re.DOTALL)
    alarm_to_parse = re.sub(
        r' +', ' ',
        re.search(pattern_top_alarm, output_dump_alarm).group(0)).split("\n")
    temp_dict = {}
    for i, alarm_i in enumerate(alarm_to_parse):
        if re.match(r"^\+", alarm_i):
            temp_dict[alarm_i] = alarm_to_parse[i + 1]
            i += 1

    for key, value in temp_dict.items():
        # key example: +2m19s468ms running, 0 wakeups, 708 alarms: 1000:android
        # value example: *alarm*:com.android.server.action.NETWORK_STATS_POLL
        temp = key.split(',')
        running_time = temp[0].split(" ")[0]
        nb_woke_up = temp[1].strip().split(" ")[0]
        nb_alarms = temp[2].strip().split(" ")[0]
        uid = temp[2].strip().split(":")[1].strip()
        package_name = temp[2].strip().split(":")[2].strip()
        action = value.split(":")[1]
        print("%sPackage name: %s" % (padding, package_name))
        print("%sAction: %s" % (padding * 2, action))
        print("%sRunning time: %s" % (padding * 2, running_time))
        print("%sNumber of device woke up: %s" % (padding * 2, nb_woke_up))
        print("%sNumber of alarms: %s" % (padding * 2, nb_alarms))
        print("%sUser ID: %s" % (padding * 2, uid))


def print_pending_alarms(output_dump_alarm, padding):
    print("Pending Alarms:")
    pattern_pending_alarm = \
        re.compile(
            r'(?<=Pending alarm batches:)'
            r'.*?(?=(Pending user blocked background alarms|Past-due non-wakeup alarms))',
            re.DOTALL)
    alarm_to_parse = re.sub(
        r' +', ' ',
        re.search(pattern_pending_alarm, output_dump_alarm).group(0)).split("\n")[1:-1]
    for line in alarm_to_parse:
        line = line.strip()
        if not line.startswith("Batch"):
            continue

        pattern_batch_info = re.compile(r'(?<=Batch\{).*?(?=\}:)',
                                        re.DOTALL)
        info = re.search(pattern_batch_info, line).group(0).split(" ")
        print("%sID: %s" % (padding, info[0]))
        print("%sNumber of alarms: %s" % (padding * 2, info[1].split("=")[1]))
        print_verbose("%sStart: %s" % (padding * 2, info[2].split("=")[1]))
        print_verbose("%sEnd: %s" % (padding * 2, info[3].split("=")[1]))
        if "flgs" in line:
            # TO-DO: translate the flags
            print_verbose("%sflag: %s" % (padding * 2, info[4].split("=")[1]))

        if line.startswith("RTC") or line.startswith("RTC_WAKEUP") or \
                line.startswith("ELAPSED") or line.startswith("ELAPSED_WAKEUP"):
            pattern_between_brackets = re.compile(r'(?<=\{).*?(?=\})',
                                                  re.DOTALL)
            info = re.search(pattern_between_brackets, line).group(0).split(" ")
            print("%sAlarm #%s:" % (padding * 2, line.split("#")[1].split(":")[0]))
            print_verbose("%sType: %s" % (padding * 2, line.split("#")[0]))
            print_verbose("%sID: %s" % (padding * 2, info[0]))
            print_verbose("%sType: %s" % (padding * 2, info[2]))
            print_verbose("%sWhen: %s" % (padding * 2, info[4]))
            print("%sPackage: %s" % (padding * 2, info[5]))


def alarm_manager(param):
    cmd = "dumpsys alarm"
    api_version = get_device_android_api_version()
    err_msg_api = "Your Android version (API 28 and bellow) does not support " \
                  "listing pending alarm"

    c, o, e = execute_adb_shell_command2(cmd)
    if c != 0:
        print_error_and_exit("Something gone wrong on "
                             "dumping alarms. Error: %s" % e)
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
        print_top_alarms(o, padding)

    if param == AlarmEnum.PENDING or run_all == 1:
        if api_version > 28:
            print_pending_alarms(o, padding)
        else:
            print_error(err_msg_api)

    if param == AlarmEnum.HISTORY or run_all == 1:
        if api_version > 28:
            print_history_alarms(o, padding)
        else:
            print_error(err_msg_api)


def toggle_location(turn_on):
    _error_if_min_version_less_than(_MIN_API_FOR_LOCATION)
    if turn_on:
        cmd = 'put secure location_mode 3'
    else:
        cmd = 'put secure location_mode 0'
    execute_adb_shell_settings_command(cmd)

# This permissions group seems to have been removed in API 29 and beyond.
# https://github.com/ashishb/adb-enhanced/runs/1799363523?check_suite_focus=true
def is_permission_group_unavailable_after_api_29(permission_group):
    return permission_group in [
        'android.permission-group.CONTACTS',
        'android.permission-group.MICROPHONE',
        'android.permission-group.LOCATION',
        'android.permission-group.SMS',
    ]


def print_state_change_info(state_name, old_state, new_state):
    if old_state != new_state:
        print_message('"%s" state changed from "%s" -> "%s"' % (
            state_name, old_state, new_state))
    else:
        print_message('"%s" state unchanged (%s)' % (state_name, old_state))
