from pathlib import Path
import ctypes as ct,numpy as np
from scipy import signal
from btf import APP,decode
import csv
P=Path(__file__).resolve().parent
lib=ct.CDLL(str(P/'replay_modes.so'));base=ct.CDLL(str(P/'replay.so'))
arg=[np.ctypeslib.ndpointer(np.int32,flags='C_CONTIGUOUS'),np.ctypeslib.ndpointer(np.uint8,flags='C_CONTIGUOUS'),ct.c_size_t];base.replay.argtypes=arg;lib.replay_mode.argtypes=arg+[ct.c_int]
f=np.load(P/'fixtures.npz');grid=f['grid'];rows=[]
def rf(c,mode):
 # Hardware S9 USB reference is nominally grid minus 500; LSB synth shift -500 further.
 x=grid[c]-(1000 if mode else 500);u=np.repeat(x,12);a=np.exp(-1/(96000*58e-6));y=signal.lfilter([1-a],[1,-a],u);return np.exp(2j*np.pi*np.cumsum(y)/96000)
def band(r):
 n=3840;hop=1920;w=np.hanning(n);v=np.lib.stride_tricks.sliding_window_view(r,n)[::hop];s=np.abs(np.fft.fft(v*w,axis=1))**2;freq=np.fft.fftfreq(n,1/96000);p=s.mean(axis=0);return p[(freq>=300)&(freq<2800)].sum(),p[(freq<=-300)&(freq>-2800)].sum(),p.sum()
for name,x in [(k,f[k]) for k in ['radio_mic_raw','voice_awb_raw']]+[('digital_silence',np.zeros((16000,2),dtype=np.int32))]:
 x=np.ascontiguousarray(x,dtype=np.int32);ref=np.zeros(len(x),np.uint8);base.replay(x,ref,len(x));cs=[]
 for mode in (0,1):
  c=np.zeros(len(x),np.uint8);lib.replay_mode(x,c,len(x),mode);cs.append(c)
  if mode==0:assert np.array_equal(c,ref)
  else:assert c.min()>=70 and c.max()<=111
  if name=='digital_silence':
   err=np.mean(grid[c[8000:]]-(1000 if mode else 500));print(name,mode,'mean Hz',err,'codes',np.unique(c[8000:]));assert abs(err)<2;continue
  a,b,t=band(rf(c,mode));wanted,other=(b,a) if mode else (a,b);row=dict(fixture=name,mode='LSB' if mode else 'USB',samples=len(x),min_code=int(c.min()),max_code=int(c.max()),wanted_pct=100*wanted/t,rejection_dB=10*np.log10(wanted/other));rows.append(row);print(row);assert wanted>other
with open(P/'simulation.csv','w') as h:w=csv.DictWriter(h,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
# Constant input test tones above the 600-unit activity threshold; measure peak RF offset.
with open(P/'tones.csv','w') as h:
 w=csv.writer(h);w.writerow(['input_Hz','mode','rf_peak_Hz','wanted_to_opposite_dB'])
 for tone in [400,1000,2000,2600]:
  t=np.arange(16000)/8000;x=np.ascontiguousarray(np.rint(100*np.column_stack([np.cos(2*np.pi*tone*t),np.sin(2*np.pi*tone*t)])),dtype=np.int32)
  for mode in (0,1):
   c=np.zeros(len(x),np.uint8);lib.replay_mode(x,c,len(x),mode);r=rf(c,mode)[96000:];sp=np.abs(np.fft.fft(r*np.hanning(len(r))))**2;freq=np.fft.fftfreq(len(r),1/96000);p=freq[np.argmax(sp)];a,b,_=band(r);rej=10*np.log10((b/a) if mode else (a/b));w.writerow([tone,'LSB' if mode else 'USB',p,rej]);print(tone,mode,p,rej);assert abs(p-(-tone if mode else tone))<=2
