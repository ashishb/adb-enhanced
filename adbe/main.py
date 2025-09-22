#!/usr/bin/env python3

import os
import sys
import typing
from pathlib import Path

import docopt

try:
    # First try local import for development
    from adbe import adb_enhanced, adb_helper
    from adbe.output_helper import print_error_and_exit, set_verbose
# Python 3.6 onwards, this throws ModuleNotFoundError
except ModuleNotFoundError:
    # This works when the code is executed as a part of the module
    import adb_enhanced
    import adb_helper
    from output_helper import print_error_and_exit, set_verbose

# List of things which this enhanced adb tool does as of today.
USAGE_STRING = """
ADB-Enhanced (adbe) by Ashish Bhatia
https://github.com/ashishb/adb-enhanced
Swiss-army knife for Android testing and development

Usage:
    adbe [options] airplane (on | off)
    adbe [options] alarm (all | top | pending | history)
    adbe [options] animations (on | off)
    adbe [options] app backup <app_name> [<backup_tar_file_path>]
    adbe [options] app info <app_name>
    adbe [options] app path <app_name>
    adbe [options] app signature <app_name>
    adbe [options] apps list (all | system | third-party | debug | backup-enabled)
    adbe [options] battery level <percentage>
    adbe [options] battery reset
    adbe [options] battery saver (on | off)
    adbe [options] cat <file_path>
    adbe [options] clear-data <app_name>
    adbe [options] dark mode (on | off)
    adbe [options] debug-app (set [-w] [-p] <app_name> | clear)
    adbe [options] devices
    adbe [options] display size
    adbe [options] display size (ldpi | mdpi | hdpi | xhdpi | xxhdpi | xxxhdpi)
    adbe [options] (enable | disable) wireless debugging
    adbe [options] dont-keep-activities (on | off)
    adbe [options] doze (on | off)
    adbe [options] dump-ui <xml_file>
    adbe [options] force-stop <app_name>
    adbe [options] gfx (on | off | lines)
    adbe [options] input-text <text>
    adbe [options] install <file_path>
    adbe [options] jank <app_name>
    adbe [options] layout (on | off)
    adbe [options] location (on | off)
    adbe [options] ls [-a] [-l] [-R|-r] <file_path>
    adbe [options] mobile-data (on | off)
    adbe [options] mobile-data saver (on | off)
    adbe [options] mv [-f] <src_path> <dest_path>
    adbe [options] notifications list
    adbe [options] open-url <url>
    adbe [options] overdraw (on | off | deut)
    adbe [options] permission-groups list all
    adbe [options] permissions (grant | revoke) <app_name> (calendar | camera | contacts | location | microphone | notifications | phone | sensors | sms | storage)
    adbe [options] permissions list (all | dangerous)
    adbe [options] press back
    adbe [options] press media (next | previous | play | pause)
    adbe [options] pull [-a] <file_path_on_android>
    adbe [options] pull [-a] <file_path_on_android> <file_path_on_machine>
    adbe [options] push <file_path_on_machine> <file_path_on_android>
    adbe [options] restart <app_name>
    adbe [options] restrict-background (true | false) <app_name>
    adbe [options] rm [-f] [-R|-r] <file_path>
    adbe [options] rotate (landscape | portrait | left | right)
    adbe [options] rtl (on | off)
    adbe [options] screen (on | off | toggle)
    adbe [options] screenrecord <filename.mp4>
    adbe [options] screenshot <filename.png>
    adbe [options] show-taps (on | off)
    adbe [options] standby-bucket get <app_name>
    adbe [options] standby-bucket set <app_name> (active | working_set | frequent | rare)
    adbe [options] start <app_name>
    adbe [options] stay-awake-while-charging (on | off)
    adbe [options] stop <app_name>
    adbe [options] top-activity
    adbe [options] uninstall [--first-user] <app_name>
    adbe [options] wifi (on | off)

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

_VERSION_FILE_NAME = "version.txt"


def main() -> None:
    if _using_python2():
        _fail_with_python2_warning()

    args: dict[str, typing.Any] = docopt.docopt(USAGE_STRING, version=_get_version())
    set_verbose(enabled=args["--verbose"])

    _validate_options(args)
    options = _get_generic_options_from_args(args)
    if options:
        adb_prefix = f"{adb_helper.get_adb_prefix()} {options}"
        adb_helper.set_adb_prefix(adb_prefix)

    action_dict = _get_actions(args)

    for keys, action in action_dict.items():
        all_keys_match = True
        for key in keys:
            if not args[key]:
                all_keys_match = False
                break
        if all_keys_match:
            action()
            sys.exit(0)

    print_error_and_exit('Not implemented: "{}"'.format(" ".join(sys.argv)))


def _get_actions(args: dict[str, typing.Any]) -> dict[tuple[str, str], typing.Callable]:
    app_name = args["<app_name>"]
    return {
        # Airplane mode
        ("airplane", "on"): lambda: adb_enhanced.handle_airplane(turn_on=True),
        ("airplane", "off"): lambda: adb_enhanced.handle_airplane(turn_on=False),

        # Alarm
        ("alarm", "all"): lambda: adb_enhanced.alarm_manager(adb_enhanced.AlarmEnum.ALL),
        ("alarm", "history"): lambda: adb_enhanced.alarm_manager(adb_enhanced.AlarmEnum.HISTORY),
        ("alarm", "pending"): lambda: adb_enhanced.alarm_manager(adb_enhanced.AlarmEnum.PENDING),
        ("alarm", "top"): lambda: adb_enhanced.alarm_manager(adb_enhanced.AlarmEnum.TOP),

        # Animations
        ("animations", "on"): lambda: adb_enhanced.toggle_animations(turn_on=True),
        ("animations", "off"): lambda: adb_enhanced.toggle_animations(turn_on=False),

        # App-related misc
        ("app", "backup"): lambda: _perform_backup(app_name, args["<backup_tar_file_path>"]),
        ("app", "info"): lambda: adb_enhanced.print_app_info(app_name),
        ("app", "path"): lambda: adb_enhanced.print_app_path(app_name),
        ("app", "signature"): lambda: adb_enhanced.print_app_signature(app_name),

        # App listing
        ("apps", "list", "all"): adb_enhanced.print_list_all_apps,
        ("apps", "list", "system"): adb_enhanced.list_system_apps,
        ("apps", "list", "third-party"): adb_enhanced.print_list_non_system_apps,
        ("apps", "list", "debug"): adb_enhanced.print_list_debug_apps,
        ("apps", "list", "backup-enabled"): adb_enhanced.print_allow_backup_apps,

        # Input-related
        # Ref: https://developer.android.com/reference/android/view/KeyEvent#KEYCODE_BACK
        ("press", "back"): lambda: adb_enhanced.press_key("KEYCODE_BACK"),
        # Ref: https://developer.android.com/reference/android/view/KeyEvent#KEYCODE_MEDIA_NEXT
        ("press", "media", "next"): lambda: adb_enhanced.press_key("KEYCODE_MEDIA_NEXT"),
        ("press", "media", "previous"): lambda: adb_enhanced.press_key("KEYCODE_MEDIA_PREVIOUS"),
        ("press", "media", "play"): lambda: adb_enhanced.press_key("KEYCODE_MEDIA_PLAY"),
        ("press", "media", "pause"): lambda: adb_enhanced.press_key("KEYCODE_MEDIA_PAUSE"),
        ("input-text",): lambda: adb_enhanced.input_text(args["<text>"]),
        ("open-url",): lambda: adb_enhanced.open_url(args["<url>"]),

        # Battery-related
        ("battery", "level"): lambda: adb_enhanced.handle_battery_level(int(args["<percentage>"])),
        ("battery", "reset"): adb_enhanced.handle_battery_reset,
        ("battery", "saver", "on"): lambda: adb_enhanced.handle_battery_saver(turn_on=True),
        ("battery", "saver", "off"): lambda: adb_enhanced.handle_battery_saver(turn_on=False),
        ("cat",): lambda: adb_enhanced.cat_file(args["<file_path>"]),

        # Dark mode
        ("dark", "mode", "on"): lambda: adb_enhanced.set_dark_mode(force=True),
        ("dark", "mode", "off"): lambda: adb_enhanced.set_dark_mode(force=False),

        # List devices
        ("devices",): adb_enhanced.handle_list_devices,

        # Display size related
        # https://developer.android.com/training/multiscreen/screendensities
        ("display", "size", "ldpi"): lambda: adb_enhanced.set_display_size(120),
        ("display", "size", "mdpi"): lambda: adb_enhanced.set_display_size(160),
        ("display", "size", "hdpi"): lambda: adb_enhanced.set_display_size(240),
        ("display", "size", "xhdpi"): lambda: adb_enhanced.set_display_size(320),
        ("display", "size", "xxhdpi"): lambda: adb_enhanced.set_display_size(480),
        ("display", "size", "xxxhdpi"): lambda: adb_enhanced.set_display_size(640),
        ("display", "size"): adb_enhanced.print_display_size,

        # GFX
        ("gfx", "on"): lambda: adb_enhanced.handle_gfx("on"),
        ("gfx", "off"): lambda: adb_enhanced.handle_gfx("off"),
        ("gfx", "lines"): lambda: adb_enhanced.handle_gfx("lines"),

        # Apk install
        ("install",): lambda: adb_enhanced.perform_install(args["<file_path>"]),
        # Apk uninstall
        ("uninstall",): lambda: adb_enhanced.perform_uninstall(app_name, is_first_user=args["--first-user"]),
        # Clear data
        ("clear-data",): lambda: adb_enhanced.clear_disk_data(app_name),

        # Mobile Data
        ("mobile-data", "saver", "on"): lambda: adb_enhanced.handle_mobile_data_saver(turn_on=True),
        ("mobile-data", "saver", "off"): lambda: adb_enhanced.handle_mobile_data_saver(turn_on=False),
        ("mobile-data", "on"): lambda: adb_enhanced.handle_mobile_data(turn_on=True),
        ("mobile-data", "off"): lambda: adb_enhanced.handle_mobile_data(turn_on=False),

        # Layout
        ("layout", "on"): lambda: adb_enhanced.handle_layout(turn_on=True),
        ("layout", "off"): lambda: adb_enhanced.handle_layout(turn_on=False),

        # Location
        ("location", "on"): lambda: adb_enhanced.toggle_location(turn_on=True),
        ("location", "off"): lambda: adb_enhanced.toggle_location(turn_on=False),
        ("notifications", "list"): adb_enhanced.print_notifications,

        # Overdraw
        ("overdraw", "on"): lambda: adb_enhanced.handle_overdraw("on"),
        ("overdraw", "off"): lambda: adb_enhanced.handle_overdraw("off"),
        ("overdraw", "deut"): lambda: adb_enhanced.handle_overdraw("deut"),

        # Permissions related
        ("permissions", "grant"): lambda: _grant_revoke_permissions(app_name, args),
        ("permissions", "revoke"): lambda: _grant_revoke_permissions(app_name, args),
        ("permission-groups", "list", "all"): adb_enhanced.list_permission_groups,
        ("permissions", "list", "all"): lambda: adb_enhanced.list_permissions(dangerous_only_permissions=False),
        ("permissions", "list", "dangerous"): lambda: adb_enhanced.list_permissions(dangerous_only_permissions=True),

        # Pull files
        ("pull",): lambda: adb_enhanced.pull_file(
            args["<file_path_on_android>"], args["<file_path_on_machine>"], copy_ancillary=args["-a"]),
        ("push",): lambda: adb_enhanced.push_file(
            args["<file_path_on_machine>"], args["<file_path_on_android>"]),
        ("restrict-background", "true"): lambda: adb_enhanced.apply_or_remove_background_restriction(app_name, set_restriction=True),
        ("restrict-background", "false"): lambda: adb_enhanced.apply_or_remove_background_restriction(app_name, set_restriction=False),

        # Rotate
        ("rotate", "portrait"): lambda: adb_enhanced.handle_rotate("portrait"),
        ("rotate", "landscape"): lambda: adb_enhanced.handle_rotate("landscape"),
        ("rotate", "left"): lambda: adb_enhanced.handle_rotate("left"),
        ("rotate", "right"): lambda: adb_enhanced.handle_rotate("right"),

        # RTL settings are not working as expected
        ("rtl", "on"): lambda: adb_enhanced.force_rtl(turn_on=True),
        ("rtl", "off"): lambda: adb_enhanced.force_rtl(turn_on=False),

        # Files related
        ("mv",): lambda: adb_enhanced.move_file(args["<src_path>"], args["<dest_path>"], force=args["-f"]),
        ("rm",): lambda: adb_enhanced.delete_file(args["<file_path>"], force=args["-f"], recursive=args["-R"] or args["-r"]),
        # Always include hidden files, -a is left for backward-compatibility but is a no-op now.
        ("ls",): lambda: adb_enhanced.list_directory(
            args["<file_path>"], long_format=args["-l"], recursive=args["-R"] or args["-r"],
            include_hidden_files=True),
        # Screen
        ("screen", "on"): lambda: adb_enhanced.switch_screen(adb_enhanced.SCREEN_ON),
        ("screen", "off"): lambda: adb_enhanced.switch_screen(adb_enhanced.SCREEN_OFF),
        ("screen", "toggle"): lambda: adb_enhanced.switch_screen(adb_enhanced.SCREEN_TOGGLE),
        ("stay-awake-while-charging", "on"): lambda: adb_enhanced.stay_awake_while_charging(turn_on=True),
        ("stay-awake-while-charging", "off"): lambda: adb_enhanced.stay_awake_while_charging(turn_on=False),

        # Standby bucket
        ("standby-bucket", "get"): lambda: adb_enhanced.get_standby_bucket(app_name),
        ("standby-bucket", "set"): lambda: adb_enhanced.set_standby_bucket(
            app_name, adb_enhanced.calculate_standby_mode(args)),
        # Doze
        ("doze", "on"): lambda: adb_enhanced.handle_doze(turn_on=True),
        ("doze", "off"): lambda: adb_enhanced.handle_doze(turn_on=False),

        # App start
        ("start",): lambda: adb_enhanced.launch_app(app_name),
        ("stop",): lambda: adb_enhanced.stop_app(app_name),
        ("restart",): lambda: (adb_enhanced.force_stop(app_name), adb_enhanced.launch_app(app_name)),

        # Wi-Fi
        ("wifi", "on"): lambda: adb_enhanced.set_wifi(turn_on=True),
        ("wifi", "off"): lambda: adb_enhanced.set_wifi(turn_on=False),

        # Wireless debugging
        ("wireless", "debugging", "enable"): adb_enhanced.enable_wireless_debug,
        ("wireless", "debugging", "disable"): adb_enhanced.disable_wireless_debug,

        ("force-stop",): lambda: adb_enhanced.force_stop(app_name),

        # Configure UI
        ("dont-keep-activities", "on"): lambda: adb_enhanced.handle_dont_keep_activities_in_background(turn_on=True),
        ("dont-keep-activities", "off"): lambda: adb_enhanced.handle_dont_keep_activities_in_background(turn_on=False),
        ("show-taps", "on"): lambda: adb_enhanced.toggle_show_taps(turn_on=True),
        ("show-taps", "off"): lambda: adb_enhanced.toggle_show_taps(turn_on=False),

        # Fetching info from UI
        ("dump-ui",): lambda: adb_enhanced.dump_ui(args["<xml_file>"]),
        ("jank",): lambda: adb_enhanced.handle_get_jank(app_name),
        ("top-activity",): adb_enhanced.print_top_activity,
        ("screenshot", ): lambda: adb_enhanced.dump_screenshot(args["<filename.png>"]),
        ("screenrecord",): lambda: adb_enhanced.dump_screenrecord(args["<filename.mp4>"]),

        # Debug app
        ("debug-app", "set"): lambda: adb_enhanced.set_debug_app(
            args["<app_name>"], wait_for_debugger=args["-w"], persistent=args["-p"]),
        ("debug-app", "clear"): lambda: adb_enhanced.clear_debug_app,
    }


def _grant_revoke_permissions(app_name: str, args: dict[str, typing.Any]) -> None:
    permission_group = adb_enhanced.get_permission_group(args)
    permissions = adb_enhanced.get_permissions_in_permission_group(permission_group)
    if not permissions and \
            adb_enhanced.is_permission_group_unavailable_after_api_29(permission_group) and \
            adb_enhanced.get_device_android_api_version() >= 29:
        print_error_and_exit("Android has made some permission group empty on API 29 and beyond, "
                             f"your device version is {adb_enhanced.get_device_android_api_version()}")
    elif not permissions:
        print_error_and_exit(f"No permissions found in permissions group: {permission_group}")
    adb_enhanced.grant_or_revoke_runtime_permissions(
        app_name, action_type="grant" if args["grant"] else "revoke", permissions=permissions)


def _perform_backup(app_name: str, backup_tar_file_path: str | None) -> None:
    if not backup_tar_file_path:
        backup_tar_file_path = f"{app_name}_backup.tar"
    adb_enhanced.perform_app_backup(app_name, backup_tar_file_path)


def _validate_options(args: dict[str, typing.Any]) -> None:
    count = 0
    if args["--emulator"]:
        count += 1
    if args["--device"]:
        count += 1
    if args["--serial"]:
        count += 1
    if count > 1:
        print_error_and_exit("Only one out of -e, -d, or -s can be provided")


def _get_generic_options_from_args(args: dict[str, typing.Any]) -> str:
    options = ""
    if args["--emulator"]:
        options += "-e "
    if args["--device"]:
        options += "-d "
    if args["--serial"]:
        options += f'-s {args["--serial"]} '
    return options


def _get_version() -> str:
    dir_of_this_script = os.path.split(__file__)[0]
    version_file_path = Path(dir_of_this_script) / _VERSION_FILE_NAME
    return Path(version_file_path).read_text(encoding="UTF-8").strip()


def _using_python2() -> bool:
    return sys.version_info < (3, 0)


def _fail_with_python2_warning() -> None:
    msg = ("You are using Python 2\nADB-enhanced no longer supports Python 2.\n"
           "Install Python 3 and then re-install this tool using\n"
           '"sudo pip uninstall adb-enhanced && sudo pip3 install adb-enhanced"')
    print_error_and_exit(msg)


if __name__ == "__main__":
    main()
