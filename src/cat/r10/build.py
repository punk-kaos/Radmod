from pathlib import Path
import subprocess,json,struct
from btf import *
R=Path(__file__).resolve().parent
APP=0x08003000; BASE='RT950_R5_RadMod_FASTSTART_CAT_R9_RELOCATED_MODE_UNTESTED.BTF'
raw=(R/BASE).read_bytes(); assert __import__('os').environ.get('RADMOD_DEV')=='1' or sha(raw)=='bc0733c60d6a0d2d48c4ace5eaa184d489f0178ac4371a3543c4515d67b02486'; p=decode(raw); assert encode(p,raw)==raw
at=lambda a,n:p[a-APP:a-APP+n]
assert unbranch(0x08025686,at(0x08025686,4))==0x08071b00
SITE=0x08019d86
# OEM main foreground address 0x08019D86 (not 0x080019D86)
assert at(SITE,4)==branch(SITE,0x0800d2d4,link=True)
run=lambda *a:subprocess.check_output(a,cwd=R,text=True)
m=[]
for variant in (1,):
 tag='B_SET_FREQ' if variant else 'A_FRAME_ONLY'
 run('clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb',f'-DSETTER={variant}','-c','parser.S','-o','parser.o')
 objs=['parser.o']
 if variant:
  run('clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-Oz','-ffreestanding','-fno-builtin','-ffunction-sections','-fstack-usage','-c','setter.c','-o','setter.o');objs+=['setter.o']
 elf=f'{tag}.elf';run('ld.lld','-T','link.ld',*objs,'-o',elf)
 assert 'There are no relocations' in run('readelf','-rW',elf)
 out=bytearray(p);allowed=set(); sizes={}
 def patch(a,b,expect=None):
  i=a-APP; assert expect is None or at(a,len(b))==expect;out[i:i+len(b)]=b;allowed.update(range(i,i+len(b)))
 for sec,addr,cap in [('.aux',0x08071778,136),('.payload',0x080718b0,528)]:
  name=tag+sec+'.bin';run('llvm-objcopy','-O','binary','--only-section='+sec,elf,name);b=(R/name).read_bytes();assert 0<len(b)<=cap,(sec,len(b));patch(addr,b,b'\xff'*len(b));sizes[sec]=len(b)
 patch(0x08025686,branch(0x08025686,0x080718b0))
 if variant:
  sym=run('readelf','-sW',elf);a=int(next(x.split()[1] for x in sym.splitlines() if x.endswith(' forehook')),16)&~1;patch(SITE,branch(SITE,a,link=True))
 assert out[0x08071ac0-APP:0x08071c00-APP]==p[0x08071ac0-APP:0x08071c00-APP]
 assert out[0x08071c00-APP:]==p[0x08071c00-APP:]
 changed={i for i,(a,b) in enumerate(zip(p,out)) if a!=b};assert changed<=allowed
 enc=encode(out,raw);assert len(enc)==455680 and decode(enc)==out and enc[:0x800]==raw[:0x800]
 name=f'RT950_R5_RadMod_FASTSTART_CAT_R10_{tag}_UNTESTED.BTF';(R/name).write_bytes(enc)
 (R/(tag+'.dis')).write_text(run('llvm-objdump','-d','--triple=thumbv7em-none-eabi',elf))
 m.append(dict(image=name,sha256=sha(enc),base_sha256=sha(raw),sections=sizes,changed_bytes=len(changed),hardware_tested=False,foreground_hook=bool(variant)))
(R/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps(m,indent=2))
