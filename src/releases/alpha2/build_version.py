#!/usr/bin/env python3
"""Version-only Alpha2 release from user-approved S10."""
from pathlib import Path
import hashlib, json, struct
from btf import decode, encode
ROOT=Path(__file__).resolve().parent
BASE=ROOT/'RT950_R5_RadMod_GE_REG30_SILENCE_S10_USB_LSB_BENCH_UNTESTED.BTF'
OUT=ROOT/'RT950_R5_RadMod_V1.0Alpha2.BTF'
APP=0x08003000; TEXT=0x6cae0; PTR=0x6cb4c
OLD=b'RadMod\r\nV1.0Alpha1\r\nRT950 Pro\r\n\0'
NEW=b'RadMod\r\nV1.0Alpha2\r\nRT950 Pro\r\n\0'
def sha(x): return hashlib.sha256(x).hexdigest()
raw=BASE.read_bytes()
assert len(raw)==455680 and sha(raw)=='8264d409661f2307846763a91ae5783eaac42986b4cba97a87399380aabf7659'
plain=decode(raw); assert encode(plain,raw)==raw
assert plain[TEXT:TEXT+len(OLD)]==OLD and plain.count(OLD)==1
assert plain[PTR:PTR+4]==struct.pack('<I',APP+TEXT)
assert plain[0x6cb14:0x6cb16]==bytes.fromhex('0d48')
assert ((APP+0x6cb14+4)&~3)+13*4==APP+PTR
assert len(OLD)==len(NEW)
p=bytearray(plain); p[TEXT:TEXT+len(NEW)]=NEW
result=encode(bytes(p),raw); assert len(result)==len(raw) and decode(result)==bytes(p)
changes=[i for i,(a,b) in enumerate(zip(plain,p)) if a!=b]
encoded_changes=[i for i,(a,b) in enumerate(zip(raw,result)) if a!=b]
assert changes==[TEXT+OLD.index(b'Alpha1')+5]
assert encoded_changes==[changes[0]+0x400]
assert raw[:0x800]==result[:0x800]
OUT.write_bytes(result)
manifest={'baseline':'RadMod V1.0Alpha2','parent':BASE.name,'parent_sha256':sha(raw),'output':OUT.name,'output_sha256':sha(result),'bytes':len(result),'about_text':NEW[:-1].decode(),'decoded_changed_bytes':len(changes),'encoded_changed_bytes':len(encoded_changes),'changed_decoded_offset':hex(changes[0]),'changed_flash_address':hex(APP+changes[0]),'changed_encoded_offset':hex(encoded_changes[0]),'old_byte':hex(plain[changes[0]]),'new_byte':hex(p[changes[0]]),'about_pointer_unchanged':True,'all_other_bytes_unchanged':True,'parent_user_approved':True,'version_only_image_hardware_tested':False}
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n'); print(json.dumps(manifest,indent=2))
