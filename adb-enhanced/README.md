# adb-enhanced
Swiss-army knife for android testing and development, inspired from [android-scripts](https://github.com/dhelleberg/android-scripts)

# Installation
`pip install adb-enhanced`

# Examples

* Turn doze mode on

`adbe doze on`

* Turn mobile-data off

`adbe mobile-data off`

* Turn on battery saver

`adbe battery saver on`

* Don't keep activities in the background

`adbe dont-keep-activities on`

* Grant storage-related runtime permissions

`adbe permissions grant com.example.android storage`

* Revoke storage-related runtime permissions

`adbe permissions revoke com.example.android storage`

* ls/cat any file without worrying about adding "run-as"

`adbe ls /data/data/com.example/databases`  # Works as long as com.example is a debuggable package

* Launch an app
`adbe start com.example`

# Usage:

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
    adbe.py [options] mobile-data (on | off)
    adbe.py [options] mobile-data saver (on | off)
    adbe.py [options] rtl (on | off)
    adbe.py [options] screenshot <filename.png>
    adbe.py [options] screenrecord <filename.mp4>
    adbe.py [options] dont-keep-activities (on | off)
    adbe.py [options] input-text <text>
    adbe.py [options] press back
    adbe.py [options] permission-groups list all
    adbe.py [options] permissions list (all | dangerous)
    adbe.py [options] permissions (grant | revoke) <app_name> (calendar | camera | contacts | location | microphone | phone | sensors | sms | storage)
    adbe.py [options] restrict-background (true | false) <app_name>
    adbe.py [options] ls [-l] [-R] <file_path>
    adbe.py [options] cat <file_path>
    adbe.py [options] start <app_name>
    adbe.py [options] stop <app_name>
    adbe.py [options] force-stop <app_name>
    adbe.py [options] clear-data <app_name>
    adbe.py [options] app-info <app_name>
    adbe.py [options] print-apk-path <app_name>

# Options:

    -e, --emulator          directs command to the only running emulator
    -d, --device            directs command to the only connected "USB" device
    -s, --serial SERIAL     directs command to the device or emulator with the given serial number or qualifier.
                            Overrides ANDROID_SERIAL environment variable.
    -l                      For long list format, only valid for "ls" command
    -R                      For recursive directory listing, only valid for "ls" command
    -v, --verbose           Verbose mode
    
## Python3 compatibility

As of Nov 27, 2017, the code is python3 compatible and as of Jan 18, 2018, pip (python package manager) also has the updated version 
