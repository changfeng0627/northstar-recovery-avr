#!/system/bin/sh
# SPDX-License-Identifier: MIT
count=0
while [ "$count" -lt 30 ]; do
    if [ -e /sys/class/net/wlan0 ]; then
        setprop wifi.driver.ready true
        exit 0
    fi
    count=$((count + 1))
    sleep 1
done
echo "wlan0 did not appear within 30 seconds" >/tmp/northstar-wlan.log
setprop sys.northstar.wlan.error timeout
exit 1
