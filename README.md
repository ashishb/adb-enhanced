# adb-enhanced
ADB enhanced for developers, inspired from [android-scripts](https://github.com/dhelleberg/android-scripts)

## Python3 compatibility
As of Nov 27, 2017, the code is python3 compatible and as of Jan 18, 2018, pip (python package manager) also has the updated version 

# Installation
pip install adb-enhanced

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

# Usage:
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
    adbe.py [options] permission-groups list all
    adbe.py [options] permissions list (all | dangerous)
    adbe.py [options] permissions (grant | revoke) <package_name> (calendar | camera | contacts | location | microphone | phone | sensors | sms | storage) - grant and revoke runtime permissions

# Options:
    -e, --emulator          directs command to the only running emulator
    -d, --device            directs command to the only connected "USB" device
    -s, --serial SERIAL     directs command to the device or emulator with the given serial number or qualifier.
                            Overrides ANDROID_SERIAL environment
