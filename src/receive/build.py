#!/usr/bin/env python3
from pathlib import Path
import argparse, json, subprocess, struct
from btf import decode, encode, branch, sha, APP
ROOT=Path(__file__).resolve().parent
BASE=ROOT/'baseline/RT950_R5_RadMod_V0.2_R2D_FIX2_SRAM_RELOC_NO_UART_UNTESTED.BTF'
CAVE=0x08070500; END=0x08071800
ap=argparse.ArgumentParser();ap.add_argument('--raw',action='store_true');ap.add_argument('--mute-test',action='store_true');ap.add_argument('--xtal-steps',type=int,default=2);ap.add_argument('--clarifier-hz',type=int,default=0);a=ap.parse_args()
assert -8<=a.xtal_steps<=8 and -2000<=a.clarifier_hz<=2000 and a.clarifier_hz%10==0
raw=BASE.read_bytes();assert __import__('os').environ.get('RADMOD_DEV')=='1' or sha(raw)=='3cefc87687911dee9582de67778862fb8023dea65457d67e554d1773fa9a2c7a'
p=decode(raw);assert encode(p,raw)==raw
at=lambda addr,n:p[addr-APP:addr-APP+n]
assert at(CAVE,END-CAVE)==b'\xff'*(END-CAVE)
assert at(0x0801ec66,4)==branch(0x0801ec66,0x0801e510,True)
assert at(0x0801ec7a,4)==branch(0x0801ec7a,0x0801ed50,True)
assert at(0x0801e70c,4)==branch(0x0801e70c,0x0801e510,True)
assert at(0x0801f0f0,4)==bytes.fromhex('70b50446')
assert at(0x0801efc6,6)==bytes.fromhex('4720aa689047')
assert at(0x0801ed50,4)==bytes.fromhex('70b50446') and at(0x0801efb0,4)==bytes.fromhex('70b50446')
assert at(0x0801f2ca,4)==branch(0x0801f2ca,0x0801e510,True)
assert at(0x0801f2f2,4)==branch(0x0801f2f2,0x0801f114)
assert at(0x0801f2b8,4)==branch(0x0801f2b8,0x0801ed50,True)
assert at(0x0801ec84,4)==branch(0x0801ec84,0x0801efb0)
assert int.from_bytes(p[:4],'little')==0x20015f78
# Check all halfword-aligned absolute RAM literals in new SRAM regions.
refs=[]
for off in range(0,len(p)-3,2):
    v=int.from_bytes(p[off:off+4],'little')
    if 0x20015f78<=v<0x20015fa0 or 0x20015fd0<=v<0x20016000:refs.append((APP+off,v))
assert refs==[(0x08003000,0x20015f78),(0x080032d4,0x20015f78)],refs
profile='USB_MUTE_DIAG' if a.mute_test else ('RAW' if a.raw else 'F4HWN_FULL')
label=f'{profile}_XTAL{a.xtal_steps:+d}_RIT{a.clarifier_hz:+d}HZ'.replace('+','P').replace('-','M')
b=ROOT/'build';b.mkdir(exist_ok=True)
opts=[f'-DMUTE_TEST={int(a.mute_test)}',f'-DRAW_PROFILE={int(a.raw)}',f'-DXTAL_STEPS={a.xtal_steps}',f'-DCLARIFIER_HZ={a.clarifier_hz}']
def cmd(*args):subprocess.run(args,cwd=ROOT,check=True)
cmd('clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-ffreestanding','-fno-builtin','-fno-unwind-tables','-fno-stack-protector','-Os','-Wall','-Wextra','-Werror',*opts,'-c','src/rx.c','-o','build/rx.o')
cmd('clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-c','src/entry.S','-o','build/entry.o')
cmd('ld.lld','--no-undefined','-T','src/rx.ld','build/entry.o','build/rx.o','-o','build/rx.elf')
cmd('llvm-objcopy','-O','binary','--only-section=.ext.text','build/rx.elf','build/rx.bin')
syms={x.split()[-1]:int(x.split()[0],16)&~1 for x in subprocess.check_output(['nm','-n',str(b/'rx.elf')],text=True).splitlines() if len(x.split())==3}
code=(b/'rx.bin').read_bytes();assert len(code)<END-CAVE
param=syms['clarifier_10hz'];assert code[param-CAVE:param-CAVE+4]==struct.pack('<i',a.clarifier_hz//10)
patches={0x0801ed50:branch(0x0801ed50,syms['link_entry']),0x0801ec66:branch(0x0801ec66,syms['clarifier_entry'],True),0x0801e70c:branch(0x0801e70c,syms['clarifier_entry'],True),0x0801f0f0:branch(0x0801f0f0,syms['direct_freq_entry']),0x0801efc6:branch(0x0801efc6,syms['af_write_entry'],True)+bytes.fromhex('00bf'),0x0801efb0:branch(0x0801efb0,syms['audio_entry']),CAVE:code}
o=bytearray(p)
for k,v in patches.items():o[k-APP:k-APP+len(v)]=v
allowed=set().union(*(set(range(k-APP,k-APP+len(v))) for k,v in patches.items()))
diff={i for i,(x,y) in enumerate(zip(p,o)) if x!=y};assert diff<=allowed
assert o[0x0801f2a8-APP:0x0801f2fa-APP]==p[0x0801f2a8-APP:0x0801f2fa-APP]
assert o[0x0806fc00-APP:CAVE-APP]==p[0x0806fc00-APP:CAVE-APP]
fw=encode(bytes(o),raw);assert decode(fw)==bytes(o) and len(fw)==455680 and fw[:0x800]==raw[:0x800]
name=f'RT950_R5_RadMod_V0.2_R2M_{label}_UNTESTED.BTF';(ROOT/name).write_bytes(fw)
# Disassemble *decoded output* actual hook regions, not just compiled object.
for start,end,tag in [(0x0801ec4c,0x0801ec8c,'RX_CALLS'),(0x0801e6f4,0x0801e728,'RX_RETUNE'),(0x0801f0f0,0x0801f114,'DIRECT_FREQ'),(0x0801ed50,0x0801edd0,'LINK'),(0x0801efb0,0x0801f01c,'AUDIO'),(0x0801f2a8,0x0801f2fa,'TX_UNCHANGED')]:
    (b/'view.bin').write_bytes(decode(fw)[start-APP:end-APP]);(b/'view.S').write_text('.syntax unified\n.thumb\n.section .text,"ax",%progbits\n.global entry\n.thumb_func\nentry:\n.incbin "build/view.bin"\n')
    cmd('clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-c','build/view.S','-o','build/view.o')
    cmd('ld.lld','-e','entry','-Ttext='+hex(start),'build/view.o','-o','build/view.elf')
    (b/f'{label}_{tag}.txt').write_text(subprocess.check_output(['llvm-objdump','-d','--triple=thumbv7m-none-eabi',str(b/'view.elf')],text=True))
(b/f'{label}_OVERLAY.txt').write_text(subprocess.check_output(['llvm-objdump','-d','--triple=thumbv7m-none-eabi',str(b/'rx.elf')],text=True))
cmd('clang','-DHOST_TEST','-std=c11','-O2','-Wall','-Wextra','-Werror',*opts,'tests/test.c','-o','build/test');cmd(str(b/'test'))
m={'baseline':BASE.name,'baseline_sha256':sha(raw),'output':name,'sha256':sha(fw),'size':len(fw),'profile':profile,'xtal_steps':a.xtal_steps,'clarifier_hz':a.clarifier_hz,'clarifier_param':hex(param),'code_bytes':len(code),'changed_bytes':len(diff),'regions':{hex(k):len(v) for k,v in patches.items()},'symbols':{k:hex(syms[k]) for k in ['link_entry','link_original','clarifier_entry','direct_freq_entry','af_write_entry','audio_entry','install','select_usb','unmute_usb','before_link','after_link','intercept_af','audio_route']},'candidate_sram':['0x20015f78-0x20015f9f','0x20015fd0-0x20015fff'],'readback_masks':['0x20015f9c','0x20015ff4'],'mute_test':a.mute_test,'hardware_tested':False}
(ROOT/f'manifest_{label}.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m,indent=2))
