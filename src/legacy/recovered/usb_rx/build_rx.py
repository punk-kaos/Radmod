#!/usr/bin/env python3
"""Port exactly the V328 BK4829 USB RX overlay onto FAST_PRIMER_R5 + V330C UI.
This is a byte-limited patch: one receiver BL and one relocated flash overlay.
"""
from __future__ import annotations
from pathlib import Path
import hashlib, struct, json, subprocess, sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from v304_image import APP, key, crypt, decoded
BAS=ROOT/'baseline'
BUILD=ROOT/'build';BUILD.mkdir(exist_ok=True)
SOURCE=BAS/'R5_UI_base.BTF'
REF=BAS/'V328_RX_reference.BTF'
ORIGINAL=BAS/'R5_original.BTF'
TARGET=BUILD/'RT950_V029_R5_FAST_PRIMER_V330C_UI_V328_USB_RX_PORT_UNTESTED.BTF'
SOURCE_SHA='1b1fefd59f1ad152fece3341df4d029f4dc8483537dcf2a2475958b91dcd2570'
REF_SHA='db94e25b9cf9aae1e3d1f10b10125bc22749747f45f7261002eefee3b71e3b31'
ORIGINAL_SHA='4988be0aabe7c16b86113a7dd34b2cb3aeb76f5e54f25a0b11ee14e9502c4b29'
HOOK=0x0801F2C2
OVERLAY=0x0806FC00
REF_OVERLAY=0x08064600
BADGE=0x0806FA00
ABOUT=0x0806FB00

def sha(b): return hashlib.sha256(b).hexdigest()
def bl(src,dst):
 delta=dst-src-4
 assert delta % 2 == 0 and -(1<<24) <= delta < (1<<24)
 x=delta&((1<<25)-1);s=(x>>24)&1;i1=(x>>23)&1;i2=(x>>22)&1
 j1=(~(i1^s))&1;j2=(~(i2^s))&1
 return struct.pack('<HH',0xf000|(s<<10)|((x>>12)&1023),0xd000|(j1<<13)|(j2<<11)|((x>>1)&2047))
def unbl(site,op):
 a,b=struct.unpack('<HH',op)
 assert (a&0xf800)==0xf000 and (b&0xd000)==0xd000
 s=(a>>10)&1;j1=(b>>13)&1;j2=(b>>11)&1
 i1=(~(j1^s))&1;i2=(~(j2^s))&1
 x=(s<<24)|(i1<<23)|(i2<<22)|((a&1023)<<12)|((b&2047)<<1)
 if s:x-=1<<25
 return site+4+x

def build():
 for fn,digest in ((SOURCE,SOURCE_SHA),(REF,REF_SHA),(ORIGINAL,ORIGINAL_SHA)):
  assert sha(fn.read_bytes())==digest, f'Input digest mismatch: {fn.name}'
 raw=SOURCE.read_bytes();refraw=REF.read_bytes();oraw=ORIGINAL.read_bytes()
 assert len(raw)==len(refraw)==len(oraw)==455680
 assert raw[:0x800]==refraw[:0x800]==oraw[:0x800], 'Unexpected BTF crypt/header scheme'
 base=decoded(raw,key(raw));ref=decoded(refraw,key(refraw));out=bytearray(base)
 def reg(a,n):return base[a-APP:a-APP+n]
 assert reg(HOOK,4)==bytes.fromhex('47 20 90 47'),f'Unexpected R5 RX dispatch hook: {reg(HOOK,4).hex()}'
 # Earlier receiver image exactly replaced this same OEM call, and the original
 # reference has the expected BL to the old 0x08064600 RX overlay.
 assert unbl(HOOK,ref[HOOK-APP:HOOK-APP+4])==REF_OVERLAY
 for a,n in [(OVERLAY,256),(BADGE,144),(ABOUT,84)]:
  assert 0 <= a-APP and a-APP+n<=len(base)
 assert reg(OVERLAY,256)==b'\xff'*256, 'RX overlay area not empty'
 assert reg(BADGE,144)!=b'\xff'*144 and reg(ABOUT,84)!=b'\xff'*84
 assert reg(0x080193F0,1)==bytes([3]),'Modulation menu is not 3-choice'
 assert reg(0x08042D3A,6)==b'USB  \0'
 assert reg(0x0805ECA2,14)==b'Modulation\0\0\0\0'
 assert reg(0x08046a50,4)==bytes.fromhex('aff30080')
 assert reg(0x08046a60,4)==bytes.fromhex('aff30080')
 assert unbl(0x0800f932,reg(0x0800f932,4))==BADGE
 assert unbl(0x08019e7e,reg(0x08019e7e,4))==ABOUT
 # Build old V328 assembly at relocated address; no arithmetic changes.
 cmds=[['clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-c',str(ROOT/'src/rx_usb_overlay.S'),'-o',str(BUILD/'rx_usb_overlay.o')],
       ['ld.lld','-T',str(ROOT/'src/rx_usb_overlay.ld'),str(BUILD/'rx_usb_overlay.o'),'-o',str(BUILD/'rx_usb_overlay.elf')],
       ['llvm-objcopy','-O','binary','--only-section=.rx_usb',str(BUILD/'rx_usb_overlay.elf'),str(BUILD/'rx_usb_overlay.bin')]]
 for c in cmds:
  p=subprocess.run(c,capture_output=True,text=True)
  assert p.returncode==0, f'Build failed: {c}\n{p.stdout}\n{p.stderr}'
 rx=(BUILD/'rx_usb_overlay.bin').read_bytes()
 assert len(rx)==116, f'Expected the original 116-byte V328 hook, got {len(rx)}'
 # The assembly uses no absolute flash pointers; linked at R5's free region,
 # it must produce the very same instructions (including constants) as V328.
 old_rx=ref[REF_OVERLAY-APP:REF_OVERLAY-APP+len(rx)]
 assert rx==old_rx,'V328 receive assembly differs following relocation'
 out[HOOK-APP:HOOK-APP+4]=bl(HOOK,OVERLAY)
 out[OVERLAY-APP:OVERLAY-APP+len(rx)]=rx
 assert unbl(HOOK,out[HOOK-APP:HOOK-APP+4])==OVERLAY
 assert out[OVERLAY-APP:OVERLAY-APP+len(rx)]==old_rx
 # Entire non-RX R5 user firmware must remain byte-for-byte identical.
 allow=set(range(HOOK-APP,HOOK-APP+4))|set(range(OVERLAY-APP,OVERLAY-APP+len(rx)))
 changed={i for i,(x,y) in enumerate(zip(base,out)) if x!=y}
 assert changed and changed<=allow, f'Non-RX bytes changed: {len(changed-allow)}'
 assert not changed.intersection(range(BADGE-APP,ABOUT-APP+84))
 assert out[0x08052f7c-APP:0x08052f98-APP]==base[0x08052f7c-APP:0x08052f98-APP], 'R5 UART banner changed'
 assert out[0x0806f600-APP:0x0806fc00-APP]==base[0x0806f600-APP:0x0806fc00-APP], 'UI overlays changed'
 for x,y in [(0x08060000,0x08060f20),(0x08062000,0x08063990),(0x08063a00,0x0806f588),(0x08071800,0x08072000)]:
  assert out[x-APP:y-APP]==base[x-APP:y-APP],f'R5 base code changed {hex(x)}'
 # Encode in original BTF scheme; use original key/header unmodified.
 frame=bytes(out[:0x400])+raw[0x400:0x800]+bytes(out[0x400:])
 enc=crypt(frame,key(raw))
 assert decoded(enc,key(enc))==bytes(out), 'BTF crypto roundtrip mismatch'
 assert enc[:0x800]==raw[:0x800] and len(enc)==455680
 TARGET.write_bytes(enc)
 details={
  'name':'R5 FAST_PRIMER + V330C UI + V328 BK4829 USB RX',
  'base_sha256':sha(raw),'reference_v328_sha256':sha(refraw),
  'output_filename':TARGET.name,'output_sha256':sha(enc),'output_bytes':len(enc),
  'modified_decoded_bytes':len(changed),
  'rx_hook_address':hex(HOOK),'rx_hook_original':reg(HOOK,4).hex(),
  'rx_hook_patched':out[HOOK-APP:HOOK-APP+4].hex(),'rx_hook_target':hex(unbl(HOOK,out[HOOK-APP:HOOK-APP+4])),
  'rx_overlay_address':hex(OVERLAY),'rx_overlay_bytes':len(rx),
  'rx_reg47_usb':hex(0x6542),'rx_reg3d_zero_if':hex(0),'rx_reg73_afc_bit':hex(0x10),
  'radio_function':'experimental BASEBAND2 direct conversion; DSB-like, no independent USB LSB rejection',
  'known_good_preserved':'R5 fast primer, voice engine, UART, V330C UI, USB badge, safe About page, 3-mode list, SDSB removal',
  'verification':['SHA-locked base/reference','assembly exact byte match to V328 RX routine','R5 original receiver dispatch matched','verified 256 bytes unused destination','strict two-region allowlist','UI code intact','TX and primer overlays untouched','Thumb BL target decoded','BTF roundtrip'],
  'hardware':'NOT TESTED; receive and FM/AM restoration require radio checks'
 }
 (BUILD/'manifest.json').write_text(json.dumps(details,indent=2)+'\n')
 print(json.dumps(details,indent=2))

if __name__=='__main__':build()
