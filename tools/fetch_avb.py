#!/usr/bin/env python3
"""Fetch pinned AOSP AVB tool and the public Android test key. No production keys."""
# SPDX-License-Identifier: MIT
import argparse,base64,hashlib,pathlib,urllib.request
FILES={'avbtool.py':'e5a664a38db623da00f080219bc0ee60a640a9dc4a872803616fae4938ac749b','test/data/testkey_rsa4096.pem':'6a224754880a57ab9cbd308267cd157d94cf05a1c8cb851aec4090e045d24121'}
def fetch(out):
    out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
    for name,expected in FILES.items():
        dest=out/pathlib.PurePosixPath(name).name
        data=dest.read_bytes() if dest.exists() else base64.b64decode(urllib.request.urlopen('https://android.googlesource.com/platform/external/avb/+/refs/tags/android-16.0.0_r1/'+name+'?format=TEXT',timeout=45).read())
        if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('AOSP tool checksum mismatch: '+name)
        dest.write_bytes(data)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();fetch(a.output)
