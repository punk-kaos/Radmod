#!/usr/bin/env python3
"""Compile the recovered RadMod overlays and generate a stock-to-release patch."""
import argparse, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from btf import APP,decode,encode,sha,branch
from patch import apply,make_manifest
OEM='53226024c9b4a782c85556a120afa5e690c132a85bf4048e59d2d193e5eaf272'
RELEASE='069e7de2e96b6eb84b57eabd8b2b4020de5d91b86b1b17e0bb85f4723dac8a89'
ARM=['clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb']

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--oem',required=True,type=Path);p.add_argument('--out',type=Path,default=ROOT/'build');p.add_argument('--dev',action='store_true',help='Allow a changed final hash; local preimage and cave checks still apply.');a=p.parse_args()
    if not __debug__:p.error('Do not run with Python -O: assertions enforce patch guards')
    stock=a.oem.read_bytes()
    if sha(stock)!=OEM:p.error('Expected RT_950Pro_V0.29_260617.BTF with SHA-256 '+OEM)
    for tool in ['clang','ld.lld','llvm-objcopy','llvm-objdump','readelf','nm']:
        if not shutil.which(tool):p.error('Missing build dependency '+tool)
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True);env=dict(os.environ);env['RADMOD_DEV']='1' if a.dev else '0';env.pop('PYTHONOPTIMIZE',None)
    stages=[]
    with tempfile.TemporaryDirectory(prefix='radmod-') as td, (out/'build.log').open('w') as log:
        w=Path(td); shutil.copytree(ROOT/'src',w/'src');
        def run(cwd,*cmd):
            log.write(f'[{cwd.relative_to(w)}] '+ ' '.join(map(str,cmd))+'\n');log.flush()
            subprocess.run([str(c) for c in cmd],cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        def stage(name,data):
            stages.append({'stage':name,'sha256':sha(data),'bytes':len(data)});print(name,sha(data),flush=True);return data
        def load(n):return json.loads((ROOT/'patches'/n).read_text())
        def delta_stage(raw,n):return apply(raw,load(n),strict=not a.dev)
        def source_stage(raw,folder,infile,outfile,script='build.py',prep=None):
            d=w/'src'/folder;shutil.copyfile(ROOT/'tools/btf.py',d/'btf.py');f=d/infile;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(raw)
            if prep:prep(d)
            run(d,sys.executable,script)
            return stage(folder,(d/outfile).read_bytes())
        r=stage('legacy OEM overlay',delta_stage(stock,'legacy_oem_to_uhf_r1.json'))
        def edit(q,addr,old,new):
            i=addr-APP;assert len(old)==len(new) and q[i:i+len(old)]==old,hex(addr)
            q[i:i+len(new)]=new
        def symbol(d,elf,name):
            lines=subprocess.check_output(['readelf','-sW',str(d/elf)],text=True).splitlines()
            return int(next(line.split()[1] for line in lines if line.split()[-1:]==[name]),16)&~1
        # FIX2 gate: compile the actual source and install three entry hooks;
        # leave the original UART reporting hook intact.
        d=w/'src/ssb/gate';flags=['-ffreestanding','-fno-builtin','-fno-unwind-tables'];run(d,*ARM,*flags,'-O2','-fno-stack-protector','-c','src/gate.c','-o','gate.o');run(d,*ARM,*flags,'-c','src/gate_entry.S','-o','entry.o');run(d,'ld.lld','--no-undefined','-T','src/gate.ld','entry.o','gate.o','-o','gate.elf');run(d,'llvm-objcopy','-O','binary','--only-section=.gate.text','gate.elf','gate.bin')
        q=bytearray(decode(r));blob=(d/'gate.bin').read_bytes();assert len(blob)<0x08070500-0x0806fcc0
        edit(q,0x0806fcc0,b'\xff'*len(blob),blob)
        for addr,old,name,link in [(0x080621ec,bytes.fromhex('42f48002'),'gate_adc_entry',False),(0x080622f4,branch(0x080622f4,0x08063cd8),'gate_hilbert_entry',False),(0x08062b34,branch(0x08062b34,0x0806472c,True),'gate_voice_begin_entry',True)]:
            edit(q,addr,old,branch(addr,symbol(d,'gate.elf',name),link))
        run(d,'clang','-O2','tests/test_gate.c','-o','test_gate');run(d,str(d/'test_gate'))
        r=stage('ssb/gate',encode(bytes(q),r))
        r=source_stage(r,'receive','baseline/RT950_R5_RadMod_V0.2_R2D_FIX2_SRAM_RELOC_NO_UART_UNTESTED.BTF','RT950_R5_RadMod_V0.2_R2M_F4HWN_FULL_XTALP2_RITP0HZ_UNTESTED.BTF')
        r=source_stage(r,'ssb/carrier','baseline/RT950_R5_RadMod_V0.2_R2M_F4HWN_FULL_XTALP2_RITP0HZ_UNTESTED.BTF','RT950_R5_RadMod_V0.2_R2N_GAIN82_PLLP640HZ_VHF_USB_UNTESTED.BTF')
        r=stage('ssb/tables',delta_stage(r,'ssb_tables.json'))
        d=w/'src/ssb/idle';run(d,*ARM,'-c','b.S','-o','b.o');run(d,'llvm-objcopy','-O','binary','--only-section=.text','b.o','b.bin');b=(d/'b.bin').read_bytes();q=bytearray(decode(r));assert len(b)<=128
        edit(q,0x08071100,b'\xff'*len(b),b)
        edit(q,0x08064c3c,bytes.fromhex('01f00f01'),branch(0x08064c3c,0x08071100+symbol(d,'b.o','apply_b'),True))
        r=stage('ssb/idle',encode(bytes(q),r))
        r=source_stage(r,'ssb/encoder','RT950_R5_RadMod_R2T_IDLE82_LIVE_VOICE_UNTESTED.BTF','RT950_R5_RadMod_R3B_SRAM16_STAGED_LIVE_G20_UART_UNTESTED.BTF')
        r=source_stage(r,'ssb/trim','RT950_R5_RadMod_R3B_SRAM16_STAGED_LIVE_G20_UART_UNTESTED.BTF','RT950_R5_RadMod_R3D_BK_INTERPOLATED_USB_TRIM_UNTESTED.BTF')
        r=source_stage(r,'ssb/faststart','RT950_R5_RadMod_R3D_BK_INTERPOLATED_USB_TRIM_UNTESTED.BTF','RT950_R5_RadMod_R3D_FASTSTART_R1_UNTESTED.BTF')
        fast='RT950_R5_RadMod_R3D_FASTSTART_R1_UNTESTED.BTF'; cat=lambda n,s:f'RT950_R5_RadMod_FASTSTART_CAT_R{n}_{s}_UNTESTED.BTF'
        previous=fast
        for n,s in [(6,'B_FIXED_FRAME'),(7,'LIVE_FREQ'),(9,'RELOCATED_MODE'),(10,'B_SET_FREQ'),(11,'B_OEM_FREQ_VFO_MODE'),(12,'B_FM_PTT')]:
            nextname=cat(n,s);r=source_stage(r,f'cat/r{n}',previous,nextname);previous=nextname
        def lsb(d):
            shutil.copyfile(ROOT/'patches/lsb_ui.json',d/'lsb_ui.json');run(d,*ARM,'-c','lsb.S','-o','lsb.o');run(d,'ld.lld','-T','link.ld','lsb.o','-o','lsb.elf');run(d,'llvm-objcopy','-O','binary','--only-section=.text','lsb.elf','lsb.bin')
        r=source_stage(r,'modulation/lsb',previous,'RT950_R5_RadMod_R12B_LSB_R1_UNTESTED.BTF',prep=lsb)
        def am(d):
            run(d,*ARM,'-Oz','-ffreestanding','-fno-builtin','-fno-unwind-tables','-c','am.c','-o','am.o');run(d,*ARM,'-c','hooks.S','-o','hooks.o');run(d,'ld.lld','-T','link.ld','hooks.o','am.o','-o','am.elf');run(d,'llvm-objcopy','-O','binary','--only-section=.payload','am.elf','am.bin');run(d,sys.executable,'host_test.py')
        r=source_stage(r,'modulation/am','RT950_R5_RadMod_R12B_LSB_R1_UNTESTED.BTF','RT950_R5_RadMod_R12B_LSB_R1_AM_PWM16_R3_UNTESTED.BTF',prep=am)
        r=source_stage(r,'ui','RT950_R5_RadMod_R12B_LSB_R1_AM_PWM16_R3_UNTESTED.BTF','RT950_R5_RadMod_V1.0Alpha1.BTF',script='build_version.py')
        if not a.dev and sha(r)!=RELEASE:raise ValueError('Release hash mismatch: '+sha(r))
        patch=make_manifest(stock,r);assert apply(stock,patch)==r
        (out/'radmod.patch.json').write_text(json.dumps(patch,indent=2)+'\n');(out/('RT950_R5_RadMod_DEV_UNTESTED.BTF' if a.dev else 'RT950_R5_RadMod_V1.0Alpha1.BTF')).write_bytes(r)
        (out/'manifest.json').write_text(json.dumps({'oem_sha256':sha(stock),'release_sha256':sha(r),'release_match':sha(r)==RELEASE,'stages':stages,'hardware_tested':False},indent=2)+'\n')
        print('PASS: OEM patch round-trip; release match:',sha(r)==RELEASE)
if __name__=='__main__':main()
