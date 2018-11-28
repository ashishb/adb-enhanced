#!/usr/bin/python

# Python 2 and 3, print compatibility
from __future__ import print_function
# Without this urllib.parse which is python 3 only cannot be accessed in python 2.
from future.standard_library import install_aliases
install_aliases()

import docopt
import psutil
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
import os
import random
# This is required only for Python 2
# pylint: disable=import-error
from urllib.parse import urlparse

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
    from adbe import adb_helper
    from adbe import output_helper
    from adbe.adb_helper import execute_adb_command, execute_adb_shell_command
    from adbe.output_helper import print_message, print_error, print_error_and_exit, print_verbose
except ImportError:
    # This works when the code is executed directly.
    import adb_helper
    import output_helper
    from adb_helper import execute_adb_command, execute_adb_shell_command
    from output_helper import print_message, print_error, print_error_and_exit, print_verbose


# List of things which this enhanced adb tool does as of today.
USAGE_STRING = """
Swiss-army knife for Android testing and development.

Usage:
    adbe [options] rotate (landscape | portrait | left | right)
    adbe [options] gfx (on | off | lines)
    adbe [options] overdraw (on | off | deut)
    adbe [options] layout (on | off)
    adbe [options] airplane (on | off)
    adbe [options] battery level <percentage>
    adbe [options] battery saver (on | off)
    adbe [options] battery reset
    adbe [options] doze (on | off)
    adbe [options] jank <app_name>
    adbe [options] devices
    adbe [options] top-activity
    adbe [options] dump-ui <xml_file>
    adbe [options] mobile-data (on | off)
    adbe [options] mobile-data saver (on | off)
    adbe [options] rtl (on | off)
    adbe [options] screenshot <filename.png>
    adbe [options] screenrecord <filename.mp4>
    adbe [options] dont-keep-activities (on | off)
    adbe [options] animations (on | off)
    adbe [options] show-taps (on | off)
    adbe [options] stay-awake-while-charging (on | off) 
    adbe [options] input-text <text>
    adbe [options] press back
    adbe [options] open-url <url>
    adbe [options] permission-groups list all
    adbe [options] permissions list (all | dangerous)
    adbe [options] permissions (grant | revoke) <app_name> (calendar | camera | contacts | location | microphone | phone | sensors | sms | storage)
    adbe [options] apps list (all | system | third-party | debug | backup-enabled)
    adbe [options] standby-bucket get <app_name>
    adbe [options] standby-bucket set <app_name> (active | working_set | frequent | rare)
    adbe [options] restrict-background (true | false) <app_name>
    adbe [options] ls [-a] [-l] [-R|-r] <file_path>
    adbe [options] rm [-f] [-R|-r] <file_path>
    adbe [options] mv [-f] <src_path> <dest_path>
    adbe [options] pull [-a] <file_path_on_android>
    adbe [options] pull [-a] <file_path_on_android> <file_path_on_machine>
    adbe [options] push <file_path_on_machine> <file_path_on_android>
    adbe [options] cat <file_path>
    adbe [options] start <app_name>
    adbe [options] stop <app_name>
    adbe [options] restart <app_name>
    adbe [options] force-stop <app_name>
    adbe [options] clear-data <app_name>
    adbe [options] app info <app_name>
    adbe [options] app path <app_name>
    adbe [options] app signature <app_name>
    adbe [options] app backup <app_name> [<backup_tar_file_path>]
    adbe [options] install <file_path>
    adbe [options] uninstall <app_name>

Options:
    -e, --emulator          directs the command to the only running emulator
    -d, --device            directs the command to the only connected "USB" device
    -s, --serial SERIAL     directs the command to the device or emulator with the given serial number or qualifier.
                            Overrides ANDROID_SERIAL environment variable.
    -l                      For long list format, only valid for "ls" command
    -R                      For recursive directory listing, only valid for "ls" and "rm" command
    -r                      For delete file, only valid for "ls" and "rm" command
    -f                      For forced deletion of a file, only valid for "rm" command
    -v, --verbose           Verbose mode
    --no-python2-warn       Don't warn about Python 2 deprecation

"""

"""
List of things which this tool will do in the future

* adbe b[ack]g[round-]c[ellular-]d[ata] [on|off] $app_name # This might not be needed at all after mobile-data saver mode
* adbe app-standby $app_name
* adbe wifi [on|off]  # svc wifi enable/disable does not seem to always work
* adbe rtl (on | off)  # adb shell settings put global debug.force_rtl 1 does not seem to work
* adbe screen (on|off|toggle)  # https://stackoverflow.com/questions/7585105/turn-on-screen-on-device
* adb shell input keyevent KEYCODE_POWER can do the toggle
* adbe press up
* adbe set_app_name [-f] $app_name
* adbe reset_app_name
* Use -q[uite] for quite mode
* Add IMEI, IMSI, phone number, and WI-Fi MAC address to devices info command - I think the best way to implement this
  will be via a companion app. And while we are on that, we can implement locale change via the companion app as well.

"""


_VERSION_FILE_NAME = 'version.txt'
_KEYCODE_BACK = 4
_MIN_API_FOR_RUNTIME_PERMISSIONS = 23


def main():
    args = docopt.docopt(USAGE_STRING, version=get_version())

    validate_options(args)
    options = ''
    if args['--emulator']:
        options += '-e '
    if args['--device']:
        options += '-d '
    if args['--serial']:
        options += '-s %s ' % args['--serial']
    if _using_python2() and not args['--no-python2-warn']:
        _warn_about_python2_deprecation()

    output_helper.set_verbose(args['--verbose'])

    if len(options) > 0:
        adb_prefix = '%s %s' % (adb_helper.get_adb_prefix(), options)
        adb_helper.set_adb_prefix(adb_prefix)

    if args['rotate']:
        direction = None
        if args['portrait']:
            direction = 'portrait'
        elif args['landscape']:
            direction = 'landscape'
        elif args['left']:
            direction = 'left'
        elif args['right']:
            direction = 'right'
        else:
            print_error_and_exit('Unexpected rotation direction "%s"' % ' '.join(sys.argv))
        handle_rotate(direction)
    elif args['gfx']:
        value = 'on' if args['on'] else \
            ('off' if args['off'] else
             'lines')
        handle_gfx(value)
    elif args['overdraw']:
        value = 'on' if args['on'] else \
            ('off' if args['off'] else
             'deut')
        handle_overdraw(value)
    elif args['layout']:
        value = args['on']
        handle_layout(value)
    elif args['airplane']:
        # This does not always work
        value = args['on']
        handle_airplane(value)
    elif args['battery']:
        if args['saver']:
            handle_battery_saver(args['on'])
        elif args['level']:
            handle_battery_level(int(args['<percentage>']))
        elif args['reset']:
            handle_battery_reset()
    elif args['doze']:
        handle_doze(args['on'])
    elif args['jank']:
        app_name = args['<app_name>']
        _ensure_package_exists(app_name)
        handle_get_jank(app_name)
    elif args['devices']:
        handle_list_devices()
    elif args['top-activity']:
        print_top_activity()
    elif args['dump-ui']:
        dump_ui(args['<xml_file>'])
    elif args['force-stop']:
        app_name = args['<app_name>']
        _ensure_package_exists(app_name)
        force_stop(app_name)
    elif args['clear-data']:
        app_name = args['<app_name>']
        _ensure_package_exists(app_name)
        clear_disk_data(app_name)
    elif args['mobile-data']:
        if args['saver']:
            handle_mobile_data_saver(args['on'])
        else:
            handle_mobile_data(args['on'])
    elif args['rtl']:
        # This is not working as expected
        force_rtl(args['on'])
    elif args['screenshot']:
        dump_screenshot(args['<filename.png>'])
    elif args['screenrecord']:
        dump_screenrecord(args['<filename.mp4>'])
    elif args['dont-keep-activities']:
        handle_dont_keep_activities_in_background(args['on'])
    elif args['animations']:
        toggle_animations(args['on'])
    elif args['show-taps']:
        toggle_show_taps(turn_on=args['on'])
    elif args['stay-awake-while-charging']:
        # Keep screen on while the device is charging.
        stay_awake_while_charging(args['on'])
    elif args['input-text']:
        input_text(args['<text>'])
    elif args['back']:
        press_back()
    elif args['open-url']:
        url = args['<url>']
        open_url(url)
    elif args['permission-groups'] and args['list'] and args['all']:
        list_permission_groups()
    elif args['permissions'] and args['list']:
        list_permissions(args['dangerous'])
    elif args['permissions']:
        android_api_version = _get_device_android_api_version()
        if android_api_version < _MIN_API_FOR_RUNTIME_PERMISSIONS:
            print_error_and_exit(
                'Runtime permissions are supported only on API %d and above, your version is %d' %
                (_MIN_API_FOR_RUNTIME_PERMISSIONS, android_api_version))
        app_name = args['<app_name>']
        _ensure_package_exists(app_name)
        permission_group = get_permission_group(args)
        permissions = get_permissions_in_permission_group(permission_group)
        if not permissions:
            print_error_and_exit('No permissions found in permissions group: %s' % permission_group)
        grant_or_revoke_runtime_permissions(
            app_name, args['grant'], permissions)
    elif args['apps'] and args['list']:
        if args['all']:
            list_all_apps()
        elif args['system']:
            list_system_apps()
        elif args['third-party']:
            list_non_system_apps()
        elif args['debug']:
            list_debug_apps()
        elif args['backup-enabled']:
            list_allow_backup_apps()
    elif args['standby-bucket']:
        app_name = args['<app_name>']
        _ensure_package_exists(app_name)
        if args['get']:
            get_standby_bucket(app_name)
        elif args['set']:
            set_standby_bucket(app_name, _calculate_standby_mode(args))
    elif args['restrict-background']:
        app_name = args['<app_name>']
        _ensure_package_exists(app_name)
        apply_or_remove_background_restriction(app_name, args['true'])
    elif args['ls']:
        file_path = args['<file_path>']
        long_format = args['-l']
        # Always include hidden files, -a is left for backward-compatibility but is a no-op now.
        include_hidden_files = True
        recursive = args['-R'] or args['-r']
        list_directory(file_path, long_format, recursive, include_hidden_files)
    elif args['rm']:
        file_path = args['<file_path>']
        force_delete = args['-f']
        recursive = args['-R'] or args['-r']
        delete_file(file_path, force_delete, recursive)
    elif args['mv']:
        src_path = args['<src_path>']
        dest_path = args['<dest_path>']
        force_move = args['-f']
        move_file(src_path, dest_path, force_move)
    elif args['pull']:
        remote_file_path = args['<file_path_on_android>']
        local_file_path = args['<file_path_on_machine>']
        copy_ancillary = args['-a']
        pull_file(remote_file_path, local_file_path, copy_ancillary)
    elif args['push']:
        remote_file_path = args['<file_path_on_android>']
        local_file_path = args['<file_path_on_machine>']
        push_file(local_file_path, remote_file_path)
    elif args['cat']:
        file_path = args['<file_path>']
        cat_file(file_path)
    elif args['start']:
        app_name = args['<app_name>']
        _ensure_package_exists(app_name)
        launch_app(app_name)
    elif args['stop']:
        app_name = args['<app_name>']
        _ensure_package_exists(app_name)
        stop_app(app_name)
    elif args['restart']:
        app_name = args['<app_name>']
        _ensure_package_exists(app_name)
        force_stop(app_name)
        launch_app(app_name)
    elif args['app']:
        app_name = args['<app_name>']
        _ensure_package_exists(app_name)
        if args['info']:
            print_app_info(app_name)
        elif args['path']:
            print_app_path(app_name)
        elif args['signature']:
            print_app_signature(app_name)
        elif args['backup']:
            backup_tar_file_path = args['<backup_tar_file_path>']
            if not backup_tar_file_path:
                backup_tar_file_path = '%s_backup.tar' % app_name
            perform_app_backup(app_name, backup_tar_file_path)
    elif args['install']:
        file_path = args['<file_path>']
        perform_install(file_path)
    elif args['uninstall']:
        app_name = args['<app_name>']
        perform_uninstall(app_name)
    else:
        print_error_and_exit('Not implemented: "%s"' % ' '.join(sys.argv))


def validate_options(args):
    count = 0
    if args['--emulator']:
        count += 1
    if args['--device']:
        count += 1
    if args['--serial']:
        count += 1
    if count > 1:
        print_error_and_exit('Only one out of -e, -d, or -s can be provided')


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
    version = _get_device_android_api_version()
    if version < 19:
        if value is 'on':
            cmd = 'setprop debug.hwui.show_overdraw true'
        elif value is 'off':
            cmd = 'setprop debug.hwui.show_overdraw false'
        elif value is 'deut':
            print_error_and_exit(
                'This command is not support on API %d' % version)
        else:
            print_error_and_exit('Unexpected value for overdraw %s' % value)
    else:
        if value is 'on':
            cmd = 'setprop debug.hwui.overdraw show'
        elif value is 'off':
            cmd = 'setprop debug.hwui.overdraw false'
        elif value is 'deut':
            cmd = 'setprop debug.hwui.overdraw show_deuteranomaly'
        else:
            print_error_and_exit('Unexpected value for overdraw %s' % value)
            return

    execute_adb_shell_command_and_poke_activity_service(cmd)


def get_version():
    dir_of_this_script = os.path.split(__file__)[0]
    version_file_path = os.path.join(dir_of_this_script, _VERSION_FILE_NAME)
    with open(version_file_path, 'r') as fh:
        return fh.read().strip()


# Perform screen rotation. Accepts four direction types - left, right, portrait, and landscape.
# Source:
# https://stackoverflow.com/questions/25864385/changing-android-device-orientation-with-adb
def handle_rotate(direction):
    disable_acceleration = 'put system accelerometer_rotation 0'
    execute_adb_shell_settings_command(disable_acceleration)

    if direction is 'portrait':
        new_direction = 0
    elif direction is 'landscape':
        new_direction = 1
    elif direction is 'left':
        current_direction = get_current_rotation_direction()
        print_verbose("Current direction: %s" % current_direction)
        if current_direction is None:
            return
        new_direction = (current_direction + 1) % 4
    elif direction is 'right':
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

    broadcast_change = 'am broadcast -a android.intent.action.AIRPLANE_MODE'
    execute_adb_shell_settings_command(cmd)
    execute_adb_shell_command(broadcast_change)


# Source:
# https://stackoverflow.com/questions/28234502/programmatically-enable-disable-battery-saver-mode
def handle_battery_saver(turn_on):
    _error_if_min_version_less_than(19)
    if turn_on:
        cmd = 'put global low_power 1'
    else:
        cmd = 'put global low_power 0'

    execute_adb_shell_command(get_battery_unplug_cmd())
    execute_adb_shell_command(get_battery_discharging_cmd())
    execute_adb_shell_settings_command(cmd)


# Source:
# https://stackoverflow.com/questions/28234502/programmatically-enable-disable-battery-saver-mode
def handle_battery_level(level):
    _error_if_min_version_less_than(19)
    if level < 0 or level > 100:
        print_error_and_exit(
            'Battery percentage %d is outside the valid range of 0 to 100' %
            level)
    cmd = 'dumpsys battery set level %d' % level

    execute_adb_shell_command(get_battery_unplug_cmd())
    execute_adb_shell_command(get_battery_discharging_cmd())
    execute_adb_shell_command(cmd)


# Source:
# https://stackoverflow.com/questions/28234502/programmatically-enable-disable-battery-saver-mode
def handle_battery_reset():
    # The battery related commands fail silently on API 16. I am not sure about 17 and 18.
    _error_if_min_version_less_than(19)
    cmd = get_battery_reset_cmd()
    execute_adb_shell_command(cmd)


# https://developer.android.com/training/monitoring-device-state/doze-standby.html
def handle_doze(turn_on):
    _error_if_min_version_less_than(23)

    enable_idle_mode_cmd = 'dumpsys deviceidle enable'
    if turn_on:
        # Source: https://stackoverflow.com/a/42440619
        cmd = 'dumpsys deviceidle force-idle'
        execute_adb_shell_command(get_battery_unplug_cmd())
        execute_adb_shell_command(get_battery_discharging_cmd())
        execute_adb_shell_command(enable_idle_mode_cmd)
        execute_adb_shell_command(cmd)
    else:
        cmd = 'dumpsys deviceidle unforce'
        execute_adb_shell_command(get_battery_reset_cmd())
        execute_adb_shell_command(enable_idle_mode_cmd)
        execute_adb_shell_command(cmd)


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


def handle_get_jank(app_name):
    running = _is_app_running(app_name)
    if not running:
        # Jank information cannot be fetched unless the app is running
        print_verbose('Starting the app %s to get its jank information' % app_name)
        launch_app(app_name)

    try:
        cmd = 'dumpsys gfxinfo %s ' % app_name
        result = execute_adb_shell_command(cmd)
        print_verbose(result)
        found = False
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
    result = execute_adb_shell_command('ps -o NAME')
    if not result:
        return False
    result = result.strip()
    return result.find(app_name) != -1


def handle_list_devices():
    s1 = execute_adb_command('devices -l')
    # Skip the first line, it says "List of devices attached"
    device_infos = s1.split('\n')[1:]

    if len(device_infos) == 0 or (
            len(device_infos) == 1 and len(device_infos[0]) == 0):
        print_error_and_exit('No attached Android device found')
    elif len(device_infos) == 1:
        _print_device_info()
    else:
        for device_info in device_infos:
            if len(device_info) == 0:
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
                _print_device_info(device_serial)


def _print_device_info(device_serial=None):
    cmd_prefix = ''
    if device_serial is not None:
        cmd_prefix = '-s %s' % device_serial

    manufacturer = execute_adb_command(
        '%s shell getprop ro.product.manufacturer' %
        cmd_prefix)
    model = execute_adb_command(
        '%s shell getprop ro.product.model' %
        cmd_prefix)
    # This worked on 4.4.3 API 19 Moto E
    display_name = execute_adb_command(
        '%s shell getprop ro.product.display' %
        cmd_prefix)
    # First fallback: undocumented
    if display_name is None or len(display_name) == 0 or display_name == 'null':
        # This works on 4.4.4 API 19 Galaxy Grand Prime
        if _get_device_android_api_version() >= 19:
            display_name = execute_adb_command('%s shell settings get system device_name' % cmd_prefix)
    # Second fallback, documented to work on API 25 and above
    # Source: https://developer.android.com/reference/android/provider/Settings.Global.html#DEVICE_NAME
    if display_name is None or len(display_name) == 0 or display_name == 'null':
        if _get_device_android_api_version() >= 19:
            display_name = execute_adb_command('%s shell settings get global device_name' % cmd_prefix)

    # ABI info
    abi = execute_adb_command(
            '%s shell getprop ro.product.cpu.abi' % cmd_prefix)

    release = execute_adb_command(
        '%s shell getprop ro.build.version.release' %
        cmd_prefix)
    sdk = execute_adb_command(
        '%s shell getprop ro.build.version.sdk' %
        cmd_prefix)
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
    output = execute_adb_shell_command(cmd)
    if not output:
        print_error_and_exit('Device returned no response, is it still connected?')
    for line in output.split('\n'):
        line = line.strip()
        if line.startswith('mFocusedApp'):
            regex_result = re.search(r'ActivityRecord{.* (\S+)/(\S+)', line)
            if regex_result is None:
                print_error('Unable to parse activity name from:')
                print_error(line)
                return None, None
            app_name, activity_name = regex_result.group(1), regex_result.group(2)
            # If activity name is a short hand then complete it.
            if activity_name.startswith('.'):
                activity_name = '%s%s' %(app_name, activity_name)
            return app_name, activity_name

    return None, None

def dump_ui(xml_file):
    tmp_file = _create_tmp_file('dump-ui', 'xml')
    cmd1 = 'uiautomator dump %s' % tmp_file
    cmd2 = 'pull %s %s' % (tmp_file, xml_file)
    cmd3 = 'rm %s' % tmp_file

    print_verbose('Writing UI to %s' % tmp_file)
    execute_adb_shell_command(cmd1)
    print_verbose('Pulling file %s' % xml_file)
    execute_adb_command(cmd2)
    print_verbose('Deleting file %s' % tmp_file)
    print_message('XML UI dumped to %s, you might want to format it using \"xmllint --format %s\"' %
                  (xml_file, xml_file))
    execute_adb_shell_command(cmd3)


def force_stop(app_name):
    cmd = 'am force-stop %s' % app_name
    print_message(execute_adb_shell_command(cmd))


def clear_disk_data(app_name):
    cmd = 'pm clear %s' % app_name
    execute_adb_shell_command(cmd)


# Source:
# https://stackoverflow.com/questions/26539445/the-setmobiledataenabled-method-is-no-longer-callable-as-of-android-l-and-later
def handle_mobile_data(turn_on):
    if turn_on:
        cmd = 'svc data enable'
    else:
        cmd = 'svc data disable'
    execute_adb_shell_command(cmd)


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
    execute_adb_shell_command(dump_cmd)
    pull_cmd = 'pull %s %s' % (screenshot_file_path_on_device, filepath)
    execute_adb_command(pull_cmd)
    del_cmd = 'rm %s' % screenshot_file_path_on_device
    execute_adb_shell_command(del_cmd)


def dump_screenrecord(filepath):
    _error_if_min_version_less_than(19)
    api_version = _get_device_android_api_version()

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
        execute_adb_shell_command(dump_cmd)

    def _pull_and_delete_file_from_device():
        global screen_record_file_path_on_device
        print_message('Saving recording to %s' % filepath)
        pull_cmd = 'pull %s %s' % (screen_record_file_path_on_device, filepath)
        execute_adb_command(pull_cmd)
        del_cmd = 'rm %s' % screen_record_file_path_on_device
        execute_adb_shell_command(del_cmd)

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


# https://developer.android.com/training/basics/network-ops/data-saver.html
def handle_mobile_data_saver(turn_on):
    if turn_on:
        cmd = 'cmd netpolicy set restrict-background true'
    else:
        cmd = 'cmd netpolicy set restrict-background false'
    execute_adb_shell_command(cmd)


# Ref: https://github.com/android/platform_packages_apps_settings/blob/4ce19f5c4fd40f3bedc41d3fbcbdede8b2614501/src/com/android/settings/DevelopmentSettings.java#L2123
# adb shell settings put global always_finish_activities true might not work on all Android versions.
# It was in system (not global before ICS)
# adb shell service call activity 43 i32 1 followed by that
def handle_dont_keep_activities_in_background(turn_on):
    # Till Api 25, the value was True/False, above API 25, 1/0 work. Source: manual testing
    if _get_device_android_api_version() <= 25:
        use_true_false_as_value = True
    else:
        use_true_false_as_value = False

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


def toggle_show_taps(turn_on):
    if turn_on:
        value = 1
    else:
        value = 0

    # Source: https://stackoverflow.com/a/32621809/434196
    cmd = 'put system show_touches %d' % value
    execute_adb_shell_settings_command(cmd)


# Source: https://developer.android.com/reference/android/provider/Settings.Global.html#STAY_ON_WHILE_PLUGGED_IN
def stay_awake_while_charging(turn_on):
    if turn_on:
        # 1 for USB charging, 2 for AC charging, 4 for wireless charging. Or them together to get 7.
        value = 7
    else:
        value = 0

    cmd1 = 'put global stay_on_while_plugged_in %d' % value
    execute_adb_shell_settings_command_and_poke_activity_service(cmd1)


def input_text(text):
    cmd = 'input text %s' % text
    execute_adb_shell_command(cmd)


def press_back():
    cmd = 'input keyevent 4'
    execute_adb_shell_command(cmd)


def open_url(url):
    # Let's not do any URL encoding for now, if required, we will add that in the future.
    parsed_url = urlparse(url = url)
    if parsed_url.scheme is None or len(parsed_url.scheme) == 0:
        parsed_url2 = urlparse(url=url, scheme='http')
        url = parsed_url2.geturl()
    cmd = 'am start -a android.intent.action.VIEW -d %s' % url
    execute_adb_shell_command(cmd)


def list_permission_groups():
    cmd = 'pm list permission-groups'
    print_message(execute_adb_shell_command(cmd))


def list_permissions(dangerous_only_permissions):
    # -g is to group permissions by permission groups.
    if dangerous_only_permissions:
        # -d => dangerous only permissions
        cmd = 'pm list permissions -g -d'
    else:
        cmd = 'pm list permissions -g'
    print_message(execute_adb_shell_command(cmd))


def _ensure_package_exists(package_name):
    if not _package_exists(package_name):
        print_error_and_exit("Package %s does not exist" % package_name)


def _package_exists(package_name):
    cmd = 'pm path %s' % package_name
    response = execute_adb_shell_command(cmd)
    return response is not None and len(response.strip()) != 0


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
    execute_adb_shell_command('touch %s' % filepath_on_device)
    # Make the tmp file world-writable or else, run-as command might fail to write on it.
    execute_adb_shell_command('chmod 666 %s' % filepath_on_device)
    return filepath_on_device


# Returns true if the file_path exists on the device, false if it does not exists or is inaccessible.
def _file_exists(file_path):
    exists_cmd = "ls %s 1>/dev/null 2>/dev/null && echo exists" % file_path
    # The second command "echo exists" will not be wrapped with run-as but that's OK in this case.
    # Since it is perfectly fine to output "exists" as a shell user.
    exists_cmd = _may_be_wrap_with_run_as(exists_cmd, file_path)
    output = execute_adb_shell_command(exists_cmd)
    return output is not None and output.find('exists') != -1


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


# Pass the full-qualified permission group name to this method.
def get_permissions_in_permission_group(permission_group):
    # List permissions by group
    permission_output = execute_adb_shell_command('pm list permissions -g')
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
            print_message(
                'Permissions in %s group are %s' %
                (permission_group, permissions))
            return permissions


def grant_or_revoke_runtime_permissions(
        package_name, action_grant, permissions):
    if action_grant:
        cmd = 'pm grant %s' % package_name
    else:
        cmd = 'pm revoke %s' % package_name
    for permission in permissions:
        execute_adb_shell_command(cmd + ' ' + permission)


def _get_all_packages(pm_cmd):
    result = execute_adb_shell_command(pm_cmd)
    if result is None:
        print_error_and_exit('Empty output, something is wrong')
    packages = []
    for line in result.split('\n'):
        _, package_name = line.split(':', 2)
        packages.append(package_name)
    return packages


def list_all_apps():
    cmd = 'pm list packages'
    packages = _get_all_packages(cmd)
    print('\n'.join(packages))


def list_system_apps():
    cmd = 'pm list packages -s'
    packages = _get_all_packages(cmd)
    print('\n'.join(packages))


def list_non_system_apps():
    cmd = 'pm list packages -3'
    packages = _get_all_packages(cmd)
    print('\n'.join(packages))


def list_debug_apps():
    cmd = 'pm list packages'
    packages = _get_all_packages(cmd)

    if _ASYNCIO_AVAILABLE:
        method_to_call = _is_debug_package
        params_list = packages
        result_list = asyncio_helper.execute_in_parallel(method_to_call, params_list)
        debug_packages = []
        for (package_name, debuggable) in result_list:
            if debuggable:
                debug_packages.append(package_name)
        print('\n'.join(debug_packages))
    else:
        print_message('Use python3 for faster execution of this call')
        _list_debug_apps_no_async(packages)


def _list_debug_apps_no_async(packages):
    debug_packages = []
    count = 0
    num_packages = len(packages)
    for package in packages:
        count += 1
        print_verbose("Checking package: %d/%s" % (count, num_packages))
        # No faster way to do this except to check each and every package individually
        if _is_debug_package(package)[1]:
            debug_packages.append(package)
    print('\n'.join(debug_packages))


_REGEX_DEBUGGABLE = '(pkgFlags|flags).*DEBUGGABLE'


def _is_debug_package(app_name):
    pm_cmd = 'dumpsys package %s' % app_name
    grep_cmd = '(grep -c -E \'%s\' || true)' % _REGEX_DEBUGGABLE
    app_info_dump = execute_adb_shell_command(pm_cmd, piped_into_cmd=grep_cmd)
    if app_info_dump is None or app_info_dump.strip() == '0':
        return app_name, False
    elif app_info_dump.strip() == '1' or app_info_dump.strip() == '2':
        return app_name, True
    else:
        print_error_and_exit('Unexpected output for %s | %s = %s' % (pm_cmd, grep_cmd, app_info_dump))


def list_allow_backup_apps():
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
        print('\n'.join(debug_packages))
    else:
        print_message('Use python3 for faster execution of this call')
        _list_allow_backup_apps_no_async(packages)


def _list_allow_backup_apps_no_async(packages):
    debug_packages = []
    count = 0
    num_packages = len(packages)
    for package in packages:
        count += 1
        print_verbose("Checking package: %d/%s" % (count, num_packages))
        # No faster way to do this except to check each and every package individually
        if _is_allow_backup_package(package)[1]:
            debug_packages.append(package)
    print('\n'.join(debug_packages))


_REGEX_BACKUP_ALLOWED = '(pkgFlags|flags).*ALLOW_BACKUP'


def _is_allow_backup_package(app_name):
    pm_cmd = 'dumpsys package %s' % app_name
    grep_cmd = '(grep -c -E \'%s\' || true)' % _REGEX_BACKUP_ALLOWED
    app_info_dump = execute_adb_shell_command(pm_cmd, piped_into_cmd=grep_cmd)
    if app_info_dump is None or app_info_dump.strip() == '0':
        return app_name, False
    elif app_info_dump.strip() == '1' or app_info_dump.strip() == '2':
        return app_name, True
    else:
        print_error_and_exit('Unexpected output for %s | %s = %s' % (pm_cmd, grep_cmd, app_info_dump))


# Source: https://developer.android.com/reference/android/app/usage/UsageStatsManager#STANDBY_BUCKET_ACTIVE
_APP_STANDBY_BUCKETS = {
    10: 'active',
    20: 'working',
    30: 'frequent',
    40: 'rare',
}


# Source: https://developer.android.com/preview/features/power#buckets
def get_standby_bucket(package_name):
    _error_if_min_version_less_than(28)
    cmd = 'am get-standby-bucket %s' % package_name
    result = execute_adb_shell_command(cmd)
    if result is None:
        print_error_and_exit('Unknown')
    print_verbose('App standby bucket for \"%s\" is %s' %(
        package_name, _APP_STANDBY_BUCKETS.get(int(result), 'unknown')))
    print(_APP_STANDBY_BUCKETS.get(int(result), 'unknown'))


def set_standby_bucket(package_name, mode):
    _error_if_min_version_less_than(28)
    cmd = 'am set-standby-bucket %s %s' % (package_name, mode)
    result = execute_adb_shell_command(cmd)
    if result is not None:  # Expected
        print_error_and_exit(result)


def _calculate_standby_mode(args):
    if args['active']:
        return 'active'
    elif args['working_set']:
        return 'working_set'
    elif args['frequent']:
        return 'frequent'
    elif args['rare']:
        return 'rare'
    else:
        raise ValueError('Illegal argument: %s' % args)


# Source: https://developer.android.com/preview/features/power
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
    cmd = '%s %s' % (cmd_prefix, file_path)
    cmd = _may_be_wrap_with_run_as(cmd, file_path)
    print_message(execute_adb_shell_command(cmd))


def delete_file(file_path, force, recursive):
    cmd_prefix = 'rm'
    if force:
        cmd_prefix += ' -f'
    if recursive:
        cmd_prefix += ' -r'
    cmd = '%s %s' % (cmd_prefix, file_path)
    cmd = _may_be_wrap_with_run_as(cmd, file_path)
    print_message(execute_adb_shell_command(cmd))


# Limitation: This command will only do run-as for the src file so, if a file is being copied from pkg1 to pkg2
# on a non-rooted device with both pkg1 and pkg2 being debuggable, this will fail. This can be improved by
# first copying the file to /data/local/tmp but as of now, I don't think that's required.
def move_file(src_path, dest_path, force):
    cmd_prefix = 'mv'
    if force:
        cmd_prefix += '-f'
    cmd = '%s %s %s' % (cmd_prefix, src_path, dest_path)
    cmd = _may_be_wrap_with_run_as(cmd, src_path)
    print_message(execute_adb_shell_command(cmd))


# Copies from remote_file_path on Android to local_file_path on the disk
# local_file_path can be None
def pull_file(remote_file_path, local_file_path, copy_ancillary = False):
    if not _file_exists(remote_file_path):
        print_error_and_exit('File %s does not exist' % remote_file_path)

    if local_file_path is None:
        local_file_path = remote_file_path.split('/')[-1]
        print_verbose('Local file path not provided, using \"%s\" for that' % local_file_path)

    tmp_file = _create_tmp_file()
    cp_cmd = 'cp -r %s %s' % (remote_file_path, tmp_file)
    wrapped_cp_cmd = _may_be_wrap_with_run_as(cp_cmd, remote_file_path)
    if cp_cmd == wrapped_cp_cmd:
        # cp command is not required at all, if copying it is not required.
        pull_cmd = 'pull %s %s' % (remote_file_path, local_file_path)
        execute_adb_command(pull_cmd)
    else:
        # First copy the files to sdcard, then pull them out, and then delete them from sdcard.
        execute_adb_shell_command(wrapped_cp_cmd)
        pull_cmd = 'pull %s %s' % (tmp_file, local_file_path)
        execute_adb_command(pull_cmd)
        del_cmd = 'rm -r %s' % tmp_file
        execute_adb_shell_command(del_cmd)

    print_message('Copying remote file \"%s\" to local file \"%s\" (Size: %d bytes)' % (
        remote_file_path,
        local_file_path,
        os.path.getsize(local_file_path)))

    if _is_sqlite_database(remote_file_path):
        # Copy temporary Sqlite files
        # Source :https://ashishb.net/all/android-the-right-way-to-pull-sqlite-database-from-the-device/
        for suffix in ['wal', 'journal', 'shm']:
            tmp_db_file = '%s-%s' % (remote_file_path, suffix)
            if not _file_exists(tmp_db_file):
                continue
            if copy_ancillary:
                pull_file(tmp_db_file, '%s-%s' %(local_file_path, suffix), copy_ancillary=True)
            else:
                print_error('File \"%s\" has an ancillary file \"%s\" which should be copied.\nSee %s for details'
                            % (remote_file_path, tmp_db_file,
                               'https://ashishb.net/all/android-the-right-way-to-pull-sqlite-database-from-the-device/'))


def push_file(local_file_path, remote_file_path):
    if not os.path.exists(local_file_path):
        print_error_and_exit('Local file %s does not exist' % local_file_path)
    if os.path.isdir(local_file_path):
        print_error_and_exit('This tool does not support pushing a directory yet' % local_file_path)

    # First push to tmp file in /data/local/tmp and then move that
    tmp_file = _create_tmp_file()
    push_cmd = 'push %s %s' % (local_file_path, tmp_file)
    # "mv" from /data/local/tmp with run-as <app_id> does not always work even when the underlying
    # dir has mode set to 777. Therefore, do a two-step cp and rm.
    mv_cmd = 'cp %s %s' % (tmp_file, remote_file_path)
    mv_cmd = _may_be_wrap_with_run_as(mv_cmd, remote_file_path)
    rm_cmd = 'rm %s' % tmp_file
    execute_adb_shell_command(rm_cmd)

    execute_adb_command(push_cmd)
    execute_adb_shell_command(mv_cmd)


def cat_file(file_path):
    cmd_prefix = 'cat'
    cmd = '%s %s' % (cmd_prefix, file_path)
    cmd = _may_be_wrap_with_run_as(cmd, file_path)
    print_message(execute_adb_shell_command(cmd))


def _may_be_wrap_with_run_as(cmd, file_path):
    if file_path.startswith('/data/data/'):
        run_as_package = file_path.split('/')[3]
        if run_as_package is not None and len(run_as_package.strip()) > 0:
            print_verbose('Running as package: %s' % run_as_package)
            cmd_with_run_as = 'run-as %s %s ' % (run_as_package, _escape_quotes(cmd))
            cmd_with_su = 'su root %s ' % _escape_quotes(cmd)
            # First try with run-as and if that fails, try with su , and if that fails, try directly.
            return '\" %s 2>/dev/null || %s 2>/dev/null || %s \"' % (
                cmd_with_run_as, cmd_with_su, cmd)

    # Try with su as well.
    cmd_with_su = 'su root %s' % _escape_quotes(cmd)
    return '\"  %s 2>/dev/null ||  %s\"' % (cmd_with_su, cmd)


def _escape_quotes(cmd):
    return cmd.replace('\'', '\\\'').replace('\"', '\\\"')


# Source: https://stackoverflow.com/a/25398877
def launch_app(app_name):
    adb_shell_cmd = 'monkey -p %s -c android.intent.category.LAUNCHER 1' % app_name
    execute_adb_shell_command(adb_shell_cmd)


def stop_app(app_name):
    # Below API 21, stop does not kill app in the foreground.
    # Above API 21, it seems it does.
    if _get_device_android_api_version() < 21:
        force_stop(app_name)
    else:
        adb_shell_cmd = 'am kill %s' % app_name
        execute_adb_shell_command(adb_shell_cmd)


def _regex_extract(regex, data):
    regex_object = re.search(regex, data, re.IGNORECASE)
    if regex_object is None:
        return None
    else:
        return regex_object.group(1)


# adb shell pm dump <app_name> produces about 1200 lines, mostly useless,
# compared to this.
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

    if _get_device_android_api_version() >= 23:
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
    if len(install_time_granted_permissions) > 0:
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
    if len(install_time_granted_permissions) > 0:
        permissions_info_msg += 'Install time granted permissions:\n%s\n\n' % '\n'.join(
            install_time_granted_permissions)
    if len(install_time_denied_permissions) > 0:
        permissions_info_msg += 'Install time denied permissions:\n%s\n\n' % '\n'.join(
            install_time_denied_permissions)
    if len(runtime_granted_permissions) > 0:
        permissions_info_msg += 'Runtime granted permissions:\n%s\n\n' % '\n'.join(
            runtime_granted_permissions)
    if len(runtime_denied_permissions) > 0:
        permissions_info_msg += 'Runtime denied permissions:\n%s\n\n' % '\n'.join(
            runtime_denied_permissions)
    if len(runtime_not_granted_permissions) > 0:
        permissions_info_msg += 'Runtime Permissions not granted and not yet requested:\n%s\n\n' % '\n'.join(
            runtime_not_granted_permissions)
    return permissions_info_msg


def _get_apk_path(app_name):
    adb_shell_cmd = 'pm path %s' % app_name
    result = execute_adb_shell_command(adb_shell_cmd)
    apk_path = result.split(':', 2)[1]
    return apk_path


def print_app_path(app_name):
    apk_path = _get_apk_path(app_name)
    print_verbose('Path for %s is %s' % (app_name, apk_path))
    print_message(apk_path)


def print_app_signature(app_name):
    apk_path = _get_apk_path(app_name)
    # Copy apk to a temp file on the disk
    tmp_apk_file = tempfile.NamedTemporaryFile(prefix=app_name, suffix='.apk')
    with tmp_apk_file:
        tmp_apk_file_name = tmp_apk_file.name
        adb_cmd = 'pull %s %s' % (apk_path, tmp_apk_file_name)
        execute_adb_command(adb_cmd)
        dir_of_this_script = os.path.split(__file__)[0]
        apk_signer_jar_path = os.path.join(dir_of_this_script, 'apksigner.jar')
        if not os.path.exists(apk_signer_jar_path):
            print_error_and_exit('apksigner.jar is missing, your adb-enhanced installation is corrupted')
            
        print_signature_cmd = 'java -jar %s verify --print-certs %s' % (apk_signer_jar_path, tmp_apk_file_name)
        print_verbose('Executing command %s' % print_signature_cmd)
        ps1 = subprocess.Popen(print_signature_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for line in ps1.stdout:
            line = line.decode('utf-8').strip()
            print_message(line)
        for line in ps1.stderr:
            line = line.decode('utf-8').strip()
            print_error(line)


# Uses abe.jar taken from https://sourceforge.net/projects/adbextractor/
def perform_app_backup(app_name, backup_tar_file):
    # TODO: Add a check to ensure that the screen is unlocked

    password = '00'
    print_verbose('Performing backup to backup.ab file')
    print_message('you might have to confirm the backup manually on your device\'s screen, enter \"%s\" as password...' % password)

    def backup_func():
        # Create backup.ab
        adb_backup_cmd = 'backup -noapk %s' % app_name
        execute_adb_command(adb_backup_cmd)

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
        ps = subprocess.Popen(abe_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ps.communicate()
        if ps.returncode == 0:
            print_message('Successfully backed up data of app %s to %s' % (app_name, backup_tar_file))
        else:
            print_error('Failed to convert backup.ab to tar file. Please ensure that it is not password protected')
    finally:
        print_verbose('Deleting backup.ab')
        ps = subprocess.Popen('rm backup.ab', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ps.communicate()


def perform_install(file_path):
    print_verbose('Installing %s' % file_path)
    # -r: replace existing application
    execute_adb_command('install -r %s' % file_path)


def perform_uninstall(app_name):
    _ensure_package_exists(app_name)
    print_verbose('Uninstalling %s' % app_name)
    execute_adb_command('uninstall %s' % app_name)


def _get_window_size():
    adb_cmd = 'shell wm size'
    result = execute_adb_command(adb_cmd)

    if result is None:
        return -1, -1

    regex_data = re.search('size: ([0-9]+)x([0-9]+)', result)
    if regex_data is None:
        return -1, -1

    return int(regex_data.group(1)), int(regex_data.group(2))


def _perform_tap(x, y):
    adb_shell_cmd = 'input tap %d %d' % (x, y)
    execute_adb_shell_command(adb_shell_cmd)


def execute_adb_shell_settings_command(settings_cmd):
    _error_if_min_version_less_than(19)
    return execute_adb_shell_command('settings %s' % settings_cmd)


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


def _error_if_min_version_less_than(min_acceptable_version):
    api_version = _get_device_android_api_version()
    if api_version < min_acceptable_version:
        cmd = ' '.join(sys.argv[1:])
        print_error_and_exit(
            '\"%s\" can only be executed on API %d and above, your device version is %d' %
            (cmd, min_acceptable_version, api_version))


# adb shell getprop ro.build.version.sdk
def _get_device_android_api_version():
    version_string = _get_prop('ro.build.version.sdk')
    if version_string is None:
        print_error_and_exit('Unable to get Android device version, is it still connected?')
    return int(version_string)


def _is_emulator():
    qemu = _get_prop('ro.kernel.qemu')
    return qemu is not None and qemu.strip() == '1'


def _get_prop(property_name):
    return execute_adb_shell_command('getprop %s' % property_name)


def _using_python2():
    return sys.version_info < (3, 0)


def _warn_about_python2_deprecation():
    msg = ('You are using Python 2, ADB-enhanced would stop supporting Python 2 after Dec 31, 2018\n' +
        'First install Python 3 and then re-install this tool using\n' +
        '\"sudo pip uninstall adb-enhanced && sudo pip3 install adb-enhanced\"')
    output_helper.print_error(msg)


if __name__ == '__main__':
    main()
