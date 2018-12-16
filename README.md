# ADB Enhanced [![Downloads](http://pepy.tech/badge/adb-enhanced)](http://pepy.tech/project/adb-enhanced) [![PyPI version](https://badge.fury.io/py/adb-enhanced.svg)](https://badge.fury.io/py/adb-enhanced) [![Build Status](https://img.shields.io/travis/ashishb/adb-enhanced/master.svg?label=Travis%20CI)](https://travis-ci.org/ashishb/adb-enhanced) [![CircleCI](https://img.shields.io/circleci/project/github/ashishb/adb-enhanced.svg?label=Circle%20CI)](https://circleci.com/gh/ashishb/adb-enhanced)

![Logo](docs/logo.png)

Swiss-army knife for Android testing and development. A command-line interface to trigger various scenarios like screen rotation, battery saver mode, data saver mode, doze mode, permission grant/revocation.

## Release announcement
See [Release announcement](https://ashishb.net/tech/introducing-adb-enhanced-a-swiss-army-knife-for-android-development/)


## Installation
`sudo pip3 install adb-enhanced`

## Note
1. `sudo pip install adb-enhanced` for python2 based install works as well but I would recommend moving to python3 since I will deprecate python2 support after Dec 31, 2018.
2. If you don't have sudo access or you are installing without sudo then `adbe` might not be configured correctly in the path.
3. To setup bash/z-sh auto-completion, execute `sudo pip3 install infi.docopt-completion && docopt-completion $(which adbe)` after installing adb-enhanced.


## Examples

	
### Device configuration

* Turn doze mode on

	`adbe doze on`

* Turn mobile-data off

	`adbe mobile-data off`

* Turn on battery saver

	`adbe battery saver on`

* Don't keep activities in the background

	`adbe dont-keep-activities on`
	
* Take a screenshot
	`adbe screenshot ~/Downloads/screenshot1.png`
	
* Take a video
	`adbe screenrecord video.mp4 # Press ^C when finished`
	
### Permisions


* Grant storage-related runtime permissions

	`adbe permissions grant com.example storage`

* Revoke storage-related runtime permissions

	`adbe permissions revoke com.example storage`
	
	
### Interacting with app
* Start an app

	`adbe start com.example`

* Kill an app

	`adbe force-stop com.example`
	
* Clear app data - equivalent of uninstall and reinstall

	`adbe clear-data com.example`
	
* ls/cat/rm any file without worrying about adding "run-as" or "su root"

	`adbe ls /data/data/com.example/databases`  # Works as long as com.example is a debuggable package, or shell has the root permission or directory has been made publicly accessible	
	
### Device info

* Detailed device info including model name, Android API version etc, device serial

	```
	$ adbe devices
	Unlock Device "dcc54112" and give USB debugging access to this PC/Laptop by unlocking and reconnecting the device. More info about this device: "unauthorized usb:339869696X transport_id:17"

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

### App info

* Detailed information about app version, target SDK version, permissions (requested, granted, denied), installer package name etc.

	```
	$ adbe app info com.google.android.youtube
	App name: com.google.android.youtube
	Version: 12.17.41
	Version Code: 121741370
	Is debuggable: False
	Min SDK version: 21
	Target SDK version: 26
	
	Permissions:
	
	Install time granted permissions:
	com.google.android.c2dm.permission.RECEIVE
	android.permission.USE_CREDENTIALS
	com.google.android.providers.gsf.permission.READ_GSERVICES
	com.google.android.youtube.permission.C2D_MESSAGE
	android.permission.MANAGE_ACCOUNTS
	android.permission.SYSTEM_ALERT_WINDOW
	android.permission.NFC
	android.permission.CHANGE_NETWORK_STATE
	android.permission.RECEIVE_BOOT_COMPLETED
	com.google.android.gms.permission.AD_ID_NOTIFICATION
	android.permission.INTERNET
	android.permission.GET_PACKAGE_SIZE
	android.permission.ACCESS_NETWORK_STATE
	android.permission.VIBRATE
	android.permission.ACCESS_WIFI_STATE
	android.permission.WAKE_LOCK
	
	Runtime Permissions not granted and not yet requested:
	android.permission.WRITE_EXTERNAL_STORAGE
	android.permission.MANAGE_DOCUMENTS
	android.permission.GET_ACCOUNTS
	android.permission.CAMERA
	android.permission.RECORD_AUDIO
	android.permission.READ_CONTACTS
	android.permission.ACCESS_FINE_LOCATION
	android.permission.ACCESS_COARSE_LOCATION
	android.permission.READ_PHONE_STATE
	android.permission.SEND_SMS
	android.permission.RECEIVE_SMS
	com.sec.android.provider.badge.permission.READ
	com.sec.android.provider.badge.permission.WRITE
	com.htc.launcher.permission.READ_SETTINGS
	com.htc.launcher.permission.UPDATE_SHORTCUT
	com.sonyericsson.home.permission.BROADCAST_BADGE
	com.sonymobile.home.permission.PROVIDER_INSERT_BADGE
	android.permission.READ_EXTERNAL_STORAGE
	
	Installer package name: None
	```

* App backup to a tar file unlike the Android-specific .ab format

	```
	$ adbe app backup com.google.android.youtube backup.tar
	```

### Usage
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

### Options

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
    
## Python3 migration timeline

- Nov 27, 2017 - Code is Python3 compatible
- Jan 18, 2018 - pip (python package manager) has the updated version which is Python3 compatible
- Nov 15, 2018 - Python2 based installation discouraged. Python3 is recommended.
- Dec 31, 2018 - Python2 will not be officially supported after Dec 31, 2018.

## Testing
```
python -m pytest -v tests/adbe_tests.py  # Python2 tests
python3 -m pytest -v tests/adbe_tests.py  # Python3 tests
```


## Relase a new build
A new build can be released using [`release/release_new_build.sh`](https://github.com/ashishb/adb-enhanced/blob/master/release/release_new_build.sh) script.

Note: The inspiration of this project came from [android-scripts](https://github.com/dhelleberg/android-scripts).

