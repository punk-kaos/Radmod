from pathlib import Path
import subprocess,json
from btf import sha,decode,encode,branch,unbranch
R=Path(__file__).resolve().parent
APP=0x08003000; SITE=0x08071b7a; EXT=0x08071ac0
BASE='RT950_R5_RadMod_FASTSTART_CAT_R7_LIVE_FREQ_UNTESTED.BTF'
NAME='RT950_R5_RadMod_FASTSTART_CAT_R9_RELOCATED_MODE_UNTESTED.BTF'
raw=(R/BASE).read_bytes(); assert __import__('os').environ.get('RADMOD_DEV')=='1' or sha(raw)=='a08bb29ef14a6a1feffde4d25b75421b8107fc62177ecb099a058b0d55db1ab4'
p=decode(raw); assert encode(p,raw)==raw
at=lambda a,n:p[a-APP:a-APP+n]
assert at(SITE,6).hex()=='01224a607047'
assert unbranch(0x08025686,at(0x08025686,4))==0x08071b00
assert unbranch(0x08071b54,at(0x08071b54,4))==0x08071b84
run=lambda *a:subprocess.check_output(a,cwd=R,text=True)
run('clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-c','mode.S','-o','mode.o')
run('ld.lld','-T','link.ld','mode.o','-o','mode.elf');run('llvm-objcopy','-O','binary','mode.elf','mode.bin')
assert 'There are no relocations' in run('readelf','-rW','mode.elf')
code=(R/'mode.bin').read_bytes();assert len(code)<128 and at(EXT,len(code))==b'\xff'*len(code)
out=bytearray(p);out[SITE-APP:SITE-APP+4]=branch(SITE,EXT);out[EXT-APP:EXT-APP+len(code)]=code
assert unbranch(SITE,out[SITE-APP:SITE-APP+4])==EXT
changed={i for i,(x,y) in enumerate(zip(p,out)) if x!=y};assert changed<=set(range(SITE-APP,SITE-APP+4))|set(range(EXT-APP,EXT-APP+len(code)))
assert out[0x08071b84-APP:0x08071be0-APP]==p[0x08071b84-APP:0x08071be0-APP]
assert __import__('os').environ.get('RADMOD_DEV')=='1' or sha(code)=='bb1290475486904ec78dd2ba900afba5fd4d8579ddd40a9522ac601978bb9bb1'
assert EXT+len(code)<=0x08071c00
assert out[0x08071c00-APP:]==p[0x08071c00-APP:]
assert at(EXT, len(code))==bytes([255])*len(code)
enc=encode(out,raw);assert len(enc)==455680 and decode(enc)==out and enc[:0x800]==raw[:0x800]
# Verify the mapping arithmetic, not MCU execution or the hardware enum.
for v in range(256):assert (0x0148>>((v&3)*4))&15==[8,4,1,0][v&3]
(R/NAME).write_bytes(enc)
dis=run('llvm-objdump','-d','--triple=thumbv7em-none-eabi','mode.elf');(R/'disassembly.txt').write_text(dis);print(dis)
m=dict(base=BASE,base_sha256=sha(raw),image=NAME,sha256=sha(enc),extension_bytes=len(code),changed_bytes=len(changed),mode_mapping_model_vectors=256,hardware_tested=False,extension_address=hex(EXT),last_1k_unchanged=True,r8_payload_byte_identical=True)
(R/'manifest.json').write_text(json.dumps(m,indent=2));print(m)
