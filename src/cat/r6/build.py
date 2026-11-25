from pathlib import Path
import subprocess,json
from btf import sha,decode,encode,branch,unbranch
R=Path(__file__).resolve().parent
APP=0x08003000; HOOK=0x08025686; CAVE=0x08071b00; OEM=0x0800c4ec
BASE='RT950_R5_RadMod_R3D_FASTSTART_R1_UNTESTED.BTF'; R4='RT950_R5_RadMod_FASTSTART_CAT_R4_DIAG_GPIO_ECHO_UNTESTED.BTF'
raw=(R/BASE).read_bytes(); assert __import__('os').environ.get('RADMOD_DEV')=='1' or sha(raw)=='dd75c081f52db999a0536061e5c9faf13a2d5f355fd1cd8cadcefdd79602dd69'
p=decode(raw);assert encode(p,raw)==raw
at=lambda a,n:p[a-APP:a-APP+n]
assert at(HOOK,4).hex()=='e6f731bf' and unbranch(HOOK,at(HOOK,4))==OEM
assert at(0x08025680,6).hex()=='bde81040c0b2'
def run(*a):return subprocess.check_output(a,cwd=R,text=True)
manifest=[]
for multi,tag in [(1,'B_FIXED_FRAME')]:
 stem=f'probe_{multi}';run('clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb',f'-DMULTI={multi}','-c','probe.S','-o',stem+'.o')
 run('ld.lld','-T','link.ld',stem+'.o','-o',stem+'.elf');run('llvm-objcopy','-O','binary',stem+'.elf',stem+'.bin');assert 'There are no relocations' in run('readelf','-rW',stem+'.elf')
 code=(R/(stem+'.bin')).read_bytes();assert 0<len(code)<=256 and at(CAVE,len(code))==b'\xff'*len(code);assert unbranch(CAVE+len(code)-4,code[-4:])==OEM
 out=bytearray(p);out[CAVE-APP:CAVE-APP+len(code)]=code;out[HOOK-APP:HOOK-APP+4]=branch(HOOK,CAVE);assert unbranch(HOOK,out[HOOK-APP:HOOK-APP+4])==CAVE
 changed={i for i,(x,y) in enumerate(zip(p,out)) if x!=y};assert changed<=set(range(CAVE-APP,CAVE-APP+len(code)))|set(range(HOOK-APP,HOOK-APP+4));enc=encode(out,raw);assert len(enc)==455680 and decode(enc)==out and enc[:0x800]==raw[:0x800]
 name=f'RT950_R5_RadMod_FASTSTART_CAT_R6_{tag}_UNTESTED.BTF';(R/name).write_bytes(enc);dis=run('llvm-objdump','-d','--triple=thumbv7em-none-eabi',stem+'.elf');(R/(stem+'_disassembly.txt')).write_text(dis);print(dis)
 manifest.append(dict(image=name,sha256=sha(enc),payload_bytes=len(code),changed_bytes=len(changed),hardware_tested=False))
(R/'manifest.json').write_text(json.dumps(dict(base=BASE,base_sha256=sha(raw),builds=manifest),indent=2));print((R/'manifest.json').read_text())
