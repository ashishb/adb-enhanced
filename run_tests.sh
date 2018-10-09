set -x
set -e
# $1 should be python or python3 to decide python versions
# For now, we just run all the commands, later, we will add
# validation to the output
APP_ID=com.android.phone
FILE_PATH=/data/data/$APP_ID

$1 adbe.py rotate landscape
$1 adbe.py rotate portrait
$1 adbe.py rotate left
$1 adbe.py rotate right

$1 adbe.py gfx on
$1 adbe.py gfx off 
$1 adbe.py gfx lines

$1 adbe.py overdraw on
$1 adbe.py overdraw off
$1 adbe.py overdraw deut

$1 adbe.py layout on
$1 adbe.py layout off

$1 adbe.py airplane on
$1 adbe.py airplane off

# TODO: figure out how to assert failure
# $1 adbe.py battery level -1
$1 adbe.py battery level 10
# TODO: figure out how to assert failure
# $1 adbe.py battery level 101

$1 adbe.py battery saver on
$1 adbe.py battery saver off
$1 adbe.py battery reset

$1 adbe.py doze on
$1 adbe.py doze off

$1 adbe.py devices
$1 adbe.py top-activity
$1 adbe.py dump-ui tmp1.xml

$1 adbe.py mobile-data on
$1 adbe.py mobile-data off
$1 adbe.py mobile-data saver on
$1 adbe.py mobile-data saver off

$1 adbe.py rtl on
$1 adbe.py rtl off

$1 adbe.py screenshot tmp1.png -v
# How to insert ^C here?
# $1 adbe.py [options] screenrecord <filename.mp4>

$1 adbe.py dont-keep-activities on
$1 adbe.py dont-keep-activities off

$1 adbe.py animations on
$1 adbe.py animations off

$1 adbe.py stay-awake-while-charging on
# Disable this since it causes Circle CI to fail
# $1 adbe.py stay-awake-while-charging off

$1 adbe.py input-text "Hello" -v
$1 adbe.py press back
$1 adbe.py open-url https://google.com

$1 adbe.py permission-groups list all -v
$1 adbe.py permissions list all -v 
$1 adbe.py permissions list dangerous -v

# TODO: Increase Travis version >= 23, so that, we can test runtime permissions.
# # Grant permissions
# $1 adbe.py permissions grant $APP_ID calendar
# $1 adbe.py permissions grant $APP_ID camera
# $1 adbe.py permissions grant $APP_ID contacts
# $1 adbe.py permissions grant $APP_ID location
# $1 adbe.py permissions grant $APP_ID microphone
# $1 adbe.py permissions grant $APP_ID phone
# $1 adbe.py permissions grant $APP_ID sensors
# $1 adbe.py permissions grant $APP_ID sms
# $1 adbe.py permissions grant $APP_ID storage
# # Revoke permissions
# $1 adbe.py permissions revoke $APP_ID calendar
# $1 adbe.py permissions revoke $APP_ID camera
# $1 adbe.py permissions revoke $APP_ID contacts
# $1 adbe.py permissions revoke $APP_ID location
# $1 adbe.py permissions revoke $APP_ID microphone
# $1 adbe.py permissions revoke $APP_ID phone
# $1 adbe.py permissions revoke $APP_ID sensors
# $1 adbe.py permissions revoke $APP_ID sms
# $1 adbe.py permissions revoke $APP_ID storage

$1 adbe.py apps list all
$1 adbe.py apps list system
$1 adbe.py apps list third-party
$1 adbe.py apps list debug

# Only supported on API >= 28
# $1 adbe.py standby-bucket get $APP_ID
# $1 adbe.py standby-bucket set $APP_ID active
# $1 adbe.py standby-bucket set $APP_ID working_set
# $1 adbe.py standby-bucket set $APP_ID frequent
# $1 adbe.py standby-bucket set $APP_ID rare

# Only supported on API >= 28
# $1 adbe.py restrict-background true $APP_ID
# $1 adbe.py restrict-background false $APP_ID

$1 adbe.py ls -l -R $FILE_PATH
$1 adbe.py rm -f -r $FILE_PATH

TMP_FILE_PATH=/data/local/tmp/tmp1.db
adb shell touch $TMP_FILE_PATH
$1 adbe.py pull -a $TMP_FILE_PATH
$1 adbe.py pull $TMP_FILE_PATH tmp2
$1 adbe.py cat $TMP_FILE_PATH

$1 adbe.py start $APP_ID
# Jank can be seen only if the app is running.
$1 adbe.py jank $APP_ID
$1 adbe.py stop $APP_ID
$1 adbe.py restart $APP_ID
$1 adbe.py force-stop $APP_ID
$1 adbe.py clear-data $APP_ID
$1 adbe.py app-info $APP_ID
$1 adbe.py app-path $APP_ID
$1 adbe.py app-signature $APP_ID

set +e
set +x
