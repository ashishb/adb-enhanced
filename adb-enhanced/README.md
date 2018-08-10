# adb-enhanced [![Downloads](http://pepy.tech/badge/adb-enhanced)](http://pepy.tech/project/adb-enhanced) [![PyPI version](https://badge.fury.io/py/adb-enhanced.svg)](https://badge.fury.io/py/adb-enhanced)

Swiss-army knife for Android testing and development. A command-line interface to trigger various scenarios like screen rotation, battery saver mode, data saver mode, doze mode, permission grant/revocation.

# Release announcement
See [Release announcement](https://ashishb.net/tech/introducing-adb-enhanced-a-swiss-army-knife-for-android-development/)


# Installation
`sudo pip3 install adb-enhanced`

## Note
1. `sudo pip install adb-enhanced` for python2 based install works as well but I would recommend moving to python3 since I might deprecate python2 support at some point.
2. If you don't have sudo access or you are installing without sudo then `adbe` might not be configured correctly in the path.


# Examples

* Launch an app

	`adbe start com.example`

* Kill an app

	`adbe force-stop com.example`
	
* Clear app data - equivalent of uninstall and reinstall

	`adbe clear-data com.example`

* Turn doze mode on

	`adbe doze on`

* Turn mobile-data off

	`adbe mobile-data off`

* Turn on battery saver

	`adbe battery saver on`

* Don't keep activities in the background

	`adbe dont-keep-activities on`

* Grant storage-related runtime permissions

	`adbe permissions grant com.example storage`

* Revoke storage-related runtime permissions

	`adbe permissions revoke com.example storage`

* ls/cat any file without worrying about adding "run-as"

	`adbe ls /data/data/com.example/databases`  # Works as long as com.example is a debuggable package

* Detailed device info including model name, Android API version etc, device serial

	```
	$ adbe devices
	Serial ID: dcc54111
	Manufacturer: OnePlus
	Model: ONEPLUS A5000 (OnePlus 5T)
	Release: 8.1.0
	SDK version: 27
	CPU: arm64-v8a
	
	Serial ID: emulator-5554
	Manufacturer: unknown
	Model: Android SDK built for x86
	Release: 4.4.2
	SDK version: 19
	CPU: x86
	```


# Usage

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
    adbe.py [options] dump-ui <xml_file>
    adbe.py [options] mobile-data (on | off)
    adbe.py [options] mobile-data saver (on | off)
    adbe.py [options] rtl (on | off)
    adbe.py [options] screenshot <filename.png>
    adbe.py [options] screenrecord <filename.mp4>
    adbe.py [options] dont-keep-activities (on | off)
    adbe.py [options] animations (on | off)
    adbe.py [options] stay-awake-while-charging (on | off)
    adbe.py [options] input-text <text>
    adbe.py [options] press back
    adbe.py [options] open-url <url>
    adbe.py [options] permission-groups list all
    adbe.py [options] permissions list (all | dangerous)
    adbe.py [options] permissions (grant | revoke) <app_name> (calendar | camera | contacts | location | microphone | phone | sensors | sms | storage)
    adbe.py [options] standby-bucket get <app_name>
    adbe.py [options] standby-bucket set <app_name> (active | working_set | frequent | rare)
    adbe.py [options] restrict-background (true | false) <app_name>
    adbe.py [options] ls [-l] [-R] <file_path>
    adbe.py [options] rm [-f] [-R] [-r] <file_path>
    adbe.py [options] pull [-a] <remote>
    adbe.py [options] pull [-a] <remote> <local>
    adbe.py [options] cat <file_path>
    adbe.py [options] start <app_name>
    adbe.py [options] stop <app_name>
    adbe.py [options] restart <app_name>
    adbe.py [options] force-stop <app_name>
    adbe.py [options] clear-data <app_name>
    adbe.py [options] app-info <app_name>
    adbe.py [options] app-path <app_name>
    adbe.py [options] app-signature <app_name>


# Options

    -e, --emulator          directs the command to the only running emulator
    -d, --device            directs the command to the only connected "USB" device
    -s, --serial SERIAL     directs the command to the device or emulator with the given serial number or qualifier.
                            Overrides ANDROID_SERIAL environment variable.
    -l                      For long list format, only valid for "ls" command
    -R                      For recursive directory listing, only valid for "ls" command
    -v, --verbose           Verbose mode
    
## Python3 compatibility

As of Nov 27, 2017, the code is python3 compatible, and as of Jan 18, 2018, pip (python package manager) has the updated version.

Note: The inspiration of this project came from [android-scripts](https://github.com/dhelleberg/android-scripts).

