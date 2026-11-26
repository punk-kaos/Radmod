from pathlib import Path
import hashlib,struct,subprocess as sp,json,math
from btf import APP,decode,encode,branch,unbranch
P=Path(__file__).resolve().parent
BASE='RT950_R5_RadMod_GE_REG30_SILENCE_S9_ZERO_OFFSET_BENCH_UNTESTED.BTF'
OUT='RT950_R5_RadMod_GE_REG30_SILENCE_S10_USB_LSB_BENCH_UNTESTED.BTF'
sha=lambda x:hashlib.sha256(x).hexdigest()
b=(P/BASE).read_bytes();assert sha(b)=='a67083ef9a129b46c0966019003c0910c5700b1a155cc20b62e985ad1df1d745';r=decode(b);o=bytearray(r);patches=[]
def patch(a,v,old):
 i=a-APP;assert r[i:i+len(v)]==old,(hex(a),r[i:i+len(v)].hex(),old.hex());o[i:i+len(v)]=v;patches.append((a,len(v)))
def build(cmd):sp.run(cmd,cwd=P,check=True)
build(['clang','--target=arm-none-eabi','-mcpu=cortex-m4','-mthumb','-c','helpers.S','-o','helpers.o']);build(['ld.lld','-T','helpers.ld','-o','helpers.elf','helpers.o'])
assert 'There are no relocations' in sp.check_output(['readelf','-rW',str(P/'helpers.elf')],text=True)
for section in ('helpers','warm','cmp','freq'):
 build(['llvm-objcopy','-O','binary','--only-section=.'+section,'helpers.elf',section+'.bin'])
g=(P/'helpers.bin').read_bytes();assert len(g)<=160;patch(0x8070f60,g,b'\xff'*len(g))
# Virtual positive frequency = 1500 - physical deviation, so the original +500 Hz virtual reference
# maps to physical +1000 Hz. Relative synthesizer shift versus USB is -500 Hz.
cal=struct.unpack_from('<113i',r,0x80651a4-APP)
# virtual step Q16 turns/sample. 1500 Hz -> 12288 turns units at 8kHz.
steps=[round(12288-cal[k]/(2**20*2*math.pi)*65536) for k in range(111,69,-1)]
assert len(steps)==42 and min(steps)>0 and max(steps)<32768
patch(0x80704ac,struct.pack('<42H',*steps),b'\xff'*84)
(P/'lsbtable.h').write_text('static const uint16_t lsbsteps[42]={'+','.join(map(str,steps))+'};\n')
# Original LSB freq handler retains mode check and calibrated BK trim, replace 625 ten-Hz units with 50.
patch(0x807044e,(P/'freq.bin').read_bytes(),bytes.fromhex('a0f27120'))
# Gate mode compare was USB==2; masked VFO mode >=2 includes USB and LSB only.
patch(0x80637a8,bytes.fromhex('0bd3'),bytes.fromhex('0bd1'))
# Shared tracker keeps all state math; select table and length, map physical index only after updating virtual state.
patch(0x80716cc,branch(0x80716cc,0x8070f60),bytes.fromhex('174c0025'))
patch(0x80716fa,(P/'cmp.bin').read_bytes(),bytes.fromhex('4e2d'))
patch(0x807171e,branch(0x807171e,0x8070f7c),bytes.fromhex('bde80007'))
# Preserve USB fallback code 0, LSB fallback selects the negative extreme 111. The shared cap now accepts 112.
patch(0x8071252,branch(0x8071252,0x8070f9c),bytes.fromhex('00206073'))
patch(0x807133c,branch(0x807133c,0x8070f8c),bytes.fromhex('002034e0'))
patch(0x807139c,bytes.fromhex('7028'),bytes.fromhex('4d28'))
patch(0x80713a0,bytes.fromhex('7020'),bytes.fromhex('4d20'))
patch(0x80713a2,(P/'warm.bin').read_bytes(),bytes.fromhex('b9f5807f38bf0020'))
allowed={i for a,n in patches for i in range(a-APP,a-APP+n)}
assert all(x==y or i in allowed for i,(x,y) in enumerate(zip(r,o)))
assert o[0x80651a4-APP:0x8065440-APP]==r[0x80651a4-APP:0x8065440-APP] # calibration and FIR
enc=encode(bytes(o),b);assert len(enc)==len(b)==455680 and decode(enc)==o
(P/OUT).write_bytes(enc)
(P/'manifest.json').write_text(json.dumps(dict(parent=BASE,parent_sha256=sha(b),output=OUT,sha256=sha(enc),size=len(enc),changed=sum(x!=y for x,y in zip(r,o)),patches=[dict(address=hex(a),size=n) for a,n in patches],lsb_candidates=42,lsb_physical_codes=[111,70],lsb_synth_delta_hz=-500,hardware_tested=False,cycle_timing_verified=False),indent=2)+'\n')
print((P/'manifest.json').read_text())
