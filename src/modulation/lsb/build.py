from pathlib import Path
import struct,hashlib,subprocess
import btf
root=Path(__file__).resolve().parent
raw=next(root.glob('*R12_B*.BTF')).read_bytes()
assert __import__('os').environ.get('RADMOD_DEV')=='1' or hashlib.sha256(raw).hexdigest()=='433d0bbfee71f21d67d32239017f5a540ea79eb341ad1d6d073da7f08b77b495'
rom=bytearray(btf.decode(raw))
def patch(a,old,new):
 i=a-btf.APP
 assert len(old)==len(new) and rom[i:i+len(old)]==old,hex(a)
 rom[i:i+len(new)]=new
def blank(a,data):
 patch(a,b'\xff'*len(data),data)
def redirect(a,old,dst):
 patch(a,bytes.fromhex(old),btf.branch(a,dst))
def read(p,a,n):
 return p[a-btf.APP:a-btf.APP+n]
import json
for e in json.loads((root/'lsb_ui.json').read_text()):
 patch(int(e['address'],16),bytes.fromhex(e['before']),bytes.fromhex(e['after']))
blob=(root/'lsb.bin').read_bytes()
assert len(blob)<=0x8070500-0x8070444
blank(0x8070444,blob)
syms=subprocess.check_output(['readelf','-sW',str(root/'lsb.elf')],text=True).splitlines()
addr=lambda name:int(next(x.split()[1] for x in syms if x.split()[-1:]==[name]),16)&~1
patch(0x807101a,bytes.fromhex('06d1'),bytes.fromhex('06d3'))
redirect(0x807109e,'adf737ba',addr('freq'))
redirect(0x80716ac,'01eb8000',addr('phase'))
redirect(0x8070ef6,'02b0b0bd',addr('rx'))
out=btf.encode(bytes(rom),raw)
assert len(out)==len(raw) and btf.decode(out)==rom
(root/'RT950_R5_RadMod_R12B_LSB_R1_UNTESTED.BTF').write_bytes(out)
print(hashlib.sha256(out).hexdigest())
