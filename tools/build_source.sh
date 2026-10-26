#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -euo pipefail
source_root=$(cd "$(dirname "$0")/.." && pwd)
build_root=${NORTHSTAR_BUILD_ROOT:-"$source_root/out/android"}
mkdir -p "$build_root" "$source_root/out"
exec > >(tee "$source_root/out/build.log") 2>&1
lock_value() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["source"][sys.argv[2]])' "$source_root/inputs.lock.json" "$1"; }
manifest_commit=$(lock_value manifest)
cd "$build_root"
repo init -u https://github.com/AERA-Recovery/android_manifest.git -b "$manifest_commit" --depth=1
# The official manifest already includes remove-minimal.xml. Do not add a second
# copy or retry thousands of times while deleting unknown manifest entries.
repo sync -c --no-clone-bundle --no-tags --fail-fast -j4
for project in bootable/recovery build/make; do
  if [[ $project == bootable/recovery ]]; then wanted=$(lock_value recovery); else wanted=$(lock_value build_make); fi
  git -C "$project" fetch --depth=1 origin "$wanted"
  git -C "$project" checkout --detach "$wanted"
done
repo manifest -r -o "$source_root/out/source-manifest.xml"
mkdir -p device/lenovo/avr
cp -a "$source_root/device/lenovo/avr/." device/lenovo/avr/
cp -a "$source_root/inputs/upstream-prebuilt/prebuilt" "$source_root/inputs/upstream-prebuilt/dtb" device/lenovo/avr/
mkdir -p device/lenovo/avr/recovery/root/vendor/firmware_mnt
cp -a "$source_root/inputs/upstream-prebuilt/recovery/root/vendor/firmware_mnt/." device/lenovo/avr/recovery/root/vendor/firmware_mnt/
python3 "$source_root/tools/stage_bundle.py" --bundle "$source_root/inputs/device-bundle" --tree device/lenovo/avr
git -C bootable/recovery apply --check "$source_root/patches/0001-module-loader.patch"
git -C bootable/recovery apply "$source_root/patches/0001-module-loader.patch"
python3 "$source_root/tools/branding.py" --source bootable/recovery --output "$source_root/out/branding"
python3 "$source_root/tools/validate.py" --tree device/lenovo/avr
source build/envsetup.sh
lunch twrp_avr-bp2a-eng
export GOMAXPROCS=2 GOMEMLIMIT=12GiB GOGC=50
export ANDROID_JAVA_OPTS='-Xmx4g -Xms1g'
mka adbd recoveryimage -j2
python3 "$source_root/tools/validate.py" --tree device/lenovo/avr --image out/target/product/avr/recovery.img > "$source_root/out/source-image-validation.json"
sha256sum out/target/product/avr/recovery.img > "$source_root/out/SHA256SUMS.txt"
