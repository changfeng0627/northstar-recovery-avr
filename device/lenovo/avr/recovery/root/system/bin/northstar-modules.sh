#!/system/bin/sh
# SPDX-License-Identifier: MIT
# Load in dependency order, without force-loading mismatched modules.
exec >>/tmp/northstar-modules.log 2>&1
base=/vendor/lib/modules/1.1
failed=0
while IFS= read -r module; do
    [ -n "$module" ] || continue
    name=${module%.ko}
    name=$(echo "$name" | tr '-' '_')
    if grep -q "^${name} " /proc/modules; then continue; fi
    if ! insmod "$base/$module"; then
        echo "Failed: $module"
        failed=1
    fi
done < "$base/modules.load.early"
if [ "$failed" -ne 0 ]; then
    setprop sys.northstar.modules.error 1
    echo "Some modules failed; inspect this log before claiming full hardware support."
fi
# An optional battery/USB module failure must not prevent a working touchscreen.
if [ -d /sys/module/goodix_brl_thp ] && [ -d /sys/module/touchscreen_mmi ]; then
    setprop sys.northstar.modules.ready 1
else
    setprop sys.northstar.touch.error modules
fi
