from pathlib import Path
import subprocess,json
from btf import *
R=Path(__file__).resolve().parent; APP=0x08003000; START=0x08061400
BASE='RT950_R5_RadMod_FASTSTART_CAT_R11_B_OEM_FREQ_VFO_MODE_UNTESTED.BTF'
raw=(R/BASE).read_bytes();assert __import__('os').environ.get('RADMOD_DEV')=='1' or sha(raw)=='ea81de6b887a366c8cc0629c421369d63f14a3b8674b11a50b9339d5ae4db1f0'
p=decode(raw);assert encode(p,raw)==raw
at=lambda a,n:p[a-APP:a-APP+n]
run=lambda *a:subprocess.check_output(a,cwd=R,text=True)
m=[]
for variant in (1,):
 tag='B_FM_PTT' if variant else 'A_STATUS_ONLY'
 run('clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-Oz','-ffreestanding','-fno-builtin','-ffunction-sections','-fstack-usage',f'-DPTT={variant}','-c','patch.c','-o','patch.o')
 objs=['patch.o']
 if variant:
  run('clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-c','tick.S','-o','tick.o');objs+=['tick.o']
 elf=tag+'.elf';run('ld.lld','-T','link.ld',*objs,'-o',elf)
 assert 'There are no relocations' in run('readelf','-rW',elf)
 run('llvm-objcopy','-O','binary','--only-section=.payload',elf,tag+'.bin');payload=(R/(tag+'.bin')).read_bytes()
 assert len(payload)<0x800 and at(START,len(payload))==b'\xff'*len(payload)
 sym=run('readelf','-sW',elf);addr=lambda name:int(next(x.split()[1] for x in sym.splitlines() if x.endswith(' '+name)),16)&~1
 out=bytearray(p);allowed=set()
 def patch(a,b):
  i=a-APP;out[i:i+len(b)]=b;allowed.update(range(i,i+len(b)))
 def hook(a,old,new,link=False):
  assert at(a,4)==branch(a,old,link), (hex(a),at(a,4).hex(),branch(a,old,link).hex())
  patch(a,branch(a,new,link))
 patch(START,payload);hook(0x08071912,0x08061000,addr('dispatch'))
 if variant:
  hook(0x080717b4,0x08061018,addr('service'),True)
  for a in (0x0801ce78,0x0801ce8a,0x08026326):hook(a,0x080156ce,addr('ptt_input'),True)
  hook(0x08025472,0x0800c9bc,addr('tick'))
 assert out[0x08071ac0-APP:]==p[0x08071ac0-APP:]
 changed={i for i,(a,b) in enumerate(zip(p,out)) if a!=b};assert changed<=allowed
 enc=encode(out,raw);assert len(enc)==len(raw) and decode(enc)==out and enc[:0x800]==raw[:0x800]
 name=f'RT950_R5_RadMod_FASTSTART_CAT_R12_{tag}_UNTESTED.BTF';(R/name).write_bytes(enc)
 (R/(tag+'.dis')).write_text(run('llvm-objdump','-d','--triple=thumbv7em-none-eabi',elf));(R/(tag+'.su')).write_text((R/'patch.su').read_text())
 m.append(dict(image=name,sha256=sha(enc),base_sha256=sha(raw),payload_bytes=len(payload),changed_bytes=len(changed),hardware_tested=False))
(R/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps(m,indent=2))
