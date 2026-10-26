#
# Copyright (C) 2026 AERA Recovery
# device.mk for Lenovo Legion Y70 (avr)
#

# USB config
PRODUCT_PROPERTY_OVERRIDES += \
    ro.recovery.usb.vid=22B8 \
    ro.recovery.usb.adb.pid=2E81 \
    ro.recovery.usb.fastboot.pid=2E80 \

# Device identity
PRODUCT_PROPERTY_OVERRIDES += \
    ro.product.device=avr \
    ro.product.name=avr_cn \
    ro.product.model=XT2611-1 \
    ro.product.brand=Lenovo \
    ro.product.manufacturer=Motorola Mobility \
    ro.build.product=avr \

# Device-specific binaries are staged under recovery/root by tools/stage_bundle.py.
# build/make copies that directory directly into the ramdisk. Do not use
# $(TARGET_RECOVERY_ROOT_OUT) as a PRODUCT_COPY_FILES destination: that variable
# is an output path, while PRODUCT_COPY_FILES destinations are PRODUCT_OUT-relative.

# 跳过prebuilt page size检查（magiskboot 4096 vs 16384）
PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE := false
