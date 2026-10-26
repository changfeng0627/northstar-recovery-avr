#!/system/bin/sh
# SPDX-License-Identifier: MIT
# Goodix THP requires its userspace processing engine, not only a kernel module.
exec >>/tmp/northstar-touch.log 2>&1
mkdir -p /tmp/northstar/touch/fw /tmp/northstar/touch/logs /tmp/northstar/record
cp /vendor/etc/thp/* /tmp/northstar/touch/fw/ || exit 1
count=0
while [ ! -e /dev/thp ] || [ ! -e /dev/input_agent ]; do
    count=$((count + 1))
    if [ "$count" -ge 30 ]; then
        echo "Goodix device nodes did not appear within 30 seconds"
        setprop sys.northstar.touch.error nodes
        exit 1
    fi
    sleep 1
done
# Use the real avr sysfs path. Do not wait for the nonexistent touch_dev node.
cat /sys/devices/platform/goodix_thp.0/screen_state 2>/dev/null
setprop sys.northstar.touch.started 1
exec /system/bin/linker64 --library-path /vendor/lib64:/system/lib64 /vendor/bin/odm_tsc
