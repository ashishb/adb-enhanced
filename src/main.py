#!/usr/bin/python

# Python 2 and 3, print compatibility
from __future__ import print_function

# Without this urllib.parse which is python 3 only cannot be accessed in python 2.
from future.standard_library import install_aliases

install_aliases()

import docopt
import sys
import os

# This is required only for Python 2
# pylint: disable=import-error

try:
    # This fails when the code is executed directly and not as a part of python package installation,
    # I definitely need a better way to handle this.
    from adbe import adb_enhanced
    from adbe import adb_helper
    from adbe.output_helper import print_error, print_error_and_exit, set_verbose
except ImportError:
    # This works when the code is executed directly.
    import adb_enhanced
    import adb_helper
    from output_helper import print_error, print_error_and_exit, set_verbose

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

    set_verbose(args['--verbose'])

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
        adb_enhanced.handle_rotate(direction)
    elif args['gfx']:
        value = 'on' if args['on'] else \
            ('off' if args['off'] else
             'lines')
        adb_enhanced.handle_gfx(value)
    elif args['overdraw']:
        value = 'on' if args['on'] else \
            ('off' if args['off'] else
             'deut')
        adb_enhanced.handle_overdraw(value)
    elif args['layout']:
        value = args['on']
        adb_enhanced.handle_layout(value)
    elif args['airplane']:
        # This does not always work
        value = args['on']
        adb_enhanced.handle_airplane(value)
    elif args['battery']:
        if args['saver']:
            adb_enhanced.handle_battery_saver(args['on'])
        elif args['level']:
            adb_enhanced.handle_battery_level(int(args['<percentage>']))
        elif args['reset']:
            adb_enhanced.handle_battery_reset()
    elif args['doze']:
        adb_enhanced.handle_doze(args['on'])
    elif args['jank']:
        app_name = args['<app_name>']
        adb_enhanced.ensure_package_exists(app_name)
        adb_enhanced.handle_get_jank(app_name)
    elif args['devices']:
        adb_enhanced.handle_list_devices()
    elif args['top-activity']:
        adb_enhanced.print_top_activity()
    elif args['dump-ui']:
        adb_enhanced.dump_ui(args['<xml_file>'])
    elif args['force-stop']:
        app_name = args['<app_name>']
        adb_enhanced.ensure_package_exists(app_name)
        adb_enhanced.force_stop(app_name)
    elif args['clear-data']:
        app_name = args['<app_name>']
        adb_enhanced.ensure_package_exists(app_name)
        adb_enhanced.clear_disk_data(app_name)
    elif args['mobile-data']:
        if args['saver']:
            adb_enhanced.handle_mobile_data_saver(args['on'])
        else:
            adb_enhanced.handle_mobile_data(args['on'])
    elif args['rtl']:
        # This is not working as expected
        adb_enhanced.force_rtl(args['on'])
    elif args['screenshot']:
        adb_enhanced.dump_screenshot(args['<filename.png>'])
    elif args['screenrecord']:
        adb_enhanced.dump_screenrecord(args['<filename.mp4>'])
    elif args['dont-keep-activities']:
        adb_enhanced.handle_dont_keep_activities_in_background(args['on'])
    elif args['animations']:
        adb_enhanced.toggle_animations(args['on'])
    elif args['show-taps']:
        adb_enhanced.toggle_show_taps(turn_on=args['on'])
    elif args['stay-awake-while-charging']:
        # Keep screen on while the device is charging.
        adb_enhanced.stay_awake_while_charging(args['on'])
    elif args['input-text']:
        adb_enhanced.input_text(args['<text>'])
    elif args['back']:
        adb_enhanced.press_back()
    elif args['open-url']:
        url = args['<url>']
        adb_enhanced.open_url(url)
    elif args['permission-groups'] and args['list'] and args['all']:
        adb_enhanced.list_permission_groups()
    elif args['permissions'] and args['list']:
        adb_enhanced.list_permissions(args['dangerous'])
    elif args['permissions']:
        android_api_version = adb_enhanced.get_device_android_api_version()
        if android_api_version < _MIN_API_FOR_RUNTIME_PERMISSIONS:
            print_error_and_exit(
                'Runtime permissions are supported only on API %d and above, your version is %d' %
                (_MIN_API_FOR_RUNTIME_PERMISSIONS, android_api_version))
        app_name = args['<app_name>']
        adb_enhanced.ensure_package_exists(app_name)
        permission_group = adb_enhanced.get_permission_group(args)
        permissions = adb_enhanced.get_permissions_in_permission_group(permission_group)
        if not permissions:
            print_error_and_exit('No permissions found in permissions group: %s' % permission_group)
        adb_enhanced.grant_or_revoke_runtime_permissions(
            app_name, args['grant'], permissions)
    elif args['apps'] and args['list']:
        if args['all']:
            adb_enhanced.list_all_apps()
        elif args['system']:
            adb_enhanced.list_system_apps()
        elif args['third-party']:
            adb_enhanced.list_non_system_apps()
        elif args['debug']:
            adb_enhanced.list_debug_apps()
        elif args['backup-enabled']:
            adb_enhanced.list_allow_backup_apps()
    elif args['standby-bucket']:
        app_name = args['<app_name>']
        adb_enhanced.ensure_package_exists(app_name)
        if args['get']:
            adb_enhanced.get_standby_bucket(app_name)
        elif args['set']:
            adb_enhanced.set_standby_bucket(app_name, adb_enhanced.calculate_standby_mode(args))
    elif args['restrict-background']:
        app_name = args['<app_name>']
        adb_enhanced.ensure_package_exists(app_name)
        adb_enhanced.apply_or_remove_background_restriction(app_name, args['true'])
    elif args['ls']:
        file_path = args['<file_path>']
        long_format = args['-l']
        # Always include hidden files, -a is left for backward-compatibility but is a no-op now.
        include_hidden_files = True
        recursive = args['-R'] or args['-r']
        adb_enhanced.list_directory(file_path, long_format, recursive, include_hidden_files)
    elif args['rm']:
        file_path = args['<file_path>']
        force_delete = args['-f']
        recursive = args['-R'] or args['-r']
        adb_enhanced.delete_file(file_path, force_delete, recursive)
    elif args['mv']:
        src_path = args['<src_path>']
        dest_path = args['<dest_path>']
        force_move = args['-f']
        adb_enhanced.move_file(src_path, dest_path, force_move)
    elif args['pull']:
        remote_file_path = args['<file_path_on_android>']
        local_file_path = args['<file_path_on_machine>']
        copy_ancillary = args['-a']
        adb_enhanced.pull_file(remote_file_path, local_file_path, copy_ancillary)
    elif args['push']:
        remote_file_path = args['<file_path_on_android>']
        local_file_path = args['<file_path_on_machine>']
        adb_enhanced.push_file(local_file_path, remote_file_path)
    elif args['cat']:
        file_path = args['<file_path>']
        adb_enhanced.cat_file(file_path)
    elif args['start']:
        app_name = args['<app_name>']
        adb_enhanced.ensure_package_exists(app_name)
        adb_enhanced.launch_app(app_name)
    elif args['stop']:
        app_name = args['<app_name>']
        adb_enhanced.ensure_package_exists(app_name)
        adb_enhanced.stop_app(app_name)
    elif args['restart']:
        app_name = args['<app_name>']
        adb_enhanced.ensure_package_exists(app_name)
        adb_enhanced.force_stop(app_name)
        adb_enhanced.launch_app(app_name)
    elif args['app']:
        app_name = args['<app_name>']
        adb_enhanced.ensure_package_exists(app_name)
        if args['info']:
            adb_enhanced.print_app_info(app_name)
        elif args['path']:
            adb_enhanced.print_app_path(app_name)
        elif args['signature']:
            adb_enhanced.print_app_signature(app_name)
        elif args['backup']:
            backup_tar_file_path = args['<backup_tar_file_path>']
            if not backup_tar_file_path:
                backup_tar_file_path = '%s_backup.tar' % app_name
            adb_enhanced.perform_app_backup(app_name, backup_tar_file_path)
    elif args['install']:
        file_path = args['<file_path>']
        adb_enhanced.perform_install(file_path)
    elif args['uninstall']:
        app_name = args['<app_name>']
        adb_enhanced.ensure_package_exists(app_name)
        adb_enhanced.perform_uninstall(app_name)
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


def get_version():
    dir_of_this_script = os.path.split(__file__)[0]
    version_file_path = os.path.join(dir_of_this_script, _VERSION_FILE_NAME)
    with open(version_file_path, 'r') as fh:
        return fh.read().strip()


def _using_python2():
    return sys.version_info < (3, 0)


def _warn_about_python2_deprecation():
    msg = ('You are using Python 2, ADB-enhanced would stop supporting Python 2 after Dec 31, 2018\n' +
           'First install Python 3 and then re-install this tool using\n' +
           '\"sudo pip uninstall adb-enhanced && sudo pip3 install adb-enhanced\"')
    print_error(msg)


if __name__ == '__main__':
    main()
