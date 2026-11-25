#!/usr/bin/env python3
"""Port the working V330 C UI to the supplied R5 image, without changing R5 DSP.
Requires clang/ld.lld/llvm-objcopy and the original user-provided BTF in baseline.
"""
from __future__ import annotations
from pathlib import Path
import subprocess,struct,hashlib,json,sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'src'))
from v304_image import APP,key,crypt,decoded
BAS=HERE/'baseline';BUILD=HERE/'build';BUILD.mkdir(exist_ok=True)
SOURCE=BAS/'R5_original.BTF'; REF=BAS/'V330C_UI_working_reference.BTF'
OUTPUT=BUILD/'RT950_V029_REG70_FAST_PRIMER_R5_V330C_UI_PORT_UNTESTED.BTF'
ORIGINAL_SHA='4988be0aabe7c16b86113a7dd34b2cb3aeb76f5e54f25a0b11ee14e9502c4b29'
REFERENCE_SHA='568f5bf45f381355854d4126504d57be87a68b1938712300809a577149fa8d00'
BADGE=0x0806fa00;ABOUT=0x0806fb00;TILE=0x0806f600
BADGE_HOOK=0x0800f932;ABOUT_HOOK=0x08019e7e
TILES=[(0x08064000,6),(0x08064084,6),(0x08064108,7),(0x080641a4,6),(0x08064228,6),(0x080642ac,7)]
def sha(b):return hashlib.sha256(b).hexdigest()
def compile_file(src,linker,out,sect):
 commands=[['clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-c',str(HERE/'src'/src),'-o',str(BUILD/f'{out}.o')],
           ['ld.lld','-T',str(HERE/'src'/linker),str(BUILD/f'{out}.o'),'-o',str(BUILD/f'{out}.elf')],
           ['llvm-objcopy','-O','binary',f'--only-section={sect}',str(BUILD/f'{out}.elf'),str(BUILD/f'{out}.bin')]]
 for c in commands:
  p=subprocess.run(c,capture_output=True,text=True)
  if p.returncode:raise RuntimeError(f'command failed: {c}\n{p.stdout}\n{p.stderr}')
 return (BUILD/f'{out}.bin').read_bytes()
def bl(src,dst):
 d=dst-src-4;assert d%2==0 and -(1<<24)<=d<(1<<24)
 x=d&((1<<25)-1);s=(x>>24)&1;i1=(x>>23)&1;i2=(x>>22)&1
 j1=(~(i1^s))&1;j2=(~(i2^s))&1
 return struct.pack('<HH',0xf000|(s<<10)|((x>>12)&1023),0xd000|(j1<<13)|(j2<<11)|((x>>1)&2047))
def decode_bl(site,op):
 a,b=struct.unpack('<HH',op);assert (a&0xf800)==0xf000 and (b&0xd000)==0xd000
 s=(a>>10)&1;j1=(b>>13)&1;j2=(b>>11)&1;i1=(~(j1^s))&1;i2=(~(j2^s))&1
 x=(s<<24)|(i1<<23)|(i2<<22)|((a&1023)<<12)|((b&2047)<<1)
 if s:x-=1<<25
 return site+4+x

def main():
 raw=SOURCE.read_bytes();refraw=REF.read_bytes()
 assert sha(raw)==ORIGINAL_SHA and sha(refraw)==REFERENCE_SHA, 'input SHA mismatch'
 assert len(raw)==len(refraw)==455680
 assert raw[:0x800]==refraw[:0x800], 'unexpected encryption header difference'
 k=key(raw);base=decoded(raw,k);ref=decoded(refraw,key(refraw));out=bytearray(base)
 assert len(base)==454656
 changes=[]
 def edit(addr,before,after,label):
  assert len(before)==len(after),label
  off=addr-APP;assert 0<=off<len(out)-len(after)
  original=base[off:off+len(after)]
  assert original==before,(label,hex(addr),original.hex(),before.hex())
  out[off:off+len(after)]=after
  changes.append(dict(addr=f'0x{addr:08x}',size=len(after),name=label))
 # Mode selector, copied exactly from the physical V330 C UI baseline.
 for address,size,name in [
  (0x080193f0,1,'3-option FM/AM/USB menu count'),
  (0x08042d20,4,'mode-list fourth entry aliases FM table A'),
  (0x08042d30,4,'mode-list fourth entry aliases FM table B'),
  (0x08042d3a,6,'rename PHASE to USB'),
  (0x08042d40,5,'erase SDSB label'),
  (0x08046a50,4,'legacy SDSB TX wrapper disabled'),
  (0x08046a60,4,'legacy SDSB RX wrapper disabled'),
  (0x0805eca2,14,'Modulation menu title'),
  (0x0805f9dc,16,'MODULATION uppercase title')]:
  edit(address,base[address-APP:address-APP+size],ref[address-APP:address-APP+size],name)
 # Copy only the validated six RGB565 USB badge tiles. No other V330 ROM data.
 for oldaddr,width in TILES:
  newaddr=oldaddr+(TILE-0x08064000);n=width*11*2
  edit(newaddr,b'\xff'*n,ref[oldaddr-APP:oldaddr-APP+n],f'USB bitmap tile from 0x{oldaddr:08x}')
 # Recompile the exact same UI renderer and About fallback with relocated literal addresses.
 badge=compile_file('ui_badge_relocated.S','ui_badge_relocated.ld','badge','.main')
 about=compile_file('about_safe.S','about_safe.ld','about','.about_recovery')
 assert len(badge)<=192 and len(about)<=128,(len(badge),len(about))
 old_badge=ref[0x08064400-APP:0x08064400-APP+len(badge)]
 old_about=ref[0x08064900-APP:0x08064900-APP+len(about)]
 assert len(old_badge)==len(badge) and len(old_about)==len(about)
 # Verify the structure of helpers against the working image, allowing only relocation literals.
 # The three BL instructions also change because their PC-relative distance to
 # the OEM bitmap renderer changes. Self pointers in the helper move as well.
 badge_expected=bytearray(old_badge)
 for offs in (0x2e,0x44,0x5a):
  assert decode_bl(0x08064400+offs,old_badge[offs:offs+4])==0x0802a714
  badge_expected[offs:offs+4]=bl(BADGE+offs,0x0802a714)
 for offs in range(0x70,0x90,4):
  val=struct.unpack_from('<I',old_badge,offs)[0]
  assert 0x08064000<=val<0x08064500
  struct.pack_into('<I',badge_expected,offs,val+(TILE-0x08064000))
 badge_expected=bytes(badge_expected)
 assert badge==badge_expected, 'relocated badge machine code differs beyond six pointers from physical V330 C reference'
 about_expected=old_about.replace(struct.pack('<I',0x08064924),struct.pack('<I',0x0806fb24))
 assert about==about_expected, 'relocated About code differs beyond label address'
 edit(BADGE,b'\xff'*len(badge),badge,'relocated main-screen USB renderer')
 edit(ABOUT,b'\xff'*len(about),about,'relocated V330 C known-working About renderer')
 edit(BADGE_HOOK,base[BADGE_HOOK-APP:BADGE_HOOK-APP+4],bl(BADGE_HOOK,BADGE),'main screen USB-renderer call')
 edit(ABOUT_HOOK,base[ABOUT_HOOK-APP:ABOUT_HOOK-APP+4],bl(ABOUT_HOOK,ABOUT),'safe About renderer call')
 # Assert exact semantics / target destinations and absence of previous V330 code overwrites.
 assert base[BADGE_HOOK-APP:BADGE_HOOK-APP+4]==bytes.fromhex('96 f8 48 31')
 assert base[ABOUT_HOOK-APP:ABOUT_HOOK-APP+4]==bytes.fromhex('00 f0 69 f8')
 assert decode_bl(BADGE_HOOK,out[BADGE_HOOK-APP:BADGE_HOOK-APP+4])==BADGE
 assert decode_bl(ABOUT_HOOK,out[ABOUT_HOOK-APP:ABOUT_HOOK-APP+4])==ABOUT
 assert out[0x080193f0-APP]==3
 assert out[0x08042d3a-APP:0x08042d40-APP]==b'USB  \0'
 assert out[0x0805eca2-APP:0x0805ecb0-APP]==b'Modulation\x00\x00\x00\x00'
 assert out[0x08019e82-APP:0x08019f54-APP]==base[0x08019e82-APP:0x08019f54-APP],'About button loop changed'
 assert out[0x0801f200-APP:0x0801f300-APP]==base[0x0801f200-APP:0x0801f300-APP],'RF receiver path changed'
 assert out[0x08052f7c-APP:0x08052f98-APP]==base[0x08052f7c-APP:0x08052f98-APP],'R5 UART banner changed'
 # Patch is strict allowlist. Everything else including R5 overlays and fast primer must match.
 allowed=set()
 for e in changes:
  addr=int(e['addr'],16);allowed.update(range(addr-APP,addr-APP+e['size']))
 diff={i for i,(a,b) in enumerate(zip(base,out)) if a!=b}
 assert diff and diff.issubset(allowed),f'Unexpected modifications: {len(diff-allowed)}'
 for start,end in [(0x08060000,0x08060f20),(0x08062000,0x08063990),(0x08063a00,0x0806f588),(0x08071800,0x08072000)]:
  assert bytes(out[start-APP:end-APP])==base[start-APP:end-APP],f'R5 code overwritten {hex(start)}'
 # encode and re-decode using R5's exact BTF format/key
 encoded=crypt(bytes(out[:0x400]+raw[0x400:0x800]+out[0x400:]),k)
 assert decoded(encoded,k)==bytes(out)
 assert encoded[:0x800]==raw[:0x800] and len(encoded)==len(raw)
 OUTPUT.write_bytes(encoded)
 manifest={
  'description':'FAST_PRIMER_R5 plus exact V330 C proven UI (relocated overlays)',
  'base_file':SOURCE.name,'base_sha256':sha(raw),'reference_file':REF.name,'reference_sha256':sha(refraw),
  'output_file':OUTPUT.name,'output_sha256':sha(encoded),'output_size':len(encoded),
  'flash_empty_space':{'tiles':'0x0806f600','USB_badge':'0x0806fa00','About':'0x0806fb00'},
  'byte_diff_count':len(diff),'changes':changes,
  'verified':['BTF crypto roundtrip','SHA-locked inputs','strict changed-byte allowlist','UI helper machine code equivalence except relocation','About UI code equivalence except relocation','branch target checks','R5 overlay preservation','R5 UART banner preservation','R5 RF, receive & fast-primer code untouched'],
  'not_ported':'V328 experimental BK4829 zero-IF USB RX feature — intentionally excluded; this is UI-only',
  'test_status':'HOST STATIC VALIDATED ONLY — not flashed or tested on actual radio'}
 (BUILD/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
