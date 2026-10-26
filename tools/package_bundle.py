#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import argparse,gzip,io,json,pathlib,tarfile
from recovery_image import digest

def package(bundle,output):
    bundle=pathlib.Path(bundle);output=pathlib.Path(output)
    manifest=json.loads((bundle/'bundle.json').read_text(encoding='utf-8'))
    items=[('bundle.json',0o644)]+[(x['path'],x['mode']&0o777) for x in manifest['entries']]
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as tar:
        for name,mode in sorted(items):
            data=(bundle/name).read_bytes();info=tarfile.TarInfo(name);info.size=len(data);info.mode=mode;info.mtime=0
            tar.addfile(info,io.BytesIO(data))
    print(digest(output.read_bytes()),output)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',required=True);p.add_argument('--output',required=True);a=p.parse_args();package(a.bundle,a.output)
