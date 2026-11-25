from pathlib import Path
import hashlib,subprocess,json,re
from btf import *
D=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
raw=(D/'RT950_R5_RadMod_R2T_IDLE82_LIVE_VOICE_UNTESTED.BTF').read_bytes();assert __import__('os').environ.get('RADMOD_DEV')=='1' or sha(raw)=='c5611c097a563708dae9f7fa5d24ce97b935470dd15de58175b1d2a1e0647b73';rom=decode(raw)
CAVE=0x8071180;END=0x8071800;IQ=0x8064a94;TICK=0x8064fee;SERIAL=0x8064d08
assert rom[CAVE-APP:END-APP]==b'\xff'*(END-CAVE)
for a,old in [(IQ,'02460028'),(TICK,'f7f71bfc'),(SERIAL,'f0b581b0')]:assert rom[a-APP:a-APP+4]==bytes.fromhex(old)
assert unbranch(0x805c828,rom[0x805c828-APP:0x805c82c-APP])==0x806217c
assert unbranch(0x8063cce,rom[0x8063cce-APP:0x8063cd2-APP])==IQ
assert unbranch(0x804d89c,rom[0x804d89c-APP:0x804d8a0-APP])==SERIAL
subprocess.run(['clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-c','fir_ram.S','-o','fir_ram.o'],check=True)
subprocess.run(['llvm-objcopy','-O','binary','--only-section=.text.fir_ram','fir_ram.o','fir_ram.bin'],check=True)
subprocess.run(['clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-mfloat-abi=soft','-Os','-ffreestanding','-fno-builtin','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-ffunction-sections','-fdata-sections','-c','serial_probe.c','-o','probe.o'],check=True)
subprocess.run(['ld.lld','-T','compact.ld','--gc-sections','-o','probe.elf','probe.o'],check=True)
subprocess.run(['llvm-objcopy','-O','binary','--only-section=.overlay','probe.elf','probe.bin'],check=True)
subprocess.run(['llvm-objcopy','-O','binary','--only-section=.tables','probe.elf','tables.bin'],check=True)
syms=subprocess.check_output(['readelf','-sW','probe.elf'],text=True)
def sym(name):return int(re.search(r'([0-9a-f]{8})\s+\d+\s+FUNC.*\b'+name+r'$',syms,re.M)[1],16)&~1
assert 'There are no relocations' in subprocess.check_output(['readelf','-rW','probe.elf'],text=True)
blob=Path('probe.bin').read_bytes();assert len(blob)<=END-CAVE;assert sym('voice_tick_source')==CAVE
table=Path('tables.bin').read_bytes();assert len(table)<=16384
ram=Path('fir_ram.bin').read_bytes();assert len(ram)<=64 and len(table)<=0x35c;ram=ram.ljust(64,b'\0')
out=bytearray(rom);patches=[(0x80650a4,table),(0x8065400,ram),(CAVE,blob),(IQ,branch(IQ,sym('voice_iq'))),(TICK,branch(TICK,sym('voice_tick_source'),True)),(SERIAL,branch(SERIAL,sym('serial_frame')))]
for a,v in patches:out[a-APP:a-APP+len(v)]=v
for a,d in [(IQ,sym('voice_iq')),(TICK,sym('voice_tick_source')),(SERIAL,sym('serial_frame'))]:
 b=out[a-APP:a-APP+4];assert unbranch(a,b[:3]+bytes([b[3]&0xbf]))==d
mask=bytearray(len(rom))
for a,v in patches:mask[a-APP:a-APP+len(v)]=b'\1'*len(v)
assert all(a==b or m for a,b,m in zip(rom,out,mask));enc=encode(out,raw);assert decode(enc)==out and len(enc)==len(raw)
name='RT950_R5_RadMod_R3B_SRAM16_STAGED_LIVE_G20_UART_UNTESTED.BTF';Path(name).write_bytes(enc)
Path('disassembly.txt').write_text(subprocess.check_output(['llvm-objdump','-d','--triple=thumbv7em-none-eabi','--mcpu=cortex-m4','probe.elf'],text=True))
manifest=dict(file=name,sha256=sha(enc),overlay_bytes=len(blob),state_bytes=152,ram_total_bytes=344,ram_code_bytes=64,ram_coeff_bytes=128,table_bytes=len(table),patches=[hex(a) for a,v in patches],hardware_tested=False);Path('manifest.json').write_text(json.dumps(manifest,indent=2));print(manifest)
