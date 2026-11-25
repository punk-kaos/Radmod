from pathlib import Path
import hashlib, json, subprocess
from btf import APP, decode, encode
D=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
base=D/'RT950_R5_RadMod_R3D_BK_INTERPOLATED_USB_TRIM_UNTESTED.BTF'
raw=base.read_bytes()
assert __import__('os').environ.get('RADMOD_DEV')=='1' or sha(raw)=='196a37b89a95eebef2d1fe2188a3b052219c5a5842eff4f7486705434708f403'
rom=decode(raw); out=bytearray(rom)
subprocess.run(['clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-c','thresholds.S','-o','thresholds.o'],cwd=D,check=True)
subprocess.run(['llvm-objcopy','-O','binary','--only-section=.text','thresholds.o','thresholds.bin'],cwd=D,check=True)
new=(D/'thresholds.bin').read_bytes(); assert len(new)==16
patches=[(0x08071336,'b9f57a6f',4000,64),(0x080713a2,'b9f57a5f',16000,256),(0x080714e6,'b0f57a5f',16000,256),(0x080714ee,'b0f57a6f',4000,64)]
# Independently decode CMP (immediate) Thumb-2 modified immediates.
def cmp_imm(b):
    a,c=int.from_bytes(b[:2],'little'),int.from_bytes(b[2:],'little')
    assert a&0xfbf0==0xf1b0 and c&0x8f00==0x0f00
    imm=((a>>10)&1)<<11|((c>>12)&7)<<8|(c&255)
    x=imm&255
    if imm>>10==0:
        v=(x,x|(x<<16),(x<<8)|(x<<24),x*0x01010101)[(imm>>8)&3]
    else:
        x=128|(imm&127); n=imm>>7; v=((x>>n)|(x<<(32-n)))&0xffffffff
    return a&15,v
records=[];mask=bytearray(len(rom))
for i,(addr,expected,old_n,new_n) in enumerate(patches):
    p=addr-APP; old=rom[p:p+4]; patch=new[4*i:4*i+4]
    assert old.hex()==expected,(hex(addr),old.hex())
    assert cmp_imm(old)==(9 if i<2 else 0,old_n)
    assert cmp_imm(patch)==(9 if i<2 else 0,new_n)
    out[p:p+4]=patch;mask[p:p+4]=b'\1'*4
    records.append(dict(address=hex(addr),old=old.hex(),new=patch.hex(),old_ticks=old_n,new_ticks=new_n))
assert all(a==b or m for a,b,m in zip(rom,out,mask))
enc=encode(out,raw); assert len(enc)==len(raw)==455680 and decode(enc)==out
# Verify all encoded bytes outside exact patch sites are unchanged, including header.
allowed=set()
for addr,_,_,_ in patches:
    p=addr-APP; assert p>=0x400
    allowed.update(range(p+0x400,p+0x404))
assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(raw,enc)))
# Stage semantics and identical live-path selection after original threshold.
def stage(t,a,b):return 0 if t<a else 1 if t<b else 2
assert [stage(t,64,256) for t in (0,63,64,255,256,16000,0xffffffff)]==[0,0,1,1,2,2,2]
assert all(stage(t,64,256)==stage(t,4000,16000) for t in range(16000,100000))
name='RT950_R5_RadMod_R3D_FASTSTART_R1_UNTESTED.BTF'; (D/name).write_bytes(enc)
manifest=dict(base=base.name,base_sha256=sha(raw),file=name,sha256=sha(enc),producer_rate_assumed_hz=8000,patches=records,decoded_bytes_changed=sum(a!=b for a,b in zip(rom,out)),encoded_bytes_changed=sum(a!=b for a,b in zip(raw,enc)),hardware_tested=False)
(D/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(D/'disassembly.txt').write_text(subprocess.check_output(['llvm-objdump','-d','--triple=thumbv7em-none-eabi','--mcpu=cortex-m4','thresholds.o'],cwd=D,text=True))
print(json.dumps(manifest,indent=2))
