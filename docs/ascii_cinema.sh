#!/usr/bin/env bash
set -euo pipefail

# This file is used for recording ascii cinema demo
# Install: brew install asciicinema
# Usage: asciinema rec --stdin -c "./ascii_cinema.sh" -t "github.com/ashishb/adb-enhanced" recording.cast

set -v

adb devices
adbe devices

adbe rotate landscape
adbe rotate portrait
adbe rotate left
adbe rotate right
adbe gfx on
adbe gfx off
adbe gfx lines
adbe overdraw on
adbe overdraw off
adbe layout on
adbe layout off
adbe battery saver on
adbe battery reset
adbe doze on
adbe doze off
adbe jank net.ashishb.androidmusicplayer
adbe top-activity
adbe dump-ui tmp1.xml
adbe mobile-data on
adbe mobile-data off
adbe mobile-data saver on
adbe mobile-data saver off
adbe show-taps on
adbe show-taps off
adbe stay-awake-while-charging on
adbe stay-awake-while-charging off
adbe screenshot tmp1.png
adbe apps list system
# Will be fixed in 2.5.11
# adbe apps list debug
# adbe apps list backup-enabled
adbe ls /data/data/net.ashishb.androidmusicplayer/databases
adbe app info net.ashishb.androidmusicplayer
adbe app path net.ashishb.androidmusicplayer
# adbe app signature net.ashishb.androidmusicplayer
adbe pull /data/data/net.ashishb.androidmusicplayer/databases/app-database.db
adbe pull -a /data/data/net.ashishb.androidmusicplayer/databases/app-database.db
adbe start net.ashishb.androidmusicplayer
adbe force-stop net.ashishb.androidmusicplayer
adbe restart net.ashishb.androidmusicplayer
# adbe app backup net.ashishb.androidmusicplayer tmp1.tar
adbe enable wireless debugging
adbe disable wireless debugging
