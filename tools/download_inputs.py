#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import argparse,hashlib,json,pathlib,tarfile,urllib.request

def download(output):
    output=pathlib.Path(output);output.mkdir(parents=True,exist_ok=True)
    lock=json.loads((pathlib.Path(__file__).resolve().parents[1]/'inputs.lock.json').read_text(encoding='utf-8'))
    for item in lock['downloads']:
        dest=output/item['file']
        if not dest.exists():
            with urllib.request.urlopen(item['url'],timeout=90) as response,dest.open('wb') as stream:
                while block:=response.read(1024*1024):stream.write(block)
        if hashlib.sha256(dest.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Download checksum mismatch: '+str(dest))
        target=output/item['extract_to'];target.mkdir(exist_ok=True)
        with tarfile.open(dest) as archive:
            archive.extractall(target,filter='data')
    return output
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();download(a.output)
