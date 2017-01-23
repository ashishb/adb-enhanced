#!/usr/local/bin/python

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
* adbe mobile-data (on|off)
* adbe [options] input-text <text>
* adbe press back


List of things which this tool will do in the future

* adbe airplane [on|off]  # does not seem to work properly
* adbe b[ack]g[round-]c[ellular-]d[ata] [on|off] $app_name # This might not be needed at all after mobile-data saver mode
* adbe app-standby $app_name
* adbe wifi [on|off]  # svc wifi enable/disable does not seem to always work
* adbe screenrecord $file_name
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
    adbe.py [options] airplane ( on | off ) - This does not work on all the devices as of now.
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
    adbe.py [options] dont-keep-activities (on | off)
    adbe.py [options] input-text <text>
    adbe.py [options] press back

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

    adb_prefix = "adb %s" % options

    if False:
        print args
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
        # This is not working as expected
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
    elif args['dont-keep-activities']:
        handle_dont_keep_activities_in_background(adb_prefix, args['on'])
    elif args['input-text']:
        input_text(adb_prefix, args['<text>'])
    elif args['back']:
        press_back(adb_prefix)
    else:
        raise NotImplementedError("Not implemented: %s" % args)


def validate_options(args):
    count = 0
    if args['--emulator']:
        count += 1
    if args['--device']:
        count += 1
    if args['--serial']:
        count += 1
    if count > 1:
        raise AssertionError("Only one out of -e, -d, or -s can be provided")


# Source: https://github.com/dhelleberg/android-scripts/blob/master/src/devtools.groovy
def handle_gfx(adb_prefix, value):
    if value == 'on':
        cmd = 'setprop debug.hwui.profile visual_bars'
    elif value == 'off':
        cmd = 'setprop debug.hwui.profile false'
    elif value == 'lines':
        cmd = 'setprop debug.hwui.profile visual_lines'
    else:
        raise AssertionError("Unexpected value for gfx %s" % value)
    execute_adb_shell_command_and_poke_activity_service(adb_prefix, cmd)


# Source: https://github.com/dhelleberg/android-scripts/blob/master/src/devtools.groovy
# https://plus.google.com/+AladinQ/posts/dpidzto1b8B
def handle_overdraw(adb_prefix, value):
    if value is 'on':
        cmd = 'setprop debug.hwui.overdraw show'
    elif value is 'off':
        cmd = 'setprop debug.hwui.overdraw false'
    elif value is 'deut':
        cmd = 'setprop debug.hwui.overdraw show_deuteranomaly'
    else:
        raise AssertionError("Unexpected value for overdraw %s" % value)
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
            print 'Current direction: %d' % current_direction
        new_direction = (current_direction + 1) % 4
    elif direction is 'right':
        current_direction = get_current_rotation_direction(adb_prefix)
        if _verbose:
            print 'Current direction: %d' % current_direction
        new_direction = (current_direction - 1) % 4
    else:
        raise AssertionError('Unexpected direction %s' % direction)
    cmd = 'settings put system user_rotation %s' % new_direction
    execute_adb_shell_command(adb_prefix, cmd)


def get_current_rotation_direction(adb_prefix):
    cmd = 'settings get system user_rotation'
    direction = execute_adb_shell_command(adb_prefix, cmd)
    if _verbose:
        print 'Return value is %s' % direction
    if not direction:
        return 0  # default direction is 0, vertical straight
    return int(direction)


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
    execute_adb_shell_command(adb_prefix, cmd)


# Source: https://stackoverflow.com/questions/28234502/programmatically-enable-disable-battery-saver-mode
def handle_battery_level(adb_prefix, level):
    if level < 0 or level > 100:
        raise AssertionError("Battery percentage must be between 0 and 100")
    cmd = 'dumpsys battery set level %d' % level

    execute_adb_shell_command(adb_prefix, get_battery_unplug_cmd())
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
        execute_adb_shell_command(adb_prefix, cmd)
    else:
        cmd = 'dumpsys deviceidle unforce'
        execute_adb_shell_command(adb_prefix, handle_battery_reset())
        execute_adb_shell_command(adb_prefix, cmd)


# Source: https://github.com/dhelleberg/android-scripts/blob/master/src/devtools.groovy
# Ref: https://gitlab.com/SaberMod/pa-android-frameworks-base/commit/a53de0629f3b94472c0f160f5bbe1090b020feab
def get_update_activity_service_cmd():
    # Note: 1599295570 == ('_' << 24) | ('S' << 16) | ('P' << 8) | 'R'
    return "service call activity 1599295570"


def get_battery_unplug_cmd():
    return 'dumpsys battery unplug'


def handle_get_jank(adb_prefix, app_name):
    cmd = 'dumpsys gfxinfo %s ' % app_name
    execute_adb_shell_command(adb_prefix, cmd, 'grep Janky')


def handle_list_devices(adb_prefix):
    cmd = 'devices -l'
    execute_adb_command(adb_prefix, cmd)


def print_top_activity(adb_prefix):
    cmd = 'dumpsys activity recents'
    execute_adb_shell_command(adb_prefix, cmd, 'grep "Recent #0"')


def force_stop(adb_prefix, app_name):
    cmd = 'am force-stop %s' % app_name
    execute_adb_shell_command(adb_prefix, cmd)


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
    filepath_on_device = "/sdcard/screenshot-%d.png" % random.randint(1, 1000 * 1000 * 1000)
    # TODO: May be in the future, add a check here to ensure that we are not over-writing any existing file.
    dump_cmd = 'screencap -p %s ' % filepath_on_device
    execute_adb_shell_command(adb_prefix, dump_cmd)
    pull_cmd = 'pull %s %s' % (filepath_on_device, filepath)
    execute_adb_command(adb_prefix, pull_cmd)
    del_cmd = 'rm %s' % filepath_on_device
    execute_adb_shell_command(adb_prefix, del_cmd)


# https://developer.android.com/training/basics/network-ops/data-saver.html
def handle_mobile_data_saver(adb_prefix, turn_on):
    if turn_on:
        cmd = "cmd netpolicy set restrict-background true"
    else:
        cmd = "cmd netpolicy set restrict-background false"
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


def execute_adb_shell_command_and_poke_activity_service(adb_prefix, adb_cmd):
    return_value = execute_adb_shell_command(adb_prefix, adb_cmd)
    execute_adb_shell_command(adb_prefix, get_update_activity_service_cmd())
    return return_value


def execute_adb_shell_command(adb_prefix, adb_cmd, piped_into_cmd=None):
    return execute_adb_command(adb_prefix, "shell %s" % adb_cmd, piped_into_cmd)


def execute_adb_command(adb_prefix, adb_cmd, piped_into_cmd=None):
    final_cmd = ("%s %s" % (adb_prefix, adb_cmd))
    if piped_into_cmd:
        if _verbose:
            print 'Executing %s | %s' % (final_cmd, piped_into_cmd)
            print 'Executing %s | %s' % (adb_command, piped_into_cmd)
        ps1 = subprocess.Popen(final_cmd, shell=True, stdout=subprocess.PIPE)
        output = subprocess.check_output(piped_into_cmd, shell=True, stdin=ps1.stdout)
        ps1.wait()
        print output
        return output
    else:
        if _verbose:
            print 'Executing %s' % final_cmd
        ps1 = subprocess.Popen(final_cmd, shell=True, stdout=subprocess.PIPE)
        ps1.wait()
        output = ''
        first_line = True
        for line in ps1.stdout:
            if first_line:
                output += line.strip()
            else:
                output += '\n' + line.strip()
        if _verbose:
            print 'Result is "%s"' % output
        return output


if __name__ == '__main__':
    main()
