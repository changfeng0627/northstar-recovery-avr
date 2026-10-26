#!/usr/bin/env python3
"""Strict Android v4/newc readers and reproducible ramdisk writer."""
# SPDX-License-Identifier: MIT
from __future__ import annotations
from dataclasses import dataclass
import gzip, hashlib, pathlib, struct
import lz4.block

def align(n, page=4): return (n + page - 1) // page * page
def digest(data): return hashlib.sha256(data).hexdigest()

def decompress(data: bytes) -> bytes:
    if data.startswith((b'070701', b'070702')): return data
    if data.startswith(b'\x1f\x8b'): return gzip.decompress(data)
    if not data.startswith(b'\x02\x21\x4c\x18'):
        raise ValueError(f'Unsupported ramdisk compression: {data[:8].hex()}')
    out=[]; pos=4
    while pos < len(data):
        if pos+4 > len(data): raise ValueError('Truncated LZ4 block header')
        size=struct.unpack_from('<I',data,pos)[0]; pos+=4
        if size == 0: break
        if size > 9*1024*1024 or pos+size > len(data): raise ValueError('Invalid LZ4 block length')
        out.append(lz4.block.decompress(data[pos:pos+size],uncompressed_size=8*1024*1024)); pos+=size
    return b''.join(out)

def compress(data: bytes) -> bytes:
    out=bytearray(b'\x02\x21\x4c\x18')
    for pos in range(0,len(data),8*1024*1024):
        block=lz4.block.compress(data[pos:pos+8*1024*1024],mode='high_compression',compression=9,store_size=False)
        out+=struct.pack('<I',len(block))+block
    return bytes(out)

@dataclass
class Entry:
    name: str
    fields: list[int]
    data: bytes
    @property
    def mode(self): return self.fields[1]

def parse_cpio(data: bytes) -> dict[str,Entry]:
    entries={}; pos=0
    while pos < len(data):
        while pos<len(data) and data[pos]==0: pos+=1
        if pos==len(data): break
        if pos+110>len(data) or data[pos:pos+6] not in (b'070701',b'070702'):
            raise ValueError(f'Invalid newc header at {pos}')
        h=[int(data[pos+6+i*8:pos+14+i*8],16) for i in range(13)]
        size,namesize=h[6],h[11]
        if namesize<1 or namesize>4096: raise ValueError('Invalid cpio name size')
        name_end=pos+110+namesize
        if name_end>len(data) or data[name_end-1]!=0: raise ValueError('Invalid cpio name')
        name=data[pos+110:name_end-1].decode('utf-8').removeprefix('./')
        start=align(name_end); end=start+size
        if end>len(data): raise ValueError('Truncated cpio entry')
        pos=align(end)
        if name=='TRAILER!!!': continue
        path=pathlib.PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts: raise ValueError(f'Unsafe path: {name}')
        entries[name]=Entry(name,h,data[start:end])
    return entries

def add(entries: dict[str,Entry],name: str,data: bytes,mode=0o100644):
    path=pathlib.PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts: raise ValueError('Unsafe entry name')
    for parent in reversed(path.parents):
        p=str(parent)
        if p=='.': continue
        if p not in entries: add(entries,p,b'',0o40755)
        elif entries[p].mode & 0o170000 != 0o40000:
            raise ValueError(f'Cannot write through non-directory {p}')
    h=[0x800000+len(entries),mode,0,0,1,0,len(data),0,0,0,0,len(name.encode())+1,0]
    entries[name]=Entry(name,h,data)

def write_cpio(entries: dict[str,Entry]) -> bytes:
    out=bytearray()
    items=list(entries.values())+[Entry('TRAILER!!!',[0,0,0,0,1,0,0,0,0,0,0,11,0],b'')]
    for item in items:
        name=item.name.encode()+b'\0'; h=item.fields.copy(); h[6]=len(item.data); h[11]=len(name);h[12]=0
        out+=b'070701'+''.join(f'{n:08x}' for n in h).encode()+name
        out+=bytes(align(len(out))-len(out));out+=item.data;out+=bytes(align(len(out))-len(out))
    out+=bytes(align(len(out),512)-len(out))
    return bytes(out)

def read_recovery(image: bytes):
    if image[:8]!=b'ANDROID!' or struct.unpack_from('<I',image,40)[0]!=4:
        raise ValueError('Expected Android boot header v4')
    kernel,ramdisk=struct.unpack_from('<II',image,8)
    if kernel!=0: raise ValueError('This avr tool only handles ramdisk-only recovery images')
    if struct.unpack_from('<I',image,1580)[0]!=0:raise ValueError('Unexpected boot v4 GKI signature')
    return parse_cpio(decompress(image[4096:4096+ramdisk]))

def write_recovery(original: bytes,entries: dict[str,Entry]) -> bytes:
    ramdisk=compress(write_cpio(entries));header=bytearray(original[:4096])
    struct.pack_into('<I',header,12,len(ramdisk));struct.pack_into('<I',header,1580,0)
    data=bytes(header)+ramdisk
    return data+bytes(align(len(data),4096)-len(data))

def read_vendor_boot(image: bytes):
    if image[:8]!=b'VNDRBOOT':raise ValueError('Expected vendor_boot')
    version,page=struct.unpack_from('<II',image,8)
    size=struct.unpack_from('<I',image,24)[0]
    header_size,dtbsize=struct.unpack_from('<II',image,2096)
    start=align(header_size,page);ramdisk=image[start:start+size]
    if version==3:return parse_cpio(decompress(ramdisk))
    if version!=4:raise ValueError('Unsupported vendor_boot version')
    table_size,count,entry_size=struct.unpack_from('<III',image,2112)
    table_offset=start+align(size,page)+align(dtbsize,page)
    if entry_size<108 or table_size<count*entry_size:raise ValueError('Invalid vendor ramdisk table')
    result={}
    for i in range(count):
        length,offset=struct.unpack_from('<II',image,table_offset+i*entry_size)
        if offset+length>len(ramdisk):raise ValueError('Invalid fragment bounds')
        if length:result.update(parse_cpio(decompress(ramdisk[offset:offset+length])))
    return result
