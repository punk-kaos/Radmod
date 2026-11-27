#!/usr/bin/env python3
"""Rebuild the Alpha2 continuation from source with exact archived SHA-256 guards."""
import argparse, json, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from btf import APP,decode,encode,sha,branch
BASE_SHA='c6f6d66eccf5e05a5bc059da4ad7912b8f9306699a685cdfc492749de0c10ec4'
STAGES=json.loads((ROOT/'docs/alpha2-build-chain.json').read_text())
ARM=['clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb']

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,default=ROOT/'RT950_R5_RadMod_V1.0Alpha2.BTF')
    p.add_argument('--out',type=Path,default=ROOT/'build/alpha2')
    p.add_argument('--target',choices=[s['target'] for s in STAGES],default='acc1500')
    a=p.parse_args()
    if not __debug__:p.error('Do not use Python -O')
    raw=a.base.read_bytes()
    if len(raw)!=455680 or sha(raw)!=BASE_SHA:p.error('Incorrect Alpha2 base image')
    a.out.mkdir(parents=True,exist_ok=True)
    completed=[]
    for stage in STAGES:
        kind=stage['target'];folder=ROOT/stage['folder']
        plain=decode(raw);assert encode(plain,raw)==raw
        out=bytearray(plain)
        def patch(addr,old,new):
            i=addr-APP;assert len(old)==len(new) and plain[i:i+len(old)]==old,hex(addr)
            out[i:i+len(new)]=new
        with tempfile.TemporaryDirectory(prefix='radmod-alpha2-') as temp:
            d=Path(temp)
            def run(*args):return subprocess.check_output(args,cwd=d,text=True)
            flags=['-Oz','-ffreestanding','-fno-builtin'] if kind=='bc203' else []
            run(*ARM,*flags,'-c',str(folder/stage['source']),'-o','payload.o')
            run('ld.lld','-T',str(folder/stage['linker']),'payload.o','-o','payload.elf')
            assert 'There are no relocations' in run('readelf','-rW','payload.elf')
            run('llvm-objcopy','-O','binary','--only-section=.payload','payload.elf','payload.bin')
            blob=(d/'payload.bin').read_bytes();addr=stage['address']
            assert stage['size'] is None or len(blob)==stage['size']
            if kind=='bt-cat':
                patch(addr,b'\xff'*len(blob),blob)
                syms=run('readelf','-sW','payload.elf')
                def symbol(n):return int(next(x.split()[1] for x in syms.splitlines() if x.endswith(' '+n)),16)&~1
                for at,old,name in [(0x08025686,'4cf013b9','wire_rx'),(0x0800a4ac,'c1b21648','ble_rx'),(0x08071778,'844644f60041','ack_hook'),(0x08071b16,'44f60041c4f20001','reply_hook'),(0x08071bd2,'44f60041c4f20001','packed_hook')]:
                    old=bytes.fromhex(old);patch(at,old,branch(at,symbol(name))+b'\x00\xbf'*((len(old)-4)//2))
            elif kind=='bc203':
                patch(addr,b'\xff'*len(blob),blob)
                patch(0x0806192c,bytes.fromhex('01f6a660'),branch(0x0806192c,addr,link=True))
                for at,old,new in [(0x08061784,'40f6a661','41f2f951'),(0x08061c12,'40f6a660','41f2f950'),(0x08061d72,'40f6a663','41f2f953')]:
                    patch(at,bytes.fromhex(old),bytes.fromhex(new))
            else:
                assert addr==0x08061694 and len(blob)<=344
                i=addr-APP;end=i+344
                expected={'pair-r2':'6c9f1d3b0fd9ed5d96bbdf93b3557778e41d622d9e196a6a40021d9128276cad','acc1500':'4b7e02a7388e6932e8d774bf7cec80eb51338544b0b8610113abda2cee9e8b24','i400x1':'c05e399e40c3c3ac893b340b5f1742fbf79a02410b4bc90dd62b097844fd0bb4'}[kind]
                assert sha(plain[i:end])==expected
                patch(addr,plain[i:i+len(blob)],blob)
                assert out[:i]==plain[:i] and out[end:]==plain[end:]
            (a.out/(kind+'.dis')).write_text(run('llvm-objdump','-d','--triple=thumbv7em-none-eabi','payload.elf'))
        result=encode(bytes(out),raw)
        assert len(result)==455680 and result[:0x800]==raw[:0x800] and decode(result)==out
        if sha(result)!=stage['sha256']:raise ValueError(kind+' output SHA-256 mismatch: '+sha(result))
        (a.out/stage['output']).write_bytes(result);completed.append(stage)
        print(stage['output'],sha(result),flush=True);raw=result
        if kind==a.target:break
    (a.out/'manifest.json').write_text(json.dumps({'target':a.target,'stages':completed,'final_sha256':sha(raw),'status':completed[-1]['status']},indent=2)+'\n')
if __name__=='__main__':main()
