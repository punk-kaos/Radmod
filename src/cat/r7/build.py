from pathlib import Path
import subprocess,json,random
from btf import sha,decode,encode,branch,unbranch
R=Path(__file__).resolve().parent
APP=0x08003000; REPLACE=0x08071b54; EXT=0x08071b84; RESUME=0x08071b58
BASE='RT950_R5_RadMod_FASTSTART_CAT_R6_B_FIXED_FRAME_UNTESTED.BTF'
NAME='RT950_R5_RadMod_FASTSTART_CAT_R7_LIVE_FREQ_UNTESTED.BTF'
raw=(R/BASE).read_bytes();assert __import__('os').environ.get('RADMOD_DEV')=='1' or sha(raw)=='0ed2105fdc2a57803816e8cf80215626f43f78d5af15565b63f76ebff0135501'
p=decode(raw);assert encode(p,raw)==raw
at=lambda a,n:p[a-APP:a-APP+n]
assert at(REPLACE,6).hex()=='44f2142c0423'
assert unbranch(0x08025686,at(0x08025686,4))==0x08071b00
run=lambda *a:subprocess.check_output(a,cwd=R,text=True)
run('clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-c','live.S','-o','live.o')
run('ld.lld','-T','link.ld','live.o','-o','live.elf');run('llvm-objcopy','-O','binary','live.elf','live.bin');assert 'There are no relocations' in run('readelf','-rW','live.elf')
code=(R/'live.bin').read_bytes();assert len(code)<0x100 and at(EXT,len(code))==b'\xff'*len(code)
assert unbranch(EXT+len(code)-6,code[-6:-2])==RESUME
out=bytearray(p);out[REPLACE-APP:REPLACE-APP+4]=branch(REPLACE,EXT);out[EXT-APP:EXT-APP+len(code)]=code
assert unbranch(REPLACE,out[REPLACE-APP:REPLACE-APP+4])==EXT
changed={i for i,(x,y) in enumerate(zip(p,out)) if x!=y};assert changed<=set(range(REPLACE-APP,REPLACE-APP+4))|set(range(EXT-APP,EXT-APP+len(code)))
enc=encode(out,raw);assert len(enc)==455680 and decode(enc)==out and enc[:0x800]==raw[:0x800]
# Model exact arithmetic sequence; not MCU execution.
def model(f):
    acc=0
    for _ in range(8):
        q,d=divmod(f,10);acc=(acc>>4)|(d<<28);f=q
    return acc.to_bytes(4,'big')+b'\x01'
rng=random.Random(817)
for f in [10000,14420000,43500000,1815000,99999999]+[rng.randrange(10000,100000000) for _ in range(10000)]:
    assert model(f)==bytes.fromhex(f'{f:08d}01')
assert model(14420000).hex()=='1442000001'
(R/NAME).write_bytes(enc)
dis=run('llvm-objdump','-d','--triple=thumbv7em-none-eabi','live.elf');(R/'disassembly.txt').write_text(dis);print(dis)
m=dict(base=BASE,base_sha256=sha(raw),image=NAME,sha256=sha(enc),extension_bytes=len(code),changed_bytes=len(changed),arithmetic_model_vectors=10005,hardware_tested=False)
(R/'manifest.json').write_text(json.dumps(m,indent=2));print(m)
