import re,struct,itertools,json,hashlib
from pathlib import Path
from btf import APP,decode
P=Path(__file__).parent;m=json.loads((P/'manifest.json').read_text());raw=(P/m['parent']).read_bytes();out=(P/m['output']).read_bytes();r=decode(raw);o=decode(out);assert hashlib.sha256(out).hexdigest()==m['sha256']
# Interpret the exact linked instruction listing; model the unchanged template-copy call.
code={}
for line in (P/'s10_gate_disasm.txt').read_text().splitlines():
 a=re.match(r'\s*([0-9a-f]+):\s+((?:[0-9a-f]{4}\s+)+)\s*([a-z][a-z0-9.]*)\s*(.*)',line)
 if a:
  addr=int(a[1],16);code[addr]=(len(a[2].split())*2,a[3],a[4].split('@')[0].strip())
base=0x80636f0;binary=(P/'generator.bin').read_bytes();template=list(struct.unpack_from('<49I',r,0x80638cc-APP))
def run(frame,cache,state,phase,chip,mode=2,vfo=0,mask=0,power=0):
 # Memory addresses stand for the actual aligned inputs, with template per chip.
 mem={};R={f'r{k}':0 for k in range(13)};R.update(r0=0x1000,r1=0x2000,r2=0x3000);z=c=False;it=[];pc=base;steps=0;writes=[];event=0
 def put(a,v,n=4):
  for j in range(n):mem[a+j]=(v>>(8*j))&255
 def get(a,n=4):
  if base<=a<base+len(binary):return int.from_bytes(binary[a-base:a-base+n],'little')
  return sum(mem.get(a+j,0)<<(8*j) for j in range(n))
 def val(s):return int(s[1:],0) if s.startswith('#') else R[s]
 def addr(s):
  a=re.match(r'\[(\w+)(?:,\s*(#[^\]]+))?\]',s);assert a,s
  return ((pc+4)&~3 if a[1]=='pc' else R[a[1]])+(val(a[2]) if a[2] else 0)
 for k,w in enumerate(frame):put(0x2000+4*k,w)
 put(0x1004,phase,1);put(0x1005,mask,1);put(0x1006,0x280,2);put(0x3000,cache,2);put(0x20017ccc,power);put(0x20017d10,state);put(0x2000a468+250,vfo,1);put(0x2000a468+88*vfo+328,mode,1)
 def cond(s):return {'eq':z,'ne':not z,'hs':c,'cs':c,'lo':not c,'cc':not c,'hi':c and not z}[s]
 while True:
  steps+=1;assert steps<200;size,op,args=code[pc];nxt=pc+size;arg=args.split(', ',1)
  if it and not it.pop(0):pc=nxt;continue
  if op in ('push.w','nop'):pass
  elif op=='pop.w':return R['r0'],[get(0x2000+4*k) for k in range(len(frame))],get(0x3000,2),get(0x20017d10),steps,writes
  elif op=='ite':it=[cond(args),not cond(args)]
  elif op.startswith('mov'):
   R[arg[0]]=val(arg[1])&0xffffffff
   if op=='movs':z=R[arg[0]]==0
  elif op.startswith('cmp'):
   a,b=map(val,arg);z=a==b;c=a>=b
  elif op in ('cbz','cbnz'):
   if (R[arg[0]]==0)==(op=='cbz'):nxt=int(arg[1].split()[0],16)
  elif op=='bl':
   assert int(args.split()[0],16)==0x806381c
   t=template.copy();t[0],t[-1]=((0x0d000000,0x04000100),(0x8c000000,0x04008000))[chip]
   for j,w in enumerate(t):put(R['r0']+4*j,w)
   # Model caller-saved clobbers, callee-saved preserved.
   for k in ['r0','r1','r2','r3','r12']:R[k]=0xdeadbeef
  elif op in ('b','beq','bne','bhi','bhs','blo'):
   if op=='b' or cond(op[1:]):nxt=int(args.split()[0],16)
  elif op.startswith('ldr'):
   n=1 if op.startswith('ldrb') else 2 if op.startswith('ldrh') else 4;R[arg[0]]=get(addr(arg[1]),n)
  elif op.startswith('str'):
   n=2 if op in ('strh','strh.w') else 4;a=addr(arg[1]);put(a,R[arg[0]],n);writes.append(a)
   if '], #' in arg[1]:R[re.match(r'\[(\w+)',arg[1])[1]]+=val(arg[1].split('], ')[1])
  elif op=='adds':
   R[arg[0]]=(R[arg[0]]+val(arg[1]))&0xffffffff;z=R[arg[0]]==0
  elif op in ('add.w','and','lsrs'):
   p=args.split(', ');x=val(p[1]);y=val(p[2]);
   if len(p)==4:y<<=int(p[3].split('#')[1],0)
   if op=='add.w':R[p[0]]=(x+y)&0xffffffff
   elif op=='and':R[p[0]]=x&y
   else:R[p[0]]=x>>y;c=bool((x>>(y-1))&1);z=R[p[0]]==0
  else:raise ValueError((hex(pc),op,args))
  pc=nxt

def transfer(frame,chip):
 cs=(0x100,0x8000)[chip];pins=0x8100;bits=[];commands=[]
 for w in frame:
  prev=pins;pins=(pins|(w&0xffff))&~(w>>16)
  if not(prev&0x400) and pins&0x400 and not(pins&cs):bits.append(int(bool(pins&0x800)))
  if not(prev&cs) and pins&cs:assert len(bits)==24;commands.append(int(''.join(map(str,bits)),2));bits=[]
  assert pins&(0x8100^cs)
 assert pins&0x8100==0x8100 and not pins&0x400 and not bits
 return commands
cases=0;maxnormal=0;maxedge=0
# Exact linked instruction-path cases for boundaries and each phase code, both chips/parities.
def ref(state,power,usb=True):
 if state==1024:
  return (0,0x30c1fa) if power>=600 and usb else (state,None)
 if power>=400:return 0,None
 if state==1023:return (1024,0x30c1f2) if usb else (state,None)
 return state+1,None
for chip,phase,parity in itertools.product(range(2),range(113),range(2)):
 h=[[0]*625 for _ in range(2)];cache=[0,0];state=0
 for k in range(2):
  ret,h[k],cache[k],state,steps,w=run(h[k],0,state,phase,chip,power=1000);assert ret==1 and state==0 and transfer(h[k],chip)==[0x700080|phase]
 for j,(power,initial) in enumerate([(399,0),(400,1),(399,1022),(399,1023),(0,1024),(599,1024),(600,1024),(1000,0),(0,0),(399,1023),(600,1024),(1000,0)]):
  k=(j+parity)&1;ret,h[k],cache[k],state,steps,w=run(h[k],cache[k],initial,phase,chip,power=power)
  exp,cmd=ref(initial,power);assert ret==1 and state==exp and transfer(h[k],chip)==[cmd if cmd is not None else 0x700080|phase],(chip,phase,j,state,exp,transfer(h[k],chip),cmd)
  assert all(0x2000<=a<0x2000+2500 or a in [0x3000,0x20017d10] for a in w)
  if cmd:maxedge=max(maxedge,steps)
  else:maxnormal=max(maxnormal,steps)
  cases+=1
 for vfo,mode in itertools.product(range(4),range(4)):
  k=0;ret,f,c_,state,steps,w=run(h[k],cache[k],1023,phase,chip,mode,vfo,power=0)
  assert transfer(f,chip)==[0x30c1f2 if vfo<=2 and mode>=2 else 0x700080|phase]
  cases+=1
 assert run(h[0],1,0,phase,chip,mask=1)[0]==0xffffffff
# End-to-end consecutive state updates, repeated pauses and both halves.
for chip,mode in itertools.product(range(2),(2,3)):
 h=[[0]*625 for _ in range(2)];cache=[0,0];state=0;events=[]
 for i,power in enumerate([1000]*2+[0]*1500+[700]*10+[450]*100+[0]*1024+[599]*300+[600]*20):
  k=i&1;old=state;ret,h[k],cache[k],state,steps,w=run(h[k],cache[k],state,77,chip,mode=mode,power=power)
  exp,cmd=ref(0 if i<2 else old,power);assert ret==1 and state==exp and transfer(h[k],chip)==[cmd if cmd else 0x7000cd]
  if cmd:events.append((i,cmd))
 assert events==[(1025,0x30c1f2),(1502,0x30c1fa),(2635,0x30c1f2),(2936,0x30c1fa)],events
print(f'PASS {cases} linked instruction-path/frame checks, plus four repeated 2956-sample state traces. Ordinary/restoration paths <= {maxnormal} instruction slots, switching path <= {maxedge} (IT-skipped slots counted, helper modeled). No MCU cycle accuracy.')
