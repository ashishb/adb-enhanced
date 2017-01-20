"""
List of things which this enhanced adb tool does

1. adbe rotate [left|right]
2. adbe gfx [on|off]
3. adbe overdraw [on|off]
4. adbe layout [on|off]
4. adbe airplane [on|off]
5. adbe activity keep-in-background [on|off]
6. adbe b[ack]g[round-]c[ellular-]d[ata] [on|off] $app_name
7. adbe battery saver [on|off]
8. adbe cellular-data saver [on|off]
9. adbe battery level [0-100]
10. adbe dump top-activity
11. adbe force-stop $app_name
12. adbe clear-data $app_name
13. adbe app-standby $app_name
14. adbe doze $app_name
15. adbe wifi [on|off]
16. adbe dump jank $app_name



adbe set_app_name [-f] $app_name
adbe reset_app_name

Use -q[uite] for quite mode

Source:
https://github.com/dhelleberg/android-scripts/blob/master/src/devtools.groovy

"""
