from pathlib import Path
import hashlib,json,subprocess
from btf import APP,decode,encode,branch,unbranch
D=Path(__file__).resolve().parent
base=next(D.glob('*R3B*.BTF')); raw=base.read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest()
assert __import__('os').environ.get('RADMOD_DEV')=='1' or sha(raw)=='fba3ff095fc1f60e068606ce2f897b0f5dbcf8ef84f87d2f0c97565a35828fb1'
rom=decode(raw); out=bytearray(rom)
CAVE=0x0807103c; END=0x08071100; HOOK=0x0807101c
assert rom[0x08071000-APP:CAVE-APP].hex()=='0b4991f8fa20022a0fd858235a43114491f8482112f00302022a06d10549884203d30549884200d24030adf771ba000068a4002000badb0040d4e100'
assert rom[CAVE-APP:END-APP]==b'\xff'*(END-CAVE)
assert rom[0x800d94c-APP:0x800d960-APP].hex()=='700c00208dec010895f4010875f3010841f40108'
for args in [['clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-c','trim.S','-o','trim.o'],['ld.lld','-T','trim.ld','-o','trim.elf','trim.o'],['llvm-objcopy','-O','binary','--only-section=.text','trim.elf','trim.bin']]:subprocess.run(args,cwd=D,check=True)
blob=(D/'trim.bin').read_bytes();assert len(blob)<=END-CAVE
patches=[(HOOK,branch(HOOK,CAVE)),(CAVE,blob)]
mask=bytearray(len(rom))
for a,b in patches:out[a-APP:a-APP+len(b)]=b;mask[a-APP:a-APP+len(b)]=b'\1'*len(b)
assert all(x==y or m for x,y,m in zip(rom,out,mask))
assert unbranch(HOOK,out[HOOK-APP:HOOK-APP+4])==CAVE
enc=encode(out,raw);assert len(enc)==len(raw) and decode(enc)==out
name='RT950_R5_RadMod_R3D_BK_INTERPOLATED_USB_TRIM_UNTESTED.BTF';(D/name).write_bytes(enc)
(D/'disassembly.txt').write_text(subprocess.check_output(['llvm-objdump','-d','--triple=thumbv7em-none-eabi','--mcpu=cortex-m4','trim.elf'],cwd=D,text=True))
manifest={'base':base.name,'base_sha256':sha(raw),'file':name,'sha256':sha(enc),'mode':2,'selector_addr':'0x20000c70','secondary_selector':1,'primary_2m_trim_hz':640,'secondary_calibration_hz':[[441200000,1680],[760000000,2500],[999996000,2900]],'outside_range':'clamp','patches':[{'address':hex(a),'length':len(b)} for a,b in patches],'decoded_bytes_changed':sum(x!=y for x,y in zip(rom,out)),'hardware_tested':False}
(D/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))
