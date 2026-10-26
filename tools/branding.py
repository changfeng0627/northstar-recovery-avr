#!/usr/bin/env python3
"""Generate Northstar alpha masks and apply narrowly scoped UI branding changes."""
# SPDX-License-Identifier: MIT
import argparse,math,pathlib,re,json
from PIL import Image,ImageDraw,ImageFont

SPECS={'aera_lock_logo':(900,684),'aera_lock_inner_dark':(900,684),'aera_lock_inner_light':(900,684),'aera_boot_final_white':(846,791),'aera_boot_final_cyan':(846,791),'aera_boot_word':(846,168),'aera_boot_subtitle':(846,50)}

def font(size):
    # Pillow's bundled scalable font is identical on Windows/Linux with the
    # pinned Pillow version; do not depend on whichever system font is installed.
    return ImageFont.load_default(size=size)

def mask(name,width,height):
    scale=2;im=Image.new('L',(width*scale,height*scale));d=ImageDraw.Draw(im)
    def text(s,y,size):
        f=font(size*scale);box=d.textbbox((0,0),s,font=f);x=(im.width-(box[2]-box[0]))/2
        d.text((x,y*scale-box[1]),s,font=f,fill=255)
    if name.endswith('subtitle'):text('RECOVERY',7,35)
    elif name.endswith('word'):text('NORTHSTAR',35,102)
    else:
        cx=width/2;cy=height*.43 if 'final' in name else height/2;r=min(width,height)*.28
        box=((cx-r)*scale,(cy-r)*scale,(cx+r)*scale,(cy+r)*scale)
        if 'inner_dark' not in name and 'inner_light' not in name:
            d.arc(box,20,310,fill=255,width=int(r*.11*scale))
            pts=[]
            for i in range(16):
                angle=-math.pi/2+i*math.pi/8;rr=r*(.72 if i%4==0 else .42 if i%2==0 else .19)
                pts.append(((cx+math.cos(angle)*rr)*scale,(cy+math.sin(angle)*rr)*scale))
            d.polygon(pts,fill=255)
        if 'final' in name:
            text('NORTHSTAR',height*.79,86);text('RECOVERY',height*.91,34)
    return im.resize((width,height),Image.Resampling.LANCZOS)

def inc_bytes(path):
    text=path.read_text(encoding='utf-8');body=text[text.index('{')+1:text.index('}')]
    return bytes(int(x,16) for x in re.findall(r'0x([0-9a-fA-F]{2})',body))

def apply(source,out):
    source=pathlib.Path(source);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
    records=[]
    for name,(w,h) in SPECS.items():
        p=source/'aeraui/assets'/(name+'.inc')
        if not p.exists():raise ValueError('Unsupported upstream assets: '+str(p))
        old=inc_bytes(p)
        if len(old)!=w*h:raise ValueError('Upstream alpha asset dimensions changed: '+name)
        new=mask(name,w,h).tobytes();(out/(name+'.old.bin')).write_bytes(old);(out/(name+'.new.bin')).write_bytes(new)
        text=p.read_text(encoding='utf-8');left=text.index('{')+1;right=text.index('}')
        body='\n'+''.join('  '+', '.join(f'0x{x:02x}' for x in new[i:i+12])+',\n' for i in range(0,len(new),12))
        p.write_text(text[:left]+body+text[right:],encoding='utf-8',newline='\n')
        records.append({'asset':name,'bytes':len(new)})
    # Change UI labels only. Keep APIs, namespaces, storage paths and copyright notices.
    edits={'aeraui/core/engine.cpp':{'identity.title = "AERA Recovery"':'identity.title = "Northstar Recovery"'},'aeraui/scenes/about_scene.cpp':{'FixedLabel(hero, "AERA"':'FixedLabel(hero, "NORTHSTAR"','landscape ? 330 : 310':'landscape ? 160 : 150','"About AERA"':'"About Northstar"','"Independent. Open. Built for recovery."':'"Based on AERA Recovery; avr tree by qingxin94."','"THE PEOPLE BEHIND AERA"':'"UPSTREAM AERA CONTRIBUTORS"'}}
    for name,replacements in edits.items():
        p=source/name;text=p.read_text(encoding='utf-8')
        for old,new in replacements.items():
            if old not in text and new not in text:raise ValueError(f'Branding anchor changed: {name}: {old}')
            text=text.replace(old,new)
        p.write_text(text,encoding='utf-8',newline='\n')
    preview=Image.new('RGB',(720,810),'#0b1527');alpha=mask('aera_boot_final_white',720,810);preview.paste('#e9f8ff',(0,0),alpha);preview.save(out/'northstar-preview.png')
    (out/'branding.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    return records

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True);a=p.parse_args();apply(a.source,a.output)
