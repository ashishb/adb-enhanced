ADB Enhanced |Downloads| |PyPI version|
=======================================

.. figure:: docs/logo.png
   :alt: Logo

   Logo

ADB-Enhanced is a Swiss army knife for Android testing and development.

A command-line interface to trigger various scenarios like screen
rotation, battery saver mode, data saver mode, doze mode, and permission
grant/revocation. It’s a wrapper around ``adb`` and not a replacement.

|Lint Python| |Lint Markdown| |Lint YAML|

|InstallAdbeTest|

|AdbeInstallTests| |AdbeUnitTests|

|Install adb-enhanced via pip| |Install adb-enhanced via homebrew|

|AdbeUnitTests-Api16| |AdbeUnitTests-Api21| |AdbeUnitTests-Api22|
|AdbeUnitTests-Api23| |AdbeUnitTests-Api24| |AdbeUnitTests-Api25|
|AdbeUnitTests-Api26| |AdbeUnitTests-Api27| |AdbeUnitTests-Api28|
|AdbeUnitTests-Api29| |AdbeUnitTests-Api31| |AdbeUnitTests-Api30|
|AdbeUnitTests-Api31| |AdbeUnitTests-Api32| |AdbeUnitTests-Api33|
|AdbeUnitTests-Api34|

|asciicast|

Release announcement
--------------------

See `Release
announcement <https://ashishb.net/tech/introducing-adb-enhanced-a-swiss-army-knife-for-android-development/>`__

Installation
------------

Recommended
~~~~~~~~~~~

``sudo pip3 install adb-enhanced``

Alternative on Mac OS via Homebrew |Homebrew package|
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``brew install adb-enhanced``

Note
----

1. ``sudo pip install adb-enhanced`` works only for Python 3. Python 2
   is no longer supported.
2. If you don’t have sudo access or you are installing without sudo then
   ``adbe`` might not be configured correctly in the path.
3. To set up bash/z-sh auto-completion, execute
   ``sudo pip3 install infi.docopt-completion && docopt-completion $(which adbe)``
   after installing adb-enhanced.

Examples
--------

Device configuration
~~~~~~~~~~~~~~~~~~~~

-  Turn doze mode on

   ``adbe doze on``

-  Turn mobile-data off

   ``adbe mobile-data off``

-  Turn on battery saver

   ``adbe battery saver on``

-  Don’t keep activities in the background

   ``adbe dont-keep-activities on``

-  Take a screenshot ``adbe screenshot ~/Downloads/screenshot1.png``

-  Take a video ``adbe screenrecord video.mp4 # Press ^C when finished``

-  Turn Wireless Debug mode on ``adbe enable wireless debugging``

Permissions
~~~~~~~~~~~

-  Grant storage-related runtime permissions

   ``adbe permissions grant com.example storage``

-  Revoke storage-related runtime permissions

   ``adbe permissions revoke com.example storage``

Interacting with app
~~~~~~~~~~~~~~~~~~~~

-  Start an app

   ``adbe start com.example``

-  Kill an app

   ``adbe force-stop com.example``

-  Clear app data - equivalent of uninstall and reinstall

   ``adbe clear-data com.example``

-  ls/cat/rm any file without worrying about adding “run-as” or “su
   root”

   ``adbe ls /data/data/com.example/databases`` # Works as long as
   com.example is a debuggable package or shell has the root permission
   or directory has been made publicly accessible

Device info
~~~~~~~~~~~

-  Detailed device info including model name, Android API version etc,
   device serial

   .. code:: bash

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

App info
~~~~~~~~

-  Detailed information about app version, target SDK version,
   permissions (requested, granted, denied), installer package name,
   etc.

   .. code:: bash

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

-  App backup to a tar file unlike the Android-specific .ab format

   .. code:: bash

      $ adbe app backup com.google.android.youtube backup.tar
      you might have to confirm the backup manually on your device's screen, enter "00" as password...
      Successfully backed up data of app com.google.android.youtube to backup.tar

Usage
~~~~~

.. code:: bash

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
   adbe [options] devices
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

Options
~~~~~~~

.. code:: bash

   -e, --emulator          directs the command to the only running emulator
   -d, --device            directs the command to the only connected "USB" device
   -s, --serial SERIAL     directs the command to the device or emulator with the given serial number or qualifier.
                           Overrides ANDROID_SERIAL environment variable.
   -l                      For long list format, only valid for "ls" command
   -R                      For recursive directory listing, only valid for "ls" and "rm" command
   -r                      For delete file, only valid for "ls" and "rm" command
   -f                      For forced deletion of a file, only valid for "rm" command
   -v, --verbose           Verbose mode

Python3 migration timeline
--------------------------

-  Nov 27, 2017 - Code is Python3 compatible
-  Jan 18, 2018 - pip (python package manager) has the updated version
   which is Python3 compatible
-  Nov 15, 2018 - Python2 based installation discouraged. Python3 is
   recommended.
-  Dec 31, 2018 - Python2 will not be officially supported after Dec 31,
   2018.
-  May 7, 2020 - Python2 no longer works with the current master branch

Testing
-------

.. code:: bash

   make lint
   make test

Release a new build
-------------------

A new build can be released using
```release/release.py`` <https://github.com/ashishb/adb-enhanced/blob/master/release/release.py>`__
script. Build a test release via ``make release_debug``. Build a
production release via ``make release_production``

Updating docs for ReadTheDocs
-----------------------------

.. code:: bash

   make documentation

Note that this happens automatically during ``make release_production``.

You will have to do ``brew install pandoc`` if you are missing pandoc.

Note: The inspiration for this project came from
`android-scripts <https://github.com/dhelleberg/android-scripts>`__.

|Packaging status|

Contributors
------------

.. figure:: https://contrib.rocks/image?repo=ashishb/adb-enhanced
   :alt: GitHub contributors

   GitHub contributors

.. |Downloads| image:: https://static.pepy.tech/badge/adb-enhanced
   :target: https://pepy.tech/project/adb-enhanced
.. |PyPI version| image:: https://badge.fury.io/py/adb-enhanced.svg
   :target: https://badge.fury.io/py/adb-enhanced
.. |Lint Python| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/lint-python.yaml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/lint-python.yaml
.. |Lint Markdown| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/lint-markdown.yaml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/lint-markdown.yaml
.. |Lint YAML| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/lint-yaml.yaml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/lint-yaml.yaml
.. |InstallAdbeTest| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/install-adbe.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/install-adbe.yml
.. |AdbeInstallTests| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-installtests.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-installtests.yml
.. |AdbeUnitTests| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests.yml
.. |Install adb-enhanced via pip| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/install-adb-enhanced-from-pip.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/install-adb-enhanced-from-pip.yml
.. |Install adb-enhanced via homebrew| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/install-adb-enhanced-from-homebrew.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/install-adb-enhanced-from-homebrew.yml
.. |AdbeUnitTests-Api16| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api16.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api16.yml
.. |AdbeUnitTests-Api21| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api21.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api21.yml
.. |AdbeUnitTests-Api22| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api22.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api22.yml
.. |AdbeUnitTests-Api23| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api23.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api23.yml
.. |AdbeUnitTests-Api24| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api24.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api24.yml
.. |AdbeUnitTests-Api25| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api25.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api25.yml
.. |AdbeUnitTests-Api26| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api26.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api26.yml
.. |AdbeUnitTests-Api27| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api27.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api27.yml
.. |AdbeUnitTests-Api28| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api28.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api28.yml
.. |AdbeUnitTests-Api29| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api29.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api29.yml
.. |AdbeUnitTests-Api31| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api31.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api31.yml
.. |AdbeUnitTests-Api30| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api30.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api30.yml
.. |AdbeUnitTests-Api32| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api32.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api32.yml
.. |AdbeUnitTests-Api33| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api33.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api33.yml
.. |AdbeUnitTests-Api34| image:: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api34.yml/badge.svg
   :target: https://github.com/ashishb/adb-enhanced/actions/workflows/adbe-unittests-api34.yml
.. |asciicast| image:: https://asciinema.org/a/0IhbOF6QNIhBlgtO6VgzNmTbK.png
   :target: https://asciinema.org/a/0IhbOF6QNIhBlgtO6VgzNmTbK
.. |Homebrew package| image:: https://repology.org/badge/version-for-repo/homebrew/adb-enhanced.svg
   :target: https://formulae.brew.sh/formula/adb-enhanced
.. |Packaging status| image:: https://repology.org/badge/vertical-allrepos/python:adb-enhanced.svg
   :target: https://repology.org/project/python:adb-enhanced/versions
