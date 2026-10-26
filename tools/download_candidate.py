#!/usr/bin/env python3
"""Download/reassemble the experimental image with standard Python only."""
# SPDX-License-Identifier: MIT
import argparse,hashlib,json,pathlib,re,shutil,urllib.request,zipfile
BASE='https://github.com/changfeng0627/northstar-recovery-avr/releases/download/v0.1.0-beta.1/'
def sha(path):
    with pathlib.Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def download(output,manifest_path=None,parts_dir=None):
    output=pathlib.Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    manifest=json.loads(pathlib.Path(manifest_path).read_text(encoding='utf-8')) if manifest_path else json.load(urllib.request.urlopen(BASE+'candidate-parts.json',timeout=45))
    if output.exists():
        if sha(output)==manifest['image_sha256']:print('Existing image already matches');return
        raise ValueError('Output already exists with different contents; refusing to overwrite')
    cache=pathlib.Path(parts_dir) if parts_dir else output.parent/'.northstar-download';cache.mkdir(exist_ok=True)
    for item in manifest['parts']:
        name=item['name']
        if not re.fullmatch(r'northstar-avr-candidate\.zip\.\d{3}',name):raise ValueError('Unsafe part name')
        dest=cache/name
        if dest.exists() and sha(dest)==item['sha256']:continue
        temporary=dest.with_suffix(dest.suffix+'.partial')
        print('Downloading',name,flush=True)
        with urllib.request.urlopen(BASE+name,timeout=90) as response,temporary.open('wb') as stream:shutil.copyfileobj(response,stream)
        if temporary.stat().st_size!=item['size'] or sha(temporary)!=item['sha256']:raise ValueError('Part checksum mismatch')
        temporary.replace(dest)
    archive=cache/'candidate.zip'
    with archive.open('wb') as stream:
        for item in manifest['parts']:
            with (cache/item['name']).open('rb') as source:shutil.copyfileobj(source,stream)
    if sha(archive)!=manifest['archive_sha256']:raise ValueError('Archive checksum mismatch')
    temp_image=output.with_name(output.name+'.partial')
    with zipfile.ZipFile(archive) as z,temp_image.open('wb') as stream:
        with z.open(manifest['image_name']) as source:shutil.copyfileobj(source,stream)
    if temp_image.stat().st_size!=manifest['image_size'] or sha(temp_image)!=manifest['image_sha256']:raise ValueError('Image checksum mismatch')
    temp_image.replace(output)
    archive.unlink()  # Keep verified resumable parts, not a second assembled ZIP.
    print('Verified image:',output,manifest['image_sha256'])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='northstar-avr-0.1.0-beta.1.img');p.add_argument('--manifest');p.add_argument('--parts-dir');args=p.parse_args();download(args.output,args.manifest,args.parts_dir)
