#!/usr/local/bin/python

import docopt
import subprocess

"""
List of things which this enhanced adb tool does

1. adbe rotate [left|right]
2. adbe gfx [on|off]
3. adbe overdraw [on|off]
4. adbe layout [on|off]
4. adbe airplane [on|off]
5. adbe activity keep-in-background [on|off]
6. adbe b[ack]g[round-]c[ellular-]d[ata] [on|off] $app_name
7. adbe battery saver [on|off]
8. adbe cellular-data saver [on|off]
9. adbe battery level [0-100]
10. adbe dump top-activity
11. adbe force-stop $app_name
12. adbe clear-data $app_name
13. adbe app-standby $app_name
14. adbe doze $app_name
15. adbe wifi [on|off]
16. adbe dump jank $app_name
17. adbe devices [maps to adb devices -l]



adbe set_app_name [-f] $app_name
adbe reset_app_name

Use -q[uite] for quite mode

"""

USAGE_STRING = """

Usage:
    adbe.py [options] rotate (landscape | portrait)
    adbe.py [options] gfx (on | off | lines)

Options:
    -e, --emulator          directs command to the only running emulator
    -d, --device            directs command to the only connected "USB" device
    -s, --serial SERIAL     directs command to the device or emulator with the given serial number or qualifier.
                            Overrides ANDROID_SERIAL environment variable.

"""


def main():
    args = docopt.docopt(USAGE_STRING, version='1.0.0rc2')
    print args
    cmds = None
    if args['rotate']:
        cmds = handle_rotate(args['portrait'])
    elif args['gfx']:
        value = 'on' if args['on'] else \
            ('off' if args['off'] else
             'lines')
        cmds = handle_gfx(value)

    validate_options(args)
    options = ''
    if args['--emulator']:
        options += '-e '
    if args['--device']:
        options += '-d '
    if args['--serial']:
        options += '-s %s ' % args['--serial']

    if cmds:
        for cmd in cmds:
            final_cmd = ("adb %s shell %s" % (options, cmd))
            subprocess.call(final_cmd, shell=True)


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
def handle_gfx(value):
    if value == 'on':
        cmd = 'setprop debug.hwui.profile visual_bars'
    elif value == 'off':
        cmd = 'setprop debug.hwui.profile false'
    elif value == 'lines':
        cmd = 'setprop debug.hwui.profile visual_lines'
    else:
        raise AssertionError("Unexpected value for gfx %s" % value)
    return [cmd]


# Source: https://stackoverflow.com/questions/25864385/changing-android-device-orientation-with-adb
def handle_rotate(portrait):
    disable_acceleration = 'settings put system accelerometer_rotation 0'
    if portrait:
        cmds = [disable_acceleration, 'settings put system user_rotation 0']
    else:
        cmds = [disable_acceleration, 'settings put system user_rotation 1']
    return cmds


if __name__ == '__main__':
    main()
