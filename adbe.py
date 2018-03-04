#!/usr/bin/python

# Python 2 and 3, print compatibility
from __future__ import print_function

import docopt
import random
import subprocess

"""
List of things which this enhanced adb tool does

* adbe rotate [left|right]
* adbe gfx [on|off]
* adbe overdraw [on|off]
* adbe layout [on|off]
* adbe destroy-activities-in-background [on|off]
* adbe battery saver [on|off]
* adbe mobile-data saver [on|off]  # adb shell cmd netpolicy set restrict-background true/false
* adbe battery level [0-100]
* adbe doze
* adbe jank $app_name
* adbe devices [maps to adb devices -l]
* adbe top-activity
* adbe force-stop $app_name
* adbe clear-data $app_name
* adbe screenshot $file_name
* adbe screenrecord $file_name
* adbe mobile-data (on|off)
* adbe [options] input-text <text>
* adbe press back


List of things which this tool will do in the future

* adbe airplane [on|off]  # does not seem to work properly
* adbe b[ack]g[round-]c[ellular-]d[ata] [on|off] $app_name # This might not be needed at all after mobile-data saver mode
* adbe app-standby $app_name
* adbe wifi [on|off]  # svc wifi enable/disable does not seem to always work
* adbe rtl (on | off)  # adb shell settings put global debug.force_rtl 1 does not seem to work
* adbe screen (on|off|toggle)  # https://stackoverflow.com/questions/7585105/turn-on-screen-on-device
* adb shell input keyevent KEYCODE_POWER can do the toggle
* adbe press up
* adbe set_app_name [-f] $app_name
* adbe reset_app_name

Use -q[uite] for quite mode

"""

USAGE_STRING = """

Usage:
    adbe.py [options] rotate (landscape | portrait | left | right)
    adbe.py [options] gfx (on | off | lines)
    adbe.py [options] overdraw (on | off | deut)
    adbe.py [options] layout (on | off)
    adbe.py [options] airplane (on | off)
    adbe.py [options] battery level <percentage>
    adbe.py [options] battery saver (on | off)
    adbe.py [options] battery reset
    adbe.py [options] doze (on | off)
    adbe.py [options] jank <app_name>
    adbe.py [options] devices
    adbe.py [options] top-activity
    adbe.py [options] force-stop <app_name>
    adbe.py [options] clear-data <app_name>
    adbe.py [options] mobile-data (on | off)
    adbe.py [options] mobile-data saver (on | off)
    adbe.py [options] rtl (on | off) - This is not working properly as of now.
    adbe.py [options] screenshot <filename.png>
    adbe.py [options] screenrecord <filename.mp4>
    adbe.py [options] dont-keep-activities (on | off)
    adbe.py [options] input-text <text>
    adbe.py [options] press back
    adbe.py [options] permission-groups list all
    adbe.py [options] permissions list (all | dangerous)
    adbe.py [options] permissions (grant | revoke) <package_name> (calendar | camera | contacts | location | microphone | phone | sensors | sms | storage) - grant and revoke runtime permissions

Options:
    -e, --emulator          directs command to the only running emulator
    -d, --device            directs command to the only connected "USB" device
    -s, --serial SERIAL     directs command to the device or emulator with the given serial number or qualifier.
                            Overrides ANDROID_SERIAL environment variable.
    -v, --verbose           Verbose mode

"""

_KEYCODE_BACK = 4

_verbose = False


def main():
    global _verbose
    args = docopt.docopt(USAGE_STRING, version='1.0.0rc2')

    validate_options(args)
    options = ''
    if args['--emulator']:
        options += '-e '
    if args['--device']:
        options += '-d '
    if args['--serial']:
        options += '-s %s ' % args['--serial']
    _verbose = args['--verbose']

    adb_prefix = 'adb %s' % options

    if False:
        print(args)
    if args['rotate']:
        direction = 'portrait' if args['portrait'] else \
                'landscape' if args['landscape'] else \
                'left' if args['left'] else \
                'right'
        handle_rotate(adb_prefix, direction)
    elif args['gfx']:
        value = 'on' if args['on'] else \
            ('off' if args['off'] else
             'lines')
        handle_gfx(adb_prefix, value)
    elif args['overdraw']:
        value = 'on' if args['on'] else \
            ('off' if args['off'] else
             'deut')
        handle_overdraw(adb_prefix, value)
    elif args['layout']:
        value = args['on']
        handle_layout(adb_prefix, value)
    elif args['airplane']:
        # This does not always work
        value = args['on']
        handle_airplane(adb_prefix, value)
    elif args['battery']:
        if args['saver']:
            handle_battery_saver(adb_prefix, args['on'])
        elif args['level']:
            handle_battery_level(adb_prefix, int(args['<percentage>']))
        elif args['reset']:
            handle_battery_reset(adb_prefix)
    elif args['doze']:
        handle_doze(adb_prefix, args['on'])
    elif args['jank']:
        handle_get_jank(adb_prefix, args['<app_name>'])
    elif args['devices']:
        handle_list_devices(adb_prefix)
    elif args['top-activity']:
        print_top_activity(adb_prefix)
    elif args['force-stop']:
        force_stop(adb_prefix, args['<app_name>'])
    elif args['clear-data']:
        clear_disk_data(adb_prefix, args['<app_name>'])
    elif args['mobile-data']:
        if args['saver']:
            handle_mobile_data_saver(adb_prefix, args['on'])
        else:
            handle_mobile_data(adb_prefix, args['on'])
    elif args['rtl']:
        # This is not working as expected
        force_rtl(adb_prefix, args['on'])
    elif args['screenshot']:
        dump_screenshot(adb_prefix, args['<filename.png>'])
    elif args['screenrecord']:
        dump_screenrecord(adb_prefix, args['<filename.mp4>'])
    elif args['dont-keep-activities']:
        handle_dont_keep_activities_in_background(adb_prefix, args['on'])
    elif args['input-text']:
        input_text(adb_prefix, args['<text>'])
    elif args['back']:
        press_back(adb_prefix)
    elif args['permission-groups'] and args['list'] and args['all']:
        list_permission_groups(adb_prefix)
    elif args['permissions'] and args['list']:
        list_permissions(adb_prefix, args['dangerous'])
    elif args['permissions']:
        package_name = args['<package_name>']
        permission_group = get_permission_group(args)
        permissions = get_permissions_in_permission_group(adb_prefix, permission_group)
        grant_or_revoke_runtime_permissions(adb_prefix, package_name, args['grant'], permissions)
    else:
        raise NotImplementedError('Not implemented: %s' % args)


def validate_options(args):
    count = 0
    if args['--emulator']:
        count += 1
    if args['--device']:
        count += 1
    if args['--serial']:
        count += 1
    if count > 1:
        raise AssertionError('Only one out of -e, -d, or -s can be provided')


# Source: https://github.com/dhelleberg/android-scripts/blob/master/src/devtools.groovy
def handle_gfx(adb_prefix, value):
    if value == 'on':
        cmd = 'setprop debug.hwui.profile visual_bars'
    elif value == 'off':
        cmd = 'setprop debug.hwui.profile false'
    elif value == 'lines':
        cmd = 'setprop debug.hwui.profile visual_lines'
    else:
        raise AssertionError('Unexpected value for gfx %s' % value)
    execute_adb_shell_command_and_poke_activity_service(adb_prefix, cmd)


# Source: https://github.com/dhelleberg/android-scripts/blob/master/src/devtools.groovy
# https://plus.google.com/+AladinQ/posts/dpidzto1b8B
def handle_overdraw(adb_prefix, value):
    version = _get_api_version(adb_prefix)
    if version < 19:
        if value is 'on':
            cmd = 'setprop debug.hwui.show_overdraw true'
        elif value is 'off':
            cmd = 'setprop debug.hwui.show_overdraw false'
        elif value is 'deut':
            raise AssertionError(
                    'This command is not support on API %d' % version)
        else:
            raise AssertionError('Unexpected value for overdraw %s' % value)
    else:
        if value is 'on':
            cmd = 'setprop debug.hwui.overdraw show'
        elif value is 'off':
            cmd = 'setprop debug.hwui.overdraw false'
        elif value is 'deut':
            cmd = 'setprop debug.hwui.overdraw show_deuteranomaly'
        else:
            raise AssertionError('Unexpected value for overdraw %s' % value)
    execute_adb_shell_command_and_poke_activity_service(adb_prefix, cmd)


# Source: https://stackoverflow.com/questions/25864385/changing-android-device-orientation-with-adb
def handle_rotate(adb_prefix, direction):
    disable_acceleration = 'settings put system accelerometer_rotation 0'
    execute_adb_shell_command(adb_prefix, disable_acceleration)

    if direction is 'portrait':
        new_direction = 0
    elif direction is 'landscape':
        new_direction = 1
    elif direction is 'left':
        current_direction = get_current_rotation_direction(adb_prefix)
        if _verbose:
            print("Current direction: %d" % current_direction)
        if current_direction is None:
            return
        new_direction = (current_direction + 1) % 4
    elif direction is 'right':
        current_direction = get_current_rotation_direction(adb_prefix)
        if _verbose:
            print("Current direction: %d" % current_direction)
        if current_direction is None:
            return
        new_direction = (current_direction - 1) % 4
    else:
        raise AssertionError('Unexpected direction %s' % direction)
    cmd = 'settings put system user_rotation %s' % new_direction
    execute_adb_shell_command(adb_prefix, cmd)


def get_current_rotation_direction(adb_prefix):
    cmd = 'settings get system user_rotation'
    direction = execute_adb_shell_command(adb_prefix, cmd)
    if _verbose:
        print("Return value is %s" % direction)
    if not direction:
        return 0  # default direction is 0, vertical straight
    try:
        return int(direction)
    except ValueError as e:
        print("Failed to get direction, device returned: \"%s\"" % e)


def handle_layout(adb_prefix, value):
    if value:
        cmd = 'setprop debug.layout true'
    else:
        cmd = 'setprop debug.layout false'
    execute_adb_shell_command_and_poke_activity_service(adb_prefix, cmd)


# Source: https://stackoverflow.com/questions/10506591/turning-airplane-mode-on-via-adb
# This is incomplete
def handle_airplane(adb_prefix, turn_on):
    if turn_on:
        cmd = 'settings put global airplane_mode_on 1'
    else:
        cmd = 'settings put global airplane_mode_on 0'

    broadcast_change = 'am broadcast -a android.intent.action.AIRPLANE_MODE'
    execute_adb_shell_command(adb_prefix, cmd)
    execute_adb_shell_command(adb_prefix, broadcast_change)


# Source: https://stackoverflow.com/questions/28234502/programmatically-enable-disable-battery-saver-mode
def handle_battery_saver(adb_prefix, turn_on):
    if turn_on:
        cmd = 'settings put global low_power 1'
    else:
        cmd = 'settings put global low_power 0'

    execute_adb_shell_command(adb_prefix, get_battery_unplug_cmd())
    execute_adb_shell_command(adb_prefix, get_battery_discharging_cmd())
    execute_adb_shell_command(adb_prefix, cmd)


# Source: https://stackoverflow.com/questions/28234502/programmatically-enable-disable-battery-saver-mode
def handle_battery_level(adb_prefix, level):
    if level < 0 or level > 100:
        raise AssertionError('Battery percentage must be between 0 and 100')
    cmd = 'dumpsys battery set level %d' % level

    execute_adb_shell_command(adb_prefix, get_battery_unplug_cmd())
    execute_adb_shell_command(adb_prefix, get_battery_discharging_cmd())
    execute_adb_shell_command(adb_prefix, cmd)


# Source: https://stackoverflow.com/questions/28234502/programmatically-enable-disable-battery-saver-mode
def handle_battery_reset(adb_prefix):
    cmd = 'dumpsys battery reset'
    execute_adb_shell_command(adb_prefix, cmd)


# https://developer.android.com/training/monitoring-device-state/doze-standby.html
def handle_doze(adb_prefix, turn_on):
    if turn_on:
        cmd = 'dumpsys deviceidle force-idle'
        execute_adb_shell_command(adb_prefix, get_battery_unplug_cmd())
        execute_adb_shell_command(adb_prefix, get_battery_discharging_cmd())
        execute_adb_shell_command(adb_prefix, cmd)
    else:
        cmd = 'dumpsys deviceidle unforce'
        execute_adb_shell_command(adb_prefix, handle_battery_reset())
        execute_adb_shell_command(adb_prefix, cmd)


# Source: https://github.com/dhelleberg/android-scripts/blob/master/src/devtools.groovy
# Ref: https://gitlab.com/SaberMod/pa-android-frameworks-base/commit/a53de0629f3b94472c0f160f5bbe1090b020feab
def get_update_activity_service_cmd():
    # Note: 1599295570 == ('_' << 24) | ('S' << 16) | ('P' << 8) | 'R'
    return 'service call activity 1599295570'

# This command puts the battery in discharging mode (most likely this is Android 6.0 onwards only)
def get_battery_discharging_cmd():
    return 'dumpsys battery set status 3'

def get_battery_unplug_cmd():
    return 'dumpsys battery unplug'


def handle_get_jank(adb_prefix, app_name):
    cmd = 'dumpsys gfxinfo %s ' % app_name
    execute_adb_shell_command(adb_prefix, cmd, 'grep Janky')


def handle_list_devices(adb_prefix):
    s1 = execute_adb_command(adb_prefix, 'devices -l')
    s2 = execute_adb_shell_command(adb_prefix, 'getprop ro.product.manufacturer') 
    s3 = execute_adb_shell_command(adb_prefix, 'getprop ro.product.model') 
    s4 = execute_adb_shell_command(adb_prefix, 'getprop ro.build.version.release')
    s5 = execute_adb_shell_command(adb_prefix, 'getprop ro.build.version.sdk')
    print(s1, s2, s3, '\tRelease:', s4, '\tSDK version:', s5)

def print_top_activity(adb_prefix):
    cmd = 'dumpsys activity recents'
    execute_adb_shell_command(adb_prefix, cmd, 'grep "Recent #0"')


def force_stop(adb_prefix, app_name):
    cmd = 'am force-stop %s' % app_name
    print(execute_adb_shell_command(adb_prefix, cmd))


def clear_disk_data(adb_prefix, app_name):
    cmd = 'pm clear %s' % app_name
    execute_adb_shell_command(adb_prefix, cmd)


# Source: https://stackoverflow.com/questions/26539445/the-setmobiledataenabled-method-is-no-longer-callable-as-of-android-l-and-later
def handle_mobile_data(adb_prefix, turn_on):
    if turn_on:
        cmd = 'svc data enable'
    else:
        cmd = 'svc data disable'
    execute_adb_shell_command(adb_prefix, cmd)


def force_rtl(adb_prefix, turn_on):
    if turn_on:
        cmd = 'settings put global debug.force_rtl 1'
    else:
        cmd = 'settings put global debug.force_rtl 1'
    execute_adb_shell_command_and_poke_activity_service(adb_prefix, cmd)


def dump_screenshot(adb_prefix, filepath):
    filepath_on_device = '/sdcard/screenshot-%d.png' % random.randint(1, 1000 * 1000 * 1000)
    # TODO: May be in the future, add a check here to ensure that we are not over-writing any existing file.
    dump_cmd = 'screencap -p %s ' % filepath_on_device
    execute_adb_shell_command(adb_prefix, dump_cmd)
    pull_cmd = 'pull %s %s' % (filepath_on_device, filepath)
    execute_adb_command(adb_prefix, pull_cmd)
    del_cmd = 'rm %s' % filepath_on_device
    execute_adb_shell_command(adb_prefix, del_cmd)


def dump_screenrecord(adb_prefix, filepath):
    filepath_on_device = "/sdcard/screenrecord-%d.mp4" % random.randint(1, 1000 * 1000 * 1000)
    # TODO: May be in the future, add a check here to ensure that we are not over-writing any existing file.
    dump_cmd = 'screenrecord %s --time-limit 10 ' % filepath_on_device
    execute_adb_shell_command(adb_prefix, dump_cmd)
    pull_cmd = 'pull %s %s' % (filepath_on_device, filepath)
    execute_adb_command(adb_prefix, pull_cmd)
    del_cmd = 'rm %s' % filepath_on_device
    execute_adb_shell_command(adb_prefix, del_cmd)


# https://developer.android.com/training/basics/network-ops/data-saver.html
def handle_mobile_data_saver(adb_prefix, turn_on):
    if turn_on:
        cmd = 'cmd netpolicy set restrict-background true'
    else:
        cmd = 'cmd netpolicy set restrict-background false'
    execute_adb_shell_command(adb_prefix, cmd)


# Ref: https://github.com/android/platform_packages_apps_settings/blob/4ce19f5c4fd40f3bedc41d3fbcbdede8b2614501/src/com/android/settings/DevelopmentSettings.java#L2123
# adb shell settings put global always_finish_activities true might not work on all Android versions.
# It was in system (not global before ICS)
# adb shell service call activity 43 i32 1 followed by that
def handle_dont_keep_activities_in_background(adb_prefix, turn_on):
    if turn_on:
        cmd1 = 'settings put global always_finish_activities true'
        cmd2 = 'service call activity 43 i32 1'
    else:
        cmd1 = 'settings put global always_finish_activities false'
        cmd2 = 'service call activity 43 i32 0'
    execute_adb_shell_command(adb_prefix, cmd1)
    execute_adb_shell_command_and_poke_activity_service(adb_prefix, cmd2)


def input_text(adb_prefix, text):
    cmd = 'input text %s' % text
    execute_adb_shell_command(adb_prefix, cmd)


def press_back(adb_prefix):
    cmd = 'input keyevent 4'
    execute_adb_shell_command(adb_prefix, cmd)


def list_permission_groups(adb_prefix):
    cmd = 'pm list permission-groups'
    print(execute_adb_shell_command(adb_prefix, cmd))


def list_permissions(adb_prefix, dangerous_only_permissions):
    # -g is to group permissions by permission groups.
    if dangerous_only_permissions:
        # -d => dangerous only permissions
        cmd = 'pm list permissions -g -d'
    else:
        cmd = 'pm list permissions -g'
    print(execute_adb_shell_command(adb_prefix, cmd))

# Returns a fully-qualified permission group name.
def get_permission_group(args):
    if args['contacts']: return 'android.permission-group.CONTACTS'
    if args['phone']: return 'android.permission-group.PHONE'
    if args['calendar']: return 'android.permission-group.CALENDAR'
    if args['camera']: return 'android.permission-group.CAMERA'
    if args['sensors']: return 'android.permission-group.SENSORS'
    if args['location']: return 'android.permission-group.LOCATION'
    if args['storage']: return 'android.permission-group.STORAGE'
    if args['microphone']: return 'android.permission-group.MICROPHONE'
    if args['sms']: return 'android.permission-group.SMS'
    raise AssertionError('Unexpected permission group: %s' % args)


# Pass the full-qualified permission group name to this method.
def get_permissions_in_permission_group(adb_prefix, permission_group):
    # List permissions by group
    permission_output = execute_adb_shell_command(adb_prefix, 'pm list permissions -g')
    splits = permission_output.split('group:')
    for split in splits:
        if split.startswith(permission_group):
            potential_permissions = split.split('\n')
            # Ignore the first entry which is the group name
            potential_permissions = potential_permissions[1:]
            # Filter out empty lines.
            permissions = filter(lambda x: len(x.strip()) > 0, potential_permissions)
            permissions = map(lambda x: x.replace('permission:', ''), permissions)
            print('Permissions are %s' % permissions)
            return permissions

def grant_or_revoke_runtime_permissions(adb_prefix, package_name, action_grant, permissions):
    if action_grant:
        cmd = 'pm grant %s' % package_name
    else:
        cmd = 'pm revoke %s' % package_name
    for permission in permissions:
        execute_adb_shell_command(adb_prefix, cmd + ' ' + permission)


def execute_adb_shell_command_and_poke_activity_service(adb_prefix, adb_cmd):
    return_value = execute_adb_shell_command(adb_prefix, adb_cmd)
    execute_adb_shell_command(adb_prefix, get_update_activity_service_cmd())
    return return_value


def execute_adb_shell_command(adb_prefix, adb_cmd, piped_into_cmd=None):
    return execute_adb_command(adb_prefix, 'shell %s' % adb_cmd, piped_into_cmd)


def execute_adb_command(adb_prefix, adb_cmd, piped_into_cmd=None):
    final_cmd = ('%s %s' % (adb_prefix, adb_cmd))
    if piped_into_cmd:
        if _verbose:
            print("Executing %s | %s" % (final_cmd, piped_into_cmd))
            print("Executing %s | %s" % (adb_cmd, piped_into_cmd))
        ps1 = subprocess.Popen(final_cmd, shell=True, stdout=subprocess.PIPE)
        output = subprocess.check_output(piped_into_cmd, shell=True, stdin=ps1.stdout)
        ps1.wait()
        print(output)
        return output
    else:
        if _verbose:
            print("Executing %s" % final_cmd)
        ps1 = subprocess.Popen(final_cmd, shell=True, stdout=subprocess.PIPE)
        ps1.wait()
        output = ''
        first_line = True
        for line in ps1.stdout:
            if first_line:
                output += line.strip()
                first_line = False
            else:
                output += '\n' + line.strip()
        if _verbose:
            print("Result is \"%s\"" % output)
        return output

# adb shell getprop ro.build.version.sdk
def _get_api_version(adb_prefix):
    version_string = _get_prop(adb_prefix, 'ro.build.version.sdk')
    if version_string is None:
        return -1
    return int(version_string)


def _get_prop(adb_prefix, property_name):
    return execute_adb_shell_command(adb_prefix, 'getprop %s' % property_name)


if __name__ == '__main__':
    main()
