#!/usr/bin/env python3

import sys
import os

import docopt


try:
    # First try local import for development
    from adbe import adb_enhanced
    from adbe import adb_helper
    from adbe.output_helper import print_error_and_exit, set_verbose
# Python 3.6 onwards, this throws ModuleNotFoundError
except (ImportError, ModuleNotFoundError):
    # This works when the code is executed as a part of the module
    import adb_enhanced
    import adb_helper
    from output_helper import print_error_and_exit, set_verbose

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
    adbe [options] dark mode (on | off)
    adbe [options] doze (on | off)
    adbe [options] jank <app_name>
    adbe [options] devices
    adbe [options] top-activity
    adbe [options] dump-ui <xml_file>
    adbe [options] mobile-data (on | off)
    adbe [options] mobile-data saver (on | off)
    adbe [options] wifi (on | off)
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
    adbe [options] notifications list
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
    adbe [options] uninstall [--first-user] <app_name>
    adbe [options] enable wireless debugging
    adbe [options] disable wireless debugging
    adbe [options] screen (on | off | toggle)
    adbe [options] alarm (all | top | pending | history)
    adbe [options] location (on | off)

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

"""

"""
List of things which this tool will do in the future

* adbe app-standby $app_name
* adbe rtl (on | off)  # adb shell settings put global debug.force_rtl 1 does not seem to work
* adb shell input keyevent KEYCODE_POWER can do the toggle
* adbe press up
* adbe set_app_name [-f] $app_name
* adbe reset_app_name
* Use -q[uite] for quite mode
* Add IMEI, IMSI, phone number, and WI-Fi MAC address to devices info command - I think the best way to implement this
  will be via a companion app. And while we are on that, we can implement locale change via the companion app as well.
* adbe dump media session - adb shell dump media_session

"""

_VERSION_FILE_NAME = 'version.txt'


def main():
    if _using_python2():
        _fail_with_python2_warning()

    args = docopt.docopt(USAGE_STRING, version=get_version())
    set_verbose(args['--verbose'])

    validate_options(args)
    options = get_generic_options_from_args(args)
    if options:
        adb_prefix = '%s %s' % (adb_helper.get_adb_prefix(), options)
        adb_helper.set_adb_prefix(adb_prefix)

    # rotate
    if args['rotate'] and args['portrait']:
        adb_enhanced.handle_rotate('portrait')
    elif args['rotate'] and args['landscape']:
        adb_enhanced.handle_rotate('landscape')
    elif args['rotate'] and args['left']:
        adb_enhanced.handle_rotate('left')
    elif args['rotate'] and args['right']:
        adb_enhanced.handle_rotate('right')

    # gfx
    elif args['gfx'] and args['on']:
        adb_enhanced.handle_gfx('on')
    elif args['gfx'] and args['off']:
        adb_enhanced.handle_gfx('off')
    elif args['gfx'] and args['lines']:
        adb_enhanced.handle_gfx('lines')

    # overdraw
    elif args['overdraw'] and args['on']:
        adb_enhanced.handle_overdraw('on')
    elif args['overdraw'] and args['off']:
        adb_enhanced.handle_overdraw('off')
    elif args['overdraw'] and args['deut']:
        adb_enhanced.handle_overdraw('deut')

    elif args['layout']:
        adb_enhanced.handle_layout(args['on'])
    elif args['airplane']:  # This command does not always work
        adb_enhanced.handle_airplane(args['on'])

    # battery
    elif args['battery'] and args['saver']:
        adb_enhanced.handle_battery_saver(args['on'])
    elif args['battery'] and args['level']:
        adb_enhanced.handle_battery_level(int(args['<percentage>']))
    elif args['battery'] and args['reset']:
        adb_enhanced.handle_battery_reset()

    elif args['doze']:
        adb_enhanced.handle_doze(args['on'])
    elif args['jank']:
        adb_enhanced.handle_get_jank(args['<app_name>'])
    elif args['devices']:
        adb_enhanced.handle_list_devices()
    elif args['top-activity']:
        adb_enhanced.print_top_activity()
    elif args['dump-ui']:
        adb_enhanced.dump_ui(args['<xml_file>'])
    elif args['force-stop']:
        app_name = args['<app_name>']
        adb_enhanced.force_stop(app_name)
    elif args['clear-data']:
        app_name = args['<app_name>']
        adb_enhanced.clear_disk_data(app_name)

    # mobile-data
    elif args['mobile-data'] and args['saver']:
        adb_enhanced.handle_mobile_data_saver(args['on'])
    elif args['mobile-data']:
        adb_enhanced.handle_mobile_data(args['on'])

    elif args['wifi']:
        adb_enhanced.set_wifi(args['on'])

    elif args['rtl']:  # This is not working as expected
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
        adb_enhanced.toggle_show_taps(args['on'])
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
        app_name = args['<app_name>']
        permission_group = adb_enhanced.get_permission_group(args)

        permissions = adb_enhanced.get_permissions_in_permission_group(permission_group)
        if not permissions and \
                adb_enhanced.is_permission_group_unavailable_after_api_29(permission_group) and \
                adb_enhanced.get_device_android_api_version() >= 29:
            print_error_and_exit('Android has made contacts group empty on API 29 and beyond, '
                                 'your device version is %d' %
                                 adb_enhanced.get_device_android_api_version())
        elif not permissions:
            print_error_and_exit('No permissions found in permissions group: %s' % permission_group)
        adb_enhanced.grant_or_revoke_runtime_permissions(
            app_name, args['grant'], permissions)

    elif args['notifications'] and args['list']:
        adb_enhanced.print_notifications()

    # apps list
    elif args['apps'] and args['list'] and args['all']:
        adb_enhanced.print_list_all_apps()
    elif args['apps'] and args['list'] and args['system']:
        adb_enhanced.list_system_apps()
    elif args['apps'] and args['list'] and args['third-party']:
        adb_enhanced.print_list_non_system_apps()
    elif args['apps'] and args['list'] and args['debug']:
        adb_enhanced.print_list_debug_apps()
    elif args['apps'] and args['list'] and args['backup-enabled']:
        adb_enhanced.print_allow_backup_apps()

    # standby bucket
    elif args['standby-bucket'] and args['get']:
        adb_enhanced.get_standby_bucket(args['<app_name>'])
    elif args['standby-bucket'] and args['set']:
        adb_enhanced.set_standby_bucket(args['<app_name>'], adb_enhanced.calculate_standby_mode(args))

    elif args['restrict-background']:
        adb_enhanced.apply_or_remove_background_restriction(args['<app_name>'], args['true'])
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
        adb_enhanced.launch_app(args['<app_name>'])
    elif args['stop']:
        adb_enhanced.stop_app(args['<app_name>'])
    elif args['restart']:
        app_name = args['<app_name>']
        adb_enhanced.force_stop(app_name)
        adb_enhanced.launch_app(app_name)

    # app
    elif args['app'] and args['info']:
        adb_enhanced.print_app_info(args['<app_name>'])
    elif args['app'] and args['path']:
        adb_enhanced.print_app_path(args['<app_name>'])
    elif args['app'] and args['signature']:
        adb_enhanced.print_app_signature(args['<app_name>'])
    elif args['app'] and args['backup']:
        app_name = args['<app_name>']
        backup_tar_file_path = args['<backup_tar_file_path>']
        if not backup_tar_file_path:
            backup_tar_file_path = '%s_backup.tar' % app_name
        adb_enhanced.perform_app_backup(app_name, backup_tar_file_path)

    # dark mode
    elif args['dark'] and args['mode']:
        if args['on']:
            adb_enhanced.set_dark_mode(True)
        elif args['off']:
            adb_enhanced.set_dark_mode(False)

    elif args['screen'] and args['on']:
        adb_enhanced.switch_screen(adb_enhanced.SCREEN_ON)
    elif args['screen'] and args['off']:
        adb_enhanced.switch_screen(adb_enhanced.SCREEN_OFF)
    elif args['screen'] and args['toggle']:
        adb_enhanced.switch_screen(adb_enhanced.SCREEN_TOGGLE)

    elif args['install']:
        file_path = args['<file_path>']
        adb_enhanced.perform_install(file_path)
    elif args['uninstall']:
        adb_enhanced.perform_uninstall(args['<app_name>'], args['--first-user'])

    elif args['enable']:
        if args['wireless'] and args['debugging']:
            adb_enhanced.enable_wireless_debug()

    elif args['disable']:
        if args['wireless'] and args['debugging']:
            adb_enhanced.disable_wireless_debug()

    # alarm
    elif args['alarm'] and args['all']:
        adb_enhanced.alarm_manager(adb_enhanced.AlarmEnum.ALL)
    elif args['alarm'] and args['history']:
        adb_enhanced.alarm_manager(adb_enhanced.AlarmEnum.HISTORY)
    elif args['alarm'] and args['pending']:
        adb_enhanced.alarm_manager(adb_enhanced.AlarmEnum.PENDING)
    elif args['alarm'] and args['top']:
        adb_enhanced.alarm_manager(adb_enhanced.AlarmEnum.TOP)

    elif args['location']:
        adb_enhanced.toggle_location(args['on'])

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


def get_generic_options_from_args(args):
    options = ''
    if args['--emulator']:
        options += '-e '
    if args['--device']:
        options += '-d '
    if args['--serial']:
        options += '-s %s ' % args['--serial']
    return options


def get_version():
    dir_of_this_script = os.path.split(__file__)[0]
    version_file_path = os.path.join(dir_of_this_script, _VERSION_FILE_NAME)
    with open(version_file_path, 'r', encoding='UTF-8') as file_handle:
        return file_handle.read().strip()


def _using_python2():
    return sys.version_info < (3, 0)


def _fail_with_python2_warning():
    msg = ('You are using Python 2\nADB-enhanced no longer supports Python 2.\n' +
           'Install Python 3 and then re-install this tool using\n' +
           '\"sudo pip uninstall adb-enhanced && sudo pip3 install adb-enhanced\"')
    print_error_and_exit(msg)


if __name__ == '__main__':
    main()
