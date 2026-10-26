#!/usr/bin/env python3
"""Repack the analyzed avr image; preserves kernel/partition layout and verifies input hashes."""
# SPDX-License-Identifier: MIT
import argparse,io,json,os,pathlib,re,struct,subprocess,sys,tempfile
from elftools.elf.elffile import ELFFile
from recovery_image import read_recovery,write_recovery,add,digest

BASE_SHA256='ef0b39a213e8509415127f997dc95b6fe4d5379e998d02c3d429323585b45135'
def needed(data):
    elf=ELFFile(io.BytesIO(data));sec=elf.get_section_by_name('.dynamic')
    return [x.needed for x in sec.iter_tags('DT_NEEDED')] if sec else []

def build(base,bundle,tree,branding,output,avbtool,key):
    original=pathlib.Path(base).read_bytes()
    if digest(original)!=BASE_SHA256:raise ValueError('Base recovery hash differs from the audited image')
    entries=read_recovery(original);baseline_count=len(entries)
    bundle=pathlib.Path(bundle);manifest=json.loads((bundle/'bundle.json').read_text(encoding='utf-8'))
    for item in manifest['entries']:
        data=(bundle/item['path']).read_bytes()
        if digest(data)!=item['sha256']:raise ValueError('Bundle changed: '+item['path'])
        add(entries,item['path'],data,item['mode'])
    root=pathlib.Path(tree)/'recovery/root'
    for path in root.rglob('*'):
        if not path.is_file():continue
        relative=path.relative_to(root).as_posix()
        if relative.startswith('vendor/'):continue  # Already read from the verified bundle.
        if relative.endswith(('.rc','.sh','.conf','.txt')):add(entries,relative,path.read_bytes().replace(b'\r\n',b'\n'),0o100755 if relative.endswith('.sh') else 0o100644)
    # This repack preserves the original compiled module list. Our early init
    # service loads the current-firmware dependency closure independently.
    props=entries['prop.default'].data.decode()
    props=props.replace('99.87.36','16.0.0').replace('2099-12-31','2026-09-05')
    props=props.replace('W3WWL36.65-11-18/12710e-0d97a','W3WWL36.65-48-7/660f5-d1e8f0')
    props='\n'.join(line for line in props.splitlines() if not line.startswith(('ro.boot.slot_suffix=','ro.boot.vbmeta.device_state=')))+'\n'
    props+='ro.build.northstar.version=0.1.0-beta.1\nro.build.northstar.status=experimental-unverified-touch\n'
    add(entries,'prop.default',props.encode())
    credits=('Northstar Recovery for avr\nDownstream: changfeng0627\nDevice tree derived from qingxin94/avr-recovery\nEngine: AERA Recovery; includes TeamWin and Android Recovery ancestry.\nOriginal copyright and license notices remain in source.\nExperimental: touch, FBE, Wi-Fi and battery require device validation.\n')
    add(entries,'system/etc/northstar/credits.txt',credits.encode())
    branding=pathlib.Path(branding);patches=[];binary=entries['system/bin/recovery'].data
    for old_file in sorted(branding.glob('*.old.bin')):
        old=old_file.read_bytes();new=old_file.with_name(old_file.name.replace('.old.bin','.new.bin')).read_bytes()
        if len(old)!=len(new):raise ValueError('Branding changed asset length')
        count=binary.count(old)
        if count not in (0,1,2):raise ValueError('Unexpected branding asset match count')
        if count:binary=binary.replace(old,new)
        patches.append({'asset':old_file.stem,'matches':count,'patched':bool(count)})
    # Fixed-length, NUL-terminated UI labels only; never replace API names or paths.
    # The source build uses the full Northstar name. STAR is the repack's short title.
    for old,new in [(b'About AERA\0',b'About STAR\0'),(b'AERA Recovery\0',b'STAR Recovery\0')]:
        if len(old)!=len(new):raise ValueError('UI label length changed')
        count=binary.count(old);binary=binary.replace(old,new)
        patches.append({'label':old[:-1].decode(),'replacement':new[:-1].decode(),'matches':count})
    add(entries,'system/bin/recovery',binary,0o100755)
    dependencies=[]
    for item in manifest['goodix']:
        name=item['path']
        if not name.startswith(('vendor/bin/','vendor/lib64/')):continue
        for lib in needed(entries[name].data):
            candidates=['vendor/lib64/'+lib,'system/lib64/'+lib]
            found=next((x for x in candidates if x in entries),None)
            if found is None:raise ValueError(f'Unresolved library: {name}: {lib}')
            dependencies.append({'requester':name,'library':lib,'resolved':found})
    # Keep AERA's diagnostic manifests accurate after adding/replacing files.
    names=sorted(set(entries)|{'ramdisk-files.txt','ramdisk-files.sha256sum'})
    add(entries,'ramdisk-files.txt',('\n'.join(names)+'\n').encode())
    checksum_lines=[digest(e.data)+'  '+name for name,e in sorted(entries.items()) if e.mode & 0o170000==0o100000 and name not in ('prop.default','ramdisk-files.sha256sum')]
    add(entries,'ramdisk-files.sha256sum',('\n'.join(checksum_lines)+'\n').encode())
    data=bytearray(write_recovery(original,entries))
    osv=(16<<25)|((2026-2000)<<4)|9
    struct.pack_into('<I',data,16,osv)
    output=pathlib.Path(output);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(data)
    command=[sys.executable,str(avbtool),'add_hash_footer','--image',str(output),'--partition_name','recovery','--partition_size','134217728','--algorithm','SHA256_RSA4096','--key',str(key),'--rollback_index','0','--prop','com.android.build.recovery.os_version:16.0.0','--prop','com.android.build.recovery.security_patch:2026-09-05']
    # Explicit reproducible salt also avoids avbtool's Unix-only /dev/urandom path.
    command+=['--salt',digest(b'northstar-avr-v1\0'+bytes(data))]
    subprocess.run(command,check=True)
    # avbtool resolves hash descriptors by partition name (recovery.img),
    # irrespective of the supplied image's basename. A temporary hard link
    # provides that name without retaining another 128 MiB copy.
    with tempfile.TemporaryDirectory(prefix='avb-verify-',dir=output.parent) as temp:
        verify_path=pathlib.Path(temp)/'recovery.img'
        os.link(output,verify_path)
        subprocess.run([sys.executable,str(avbtool),'verify_image','--image',str(verify_path),'--key',str(key)],check=True)
    final=output.read_bytes();readback=read_recovery(final)
    if len(final)!=134217728:raise ValueError('Recovery partition size mismatch')
    for item in manifest['entries']:
        if digest(readback[item['path']].data)!=item['sha256']:raise ValueError('Packed file checksum mismatch')
    required=['init.recovery.northstar.rc','system/bin/northstar-touch.sh','system/bin/northstar-modules.sh','vendor/bin/odm_tsc','system/etc/wifi/northstar-supplicant.conf']
    for name in required:
        if name not in readback:raise ValueError('Missing required file '+name)
    report={'base_sha256':BASE_SHA256,'candidate_sha256':digest(final),'image_size':len(final),'entry_count':len(entries),'original_entry_count':baseline_count,'device_module_count':len(manifest['modules']),'kernel_baseline':manifest['kernel'],'avb_verification':'passed','packed_bundle_checksums':'passed','library_dependencies':dependencies,'branding':patches,'device_testing':'NOT TESTED: phone remains on restored stock recovery'}
    output.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['base','bundle','tree','branding','output','avbtool','key']:p.add_argument('--'+key,required=True)
    args=p.parse_args();report=build(**vars(args));print('Candidate:',report['candidate_sha256'])
