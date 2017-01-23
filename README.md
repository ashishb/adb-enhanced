# adb-enhanced
ADB enhanced for developers

Usage:
    adbe.py [options] rotate (landscape | portrait)
    adbe.py [options] gfx (on | off | lines)
    adbe.py [options] overdraw ( on | off | deut )
    adbe.py [options] layout ( on | off )
    adbe.py [options] airplane ( on | off ) - This does not work on all the
devices as of now.
    adbe.py [options] battery level <percentage>
    adbe.py [options] battery saver (on | off)
    adbe.py [options] battery reset
    adbe.py [options] doze (on | off)
    adbe.py [options] jank <app_name>
    adbe.py [options] devices
    adbe.py [options] top-activity
    adbe.py [options] force-stop <app_name>
    adbe.py [options] clear-data <app_name>
    adbe.py [options] mobile-data ( on | off )
    adbe.py [options] mobile-data saver ( on | off )
    adbe.py [options] rtl ( on | off ) - This is not working properly as of now.
    adbe.py [options] screenshot <filename.png>
    adbe.py [options] dont-keep-activities ( on | off )

Options:
    -e, --emulator          directs command to the only running emulator
    -d, --device            directs command to the only connected "USB" device
    -s, --serial SERIAL     directs command to the device or emulator with the
given serial number or qualifier.
                            Overrides ANDROID_SERIAL environment variable.
    -v, --verbose           Verbose mode
