#!/usr/bin/env python3
from pathlib import Path
import subprocess, json
from btf import decode,encode,branch,sha,APP
R=Path(__file__).resolve().parent
BASE=R/'baseline/RT950_R5_RadMod_V0.2_R2M_F4HWN_FULL_XTALP2_RITP0HZ_UNTESTED.BTF'
raw=BASE.read_bytes(); assert __import__('os').environ.get('RADMOD_DEV')=='1' or sha(raw)=='d7842032b53c5de589c34b6f68f002faf4404bf406c37c2c4eb59c6dbb2a2322'
p=decode(raw); assert encode(p,raw)==raw
patches={0x08062a5a:('ca21','d221'),0x08062a76:('4a21','5221'),0x08062b86:('4a20','5220'),0x08062c32:('ca21','d221'),0x08062e98:('4a22','5222')}
def slice_at(x,a,n):return x[a-APP:a-APP+n]
def apply(x,a,old,new):
    assert slice_at(x,a,len(old))==old,(hex(a),slice_at(x,a,len(old)).hex(),old.hex())
    assert len(old)==len(new); x[a-APP:a-APP+len(new)]=new
q=bytearray(p)
for a,(o,n) in patches.items():apply(q,a,bytes.fromhex(o),bytes.fromhex(n))
assert [i+APP for i,(a,b) in enumerate(zip(p,q)) if a!=b]==sorted(patches)
assert slice_at(q,0x080430f4,2)==bytes.fromhex('c221')
assert slice_at(q,0x08064a82,2)==bytes.fromhex('5221')
assert slice_at(q,0x0806501c,2)==bytes.fromhex('5224')
assert slice_at(q,0x0806e0a4,0x800)==slice_at(p,0x0806e0a4,0x800)
b=R/'build';b.mkdir(exist_ok=True)
def cmd(*a):subprocess.run(a,cwd=R,check=True)
cmd('clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-c','tx_offset.S','-o','build/tx_offset.o')
cmd('ld.lld','--no-undefined','-e','tx_offset','-Ttext=0x08071000','--defsym=oem_tx_frequency=0x0801e511','build/tx_offset.o','-o','build/tx_offset.elf')
cmd('llvm-objcopy','-O','binary','--only-section=.text','build/tx_offset.elf','build/tx_offset.bin')
code=(b/'tx_offset.bin').read_bytes();assert len(code)<=0x100
cave=0x08071000; hook=0x0801f2ca
assert slice_at(p,cave,0x100)==b'\xff'*0x100
assert slice_at(p,hook,4)==branch(hook,0x0801e510,True)
r=bytearray(q);apply(r,hook,branch(hook,0x0801e510,True),branch(hook,cave,True));apply(r,cave,b'\xff'*len(code),code)
assert all(i+APP in patches or hook<=i+APP<hook+4 or cave<=i+APP<cave+len(code) for i,(a,b) in enumerate(zip(p,r)) if a!=b)
# Decode from finished BTF and disassemble exact affected ranges.
def disassemble(plain,start,end,name):
    (b/'view.bin').write_bytes(slice_at(plain,start,end-start))
    (b/'view.S').write_text('.syntax unified\n.thumb\n.section .text,"ax",%progbits\n.global entry\n.thumb_func\nentry:\n.incbin "build/view.bin"\n')
    cmd('clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-c','build/view.S','-o','build/view.o')
    cmd('ld.lld','-e','entry','-Ttext='+hex(start),'build/view.o','-o','build/view.elf')
    (b/name).write_text(subprocess.check_output(['llvm-objdump','-d','--triple=thumbv7m-none-eabi','build/view.elf'],cwd=R,text=True))
results=[]
for label,plain in [('GAIN82_PLLP640HZ_VHF_USB',r)]:
    f=encode(bytes(plain),raw);v=decode(f);assert v==bytes(plain) and len(f)==len(raw) and f[:0x800]==raw[:0x800]
    name=f'RT950_R5_RadMod_V0.2_R2N_{label}_UNTESTED.BTF';(R/name).write_bytes(f)
    for a,(old,new) in patches.items():assert slice_at(v,a,2)==bytes.fromhex(new)
    for start,end,tag in [(0x08062a50,0x08062a88,'primer'),(0x08062b68,0x08062b90,'launch_init'),(0x08062c24,0x08062c42,'launch_write'),(0x08062e94,0x08062eb0,'launch_bookkeeping'),(0x080430ec,0x080430fe,'fsk'),(0x0801f2a8,0x0801f2de,'tx_freq')]:disassemble(v,start,end,label+'_'+tag+'.txt')
    if label.endswith('VHF_USB'):disassemble(v,cave,cave+len(code),label+'_offset.txt')
    results.append({'file':name,'sha256':sha(f),'size':len(f),'decoded_byte_changes':sum(a!=b for a,b in zip(p,v)),'hardware_tested':False})
(R/'manifest.json').write_text(json.dumps({'baseline':BASE.name,'baseline_sha256':sha(raw),'reference_patches':{hex(a):v for a,v in patches.items()},'pll_hook':hex(hook),'pll_code':hex(cave),'pll_bytes':len(code),'images':results},indent=2)+'\n');print(json.dumps(results,indent=2))
