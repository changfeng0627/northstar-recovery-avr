#!/usr/bin/env python3
"""Build a complete, device-matched module/Goodix staging tree from read-only backups."""
# SPDX-License-Identifier: MIT
import argparse, io, json, pathlib, re, tarfile
from elftools.elf.elffile import ELFFile
from recovery_image import read_vendor_boot,digest

EARLY=['goodix_brl_thp','touchscreen_mmi','qti_battery_charger','qti_glink_charger_v2','mmi_glink_charger','qpnp_adaptive_charge','qcom_q6v5_pas','adsp_loader_dlkm','dwc3-msm','usb_f_gsi']
WLAN=['qca_cld3_wcn7750','rmnet_wlan']
def norm(name):return name.removesuffix('.ko').replace('-','_')
def modinfo(data,key):
    elf=ELFFile(io.BytesIO(data));section=elf.get_section_by_name('.modinfo')
    if section is None:raise ValueError('Module has no .modinfo')
    values=[s[len(key)+1:].decode() for s in section.data().split(b'\0') if s.startswith(key.encode()+b'=')]
    return values[0] if values else ''

def prepare(archive,vendor_boot,output,kernel):
    output=pathlib.Path(output);output.mkdir(parents=True,exist_ok=True)
    files={}
    with tarfile.open(archive) as t:
        for m in t.getmembers():
            if m.isfile():
                p=pathlib.PurePosixPath(m.name)
                if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe donor archive')
                files[str(p)]=t.extractfile(m).read()
    boot=read_vendor_boot(pathlib.Path(vendor_boot).read_bytes())
    modules={}
    for name,data in [(k,e.data) for k,e in boot.items()]+list(files.items()):
        if name.endswith('.ko'):
            key=norm(pathlib.PurePosixPath(name).name)
            modules[key]=(pathlib.PurePosixPath(name).name,data,name)
    order=[];visiting=set();visited=set()
    def visit(name):
        key=norm(name)
        if key in visited:return
        if key in visiting:raise ValueError('Module dependency cycle: '+name)
        if key not in modules:raise ValueError('Missing dependency: '+name)
        visiting.add(key)
        for dep in filter(None,modinfo(modules[key][1],'depends').split(',')):visit(dep)
        visiting.remove(key);visited.add(key);order.append(key)
    for seed in EARLY:visit(seed)
    early=list(order)
    for seed in WLAN:visit(seed)
    wlan=order[len(early):]
    entries={};module_records=[]
    base='vendor/lib/modules/1.1'
    for key in order:
        name,data,source=modules[key];vm=modinfo(data,'vermagic')
        if not vm.startswith(kernel.split('-android')[0]+'-android16-6-'):
            raise ValueError(f'Module kernel family mismatch: {name}: {vm}')
        entries[base+'/'+name]=(data,0o100644)
        module_records.append({'name':name,'source':source,'sha256':digest(data),'vermagic':vm,'depends':modinfo(data,'depends')})
    for label,keys in [('early',early),('wlan',wlan)]:
        entries[base+'/modules.load.'+label]=(('\n'.join(modules[k][0] for k in keys)+'\n').encode(),0o100644)
    entries[base+'/modules.load']=(('\n'.join(modules[k][0] for k in order)+'\n').encode(),0o100644)
    dep_lines=[]
    for key in order:
        name,data,_=modules[key]
        dep_lines.append(name+': '+' '.join(modules[norm(d)][0] for d in modinfo(data,'depends').split(',') if d))
    entries[base+'/modules.dep']=(('\n'.join(dep_lines)+'\n').encode(),0o100644)
    old=b'/data/vendor/touchscreen';new=b'/tmp/northstar/touch'.ljust(len(old),b'/')
    old_rec=b'/data/vendor/touchrec';new_rec=b'/tmp/northstar/record'.ljust(len(old_rec),b'/')
    if len(new)!=len(old) or len(new_rec)!=len(old_rec):raise ValueError('Path substitution length changed')
    patched=[]
    for name,data in files.items():
        if name.startswith(('vendor/bin/','vendor/lib64/','vendor/etc/thp/')):
            original=digest(data)
            if name.startswith(('vendor/bin/','vendor/lib64/')):
                data=data.replace(old,new).replace(old_rec,new_rec)
            entries[name]=(data,0o100755 if name.startswith('vendor/bin/') else 0o100644)
            patched.append({'path':name,'original_sha256':original,'sha256':digest(data),'redirected_to_tmp':original!=digest(data)})
    # odm_tsc dlopens these libraries; DT_NEEDED alone does not enumerate them.
    for name in ('vendor/bin/odm_tsc','vendor/lib64/libgdix_tsc.so','vendor/lib64/libgdix_tsa_avr.so','vendor/lib64/libgdix_afe.so','vendor/etc/thp/thp_cfg_9916.bin'):
        if name not in entries:raise ValueError('Missing Goodix component '+name)
    for name,(data,mode) in entries.items():
        dest=output/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        if mode==0o100755:dest.chmod(0o755)
    manifest={'kernel':kernel,'donor_archive_sha256':digest(pathlib.Path(archive).read_bytes()),'vendor_boot_sha256':digest(pathlib.Path(vendor_boot).read_bytes()),'modules':module_records,'early_modules':[modules[k][0] for k in early],'wlan_modules':[modules[k][0] for k in wlan],'goodix':patched,'entries':[{'path':k,'mode':mode,'sha256':digest(data)} for k,(data,mode) in entries.items()]}
    (output/'bundle.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--donor',required=True);p.add_argument('--vendor-boot',required=True);p.add_argument('--kernel',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    m=prepare(a.donor,a.vendor_boot,a.output,a.kernel);print(f"Prepared {len(m['modules'])} modules and {len(m['goodix'])} Goodix files")
