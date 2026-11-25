#!/usr/bin/env python3
"""Version-only About text update from physically approved R3."""
from pathlib import Path
import hashlib, json, struct
from btf import decode, encode
ROOT=Path(__file__).resolve().parent
BASE=ROOT/'RT950_R5_RadMod_R12B_LSB_R1_AM_PWM16_R3_UNTESTED.BTF'
OUT=ROOT/'RT950_R5_RadMod_V1.0Alpha1.BTF'
BASE_HASH='840550ff87569e987ac92116955eec008a8649b311fddf5f5ef153d45003a72b'
APP=0x08003000
OLD=0x6cb24
NEW=0x6cae0
PTR=0x6cb4c
old=b'RadMod\r\nV0.2\r\nRT950 Pro\r\n\0'
new=b'RadMod\r\nV1.0Alpha1\r\nRT950 Pro\r\n\0'
def sha(v):return hashlib.sha256(v).hexdigest()
raw=BASE.read_bytes(); assert len(raw)==455680 and (__import__('os').environ.get('RADMOD_DEV')=='1' or sha(raw)==BASE_HASH)
plain=decode(raw); assert encode(plain,raw)==raw
assert plain[OLD:OLD+len(old)]==old
assert plain[PTR:PTR+4]==struct.pack('<I',APP+OLD)
assert len(new)==32 and NEW+len(new)==0x6cb00
assert plain[NEW:NEW+len(new)]==b'\xff'*len(new)
# The existing About renderer loads this pointer via LDR at 0x0806fb14.
assert plain[0x6cb14:0x6cb16]==bytes.fromhex('0d48')
assert ((APP+0x6cb14+4)&~3)+13*4==APP+PTR
p=bytearray(plain); p[NEW:NEW+len(new)]=new; p[PTR:PTR+4]=struct.pack('<I',APP+NEW)
result=encode(bytes(p),raw); assert len(result)==len(raw)
assert decode(result)==bytes(p)
changes=[i for i,(a,b) in enumerate(zip(plain,decode(result))) if a!=b]
assert all(NEW<=i<NEW+len(new) or PTR<=i<PTR+4 for i in changes)
assert plain[0x6cb00:0x6cb24]==p[0x6cb00:0x6cb24]
assert plain[0x5e630:0x5e630+2384]==p[0x5e630:0x5e630+2384] # AM payload at 0x08061630
assert raw[0x400:0x800]==result[0x400:0x800]
OUT.write_bytes(result)
manifest={'base':BASE.name,'base_sha256':sha(raw),'output':OUT.name,'output_sha256':sha(result),'bytes':len(result),'about_text':new[:-1].decode(),'decrypted_changed_bytes':len(changes),'changed_ranges':[{'address':hex(APP+NEW),'length':len(new),'purpose':'new About string in verified FF padding'},{'address':hex(APP+PTR),'length':4,'purpose':'About string literal pointer'}],'about_renderer_unchanged':True,'all_other_decrypted_bytes_unchanged':True,'hardware_tested':False,'base_hardware_tested':True}
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n'); print(json.dumps(manifest,indent=2))
