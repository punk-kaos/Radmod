from pathlib import Path
import struct, hashlib, subprocess, re, json
import btf
p=Path(__file__).resolve().parent
base=p/'RT950_R5_RadMod_R12B_LSB_R1_UNTESTED.BTF'
raw=base.read_bytes()
assert len(raw)==455680
assert __import__('os').environ.get('RADMOD_DEV')=='1' or hashlib.sha256(raw).hexdigest()=='016bee3c4c0cc75169a2ac0e4d57acd2385762839604a79eed5dcacb5456ca63'
plain=btf.decode(raw); out=bytearray(plain); changes=[]
def patch(a,old,new,description):
 i=a-btf.APP;assert len(old)==len(new) and out[i:i+len(old)]==old,hex(a)
 out[i:i+len(new)]=new;changes.append((a,len(new),description))
symbols={m[1]:int(m[0],16) for m in re.findall(r'\s+\d+: ([\da-f]+)\s+\d+\s+FUNC\s+GLOBAL\s+DEFAULT\s+\d+\s+(\w+)',subprocess.check_output(['readelf','-sW',str(p/'am.elf')],text=True))}
def jump(a,old,name,description):
 d=symbols[name]&~1;b=btf.branch(a,d);assert btf.unbranch(a,b)==d;patch(a,bytes.fromhex(old),b,description)
# Only AM-specific rejection is bypassed. The preceding 108-136 MHz and remaining stock eligibility checks remain unchanged.
patch(0x0800c0ae,bytes.fromhex('07d0'),bytes.fromhex('00bf'),'AM-only eligibility branch NOP')
jump(0x0801ed50,'51f0d6bb','reg30_transition','stop active AM before stock REG30 state transition; preserve caller LR')
jump(0x0801d93e,'fff731be','tx_complete','complete OEM RF-path GPIO setup before AM startup')
patch(0x080030b4,bytes.fromhex('bb320008'),struct.pack('<I',symbols['am_irq']|1),'TIM3 IRQ29 (previous default handler)')
blob=(p/'am.bin').read_bytes();assert len(blob)<=2512;patch(0x08061630,b'\xff'*len(blob),blob,'AM-only code and tables in verified all-FF cave')
enc=btf.encode(bytes(out),raw);assert len(enc)==len(raw) and btf.decode(enc)==out
allowed=set(i for a,n,d in changes for i in range(a-btf.APP,a-btf.APP+n));diff=[i for i,(a,b) in enumerate(zip(plain,out)) if a!=b];assert set(diff)<=allowed
# Preserve entire existing USB/LSB startup wrapper, SSB producer and CAT code byte-for-byte.
for a,b in [(0x08046a1c,0x08046a70),(0x08064fee,0x08065035),(0x08070444,0x080704ac),(0x08070500,0x0807052c),(0x0801ec84,0x0801ec88),(0x0801f2a8,0x0801f2ac),(0x0801f2fc,0x0801f300)]:assert plain[a-btf.APP:b-btf.APP]==out[a-btf.APP:b-btf.APP]
name='RT950_R5_RadMod_R12B_LSB_R1_AM_PWM16_R3_UNTESTED.BTF';(p/name).write_bytes(enc)
manifest={'base':base.name,'base_sha256':hashlib.sha256(raw).hexdigest(),'output':name,'output_sha256':hashlib.sha256(enc).hexdigest(),'bytes':len(enc),'payload_bytes':len(blob),'cave_capacity':2512,'decrypted_changed_bytes':len(diff),'patches':[{'addr':hex(a),'bytes':n,'purpose':d} for a,n,d in changes],'symbols':{k:hex(v) for k,v in symbols.items()},'hardware_tested':False}
(p/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))
