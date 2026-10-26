#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import argparse,json,pathlib,re,sys
from recovery_image import digest,read_recovery

def validate(tree,image=None):
    tree=pathlib.Path(tree);board=(tree/'BoardConfig.mk').read_text(encoding='utf-8');props=(tree/'system.prop').read_text(encoding='utf-8')
    assert 'ro.boot.slot_suffix=' not in props,'Boot slot override found'
    assert 'ro.boot.vbmeta.device_state=' not in props,'Bootloader state override found'
    assert '2099-12-31' not in board,'Fabricated security patch date'
    assert 'VENDOR_SECURITY_PATCH        := $(PLATFORM_VERSION)' not in board,'Invalid security patch format'
    assert '$(TARGET_RECOVERY_ROOT_OUT)' not in '\n'.join(x for x in (tree/'device.mk').read_text(encoding='utf-8').splitlines() if not x.strip().startswith('#')),'Incorrect PRODUCT_COPY_FILES destination'
    rc=(tree/'recovery/root/init.recovery.qcom.rc').read_text(encoding='utf-8')
    assert 'import /init.recovery.northstar.rc' in rc,'Missing Northstar init import'
    assert '/sys/class/touch/touch_dev' not in rc,'Nonexistent touch node'
    generated=(tree/'generated_modules.mk').read_text(encoding='utf-8')
    early=re.search(r'AERA_LOAD_VENDOR_MODULES := "([^"]+)"',generated).group(1).split()
    assert early.index('touchscreen_mmi.ko')<early.index('goodix_brl_thp.ko'),'Touch dependency order reversed'
    report={'static_checks':'passed','early_module_count':len(early)}
    if image:
        blob=pathlib.Path(image).read_bytes();entries=read_recovery(blob)
        assert len(blob)==134217728,'Image size does not match recovery partition'
        for name in early:assert 'vendor/lib/modules/1.1/'+name in entries,'Module not packed: '+name
        for name in ('vendor/bin/odm_tsc','vendor/lib64/libgdix_tsa_avr.so','vendor/etc/thp/thp_cfg_9916.bin','system/bin/northstar-touch.sh','system/etc/wifi/northstar-supplicant.conf'):
            assert name in entries,'Missing component '+name
        for line in entries['ramdisk-files.sha256sum'].data.decode().splitlines():
            expected,name=line.split('  ',1)
            assert digest(entries[name].data)==expected,'Stale ramdisk manifest: '+name
        assert b'/data/vendor/touchscreen' not in entries['vendor/bin/odm_tsc'].data,'Touch daemon still depends on userdata'
        assert b'sys.northstar.modules.ready' in entries['init.recovery.northstar.rc'].data
        report.update(image_checks='passed',sha256=digest(blob),entries=len(entries))
    print(json.dumps(report,indent=2));return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tree',default='device/lenovo/avr');p.add_argument('--image');a=p.parse_args();validate(a.tree,a.image)
