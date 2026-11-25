from pathlib import Path
import subprocess,json
from btf import *
R=Path(__file__).resolve().parent
APP=0x08003000; START=0x08061000
BASE='RT950_R5_RadMod_FASTSTART_CAT_R10_B_SET_FREQ_UNTESTED.BTF'
raw=(R/BASE).read_bytes(); assert __import__('os').environ.get('RADMOD_DEV')=='1' or sha(raw)=='6d2f5189bc353db52aca91078d10fc3b8ec7bc0889b8e98e1a9951b6e6d3143e'
p=decode(raw); assert encode(p,raw)==raw
at=lambda a,n:p[a-APP:a-APP+n]
assert at(0x08071912,4)==bytes.fromhex('012808d1')
assert at(0x080717b4,4)==branch(0x080717b4,0x08071940,link=True)
run=lambda *a:subprocess.check_output(a,cwd=R,text=True)
m=[]
for variant in (1,):
 tag='B_OEM_FREQ_VFO_MODE' if variant else 'A_VFO_MODE'
 run('clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-c','dispatch.S','-o','dispatch.o')
 run('clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-Oz','-ffreestanding','-fno-builtin','-ffunction-sections','-fstack-usage',f'-DEXPANDED={variant}','-c','service.c','-o','service.o')
 elf=tag+'.elf';run('ld.lld','-T','link.ld','dispatch.o','service.o','-o',elf)
 assert 'There are no relocations' in run('readelf','-rW',elf)
 run('llvm-objcopy','-O','binary','--only-section=.payload',elf,tag+'.bin');payload=(R/(tag+'.bin')).read_bytes()
 assert len(payload)<0x800 and at(START,len(payload))==b'\xff'*len(payload)
 sym=run('readelf','-sW',elf); addr=lambda name:int(next(x.split()[1] for x in sym.splitlines() if x.endswith(' '+name)),16)&~1
 assert addr('dispatch')==START
 out=bytearray(p); allowed=set()
 def patch(a,b):
  i=a-APP;out[i:i+len(b)]=b;allowed.update(range(i,i+len(b)))
 patch(START,payload);patch(0x08071912,branch(0x08071912,START));patch(0x080717b4,branch(0x080717b4,addr('service_new'),link=True))
 assert unbranch(0x08071912,out[0x08071912-APP:0x08071916-APP])==START
 assert out[0x08071ac0-APP:]==p[0x08071ac0-APP:]
 changed={i for i,(a,b) in enumerate(zip(p,out)) if a!=b};assert changed<=allowed
 enc=encode(out,raw);assert len(enc)==len(raw) and decode(enc)==out and enc[:0x800]==raw[:0x800]
 name=f'RT950_R5_RadMod_FASTSTART_CAT_R11_{tag}_UNTESTED.BTF';(R/name).write_bytes(enc)
 (R/(tag+'.dis')).write_text(run('llvm-objdump','-d','--triple=thumbv7em-none-eabi',elf));(R/(tag+'.su')).write_text((R/'service.su').read_text())
 m.append(dict(image=name,sha256=sha(enc),base_sha256=sha(raw),payload_bytes=len(payload),changed_bytes=len(changed),dispatch=hex(START),service=hex(addr('service_new')),hardware_tested=False))
(R/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps(m,indent=2))
