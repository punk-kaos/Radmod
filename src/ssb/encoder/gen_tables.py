from pathlib import Path
import numpy as np,re
D=Path(__file__).parent
s=(D/'rt_tables.h').read_text();H=np.array([complex(float(a),float(b)) for a,b in re.findall(r'\{([\d.eE+\-]+)f,([\d.eE+\-]+)f\}',s.split('static const Cpx twiddle')[0])]);assert len(H)==256
omega=2*np.pi*3125/8000;N=16;d=N//2;k=np.arange(-d,d);h=np.fft.ifft(H);coef=h[k%256]*np.exp(1j*omega*k);coef=np.rint(coef.real*32768)+1j*np.rint(coef.imag*32768)
# Pack coefficients for real and imaginary complex dot products.
def packed(a,b):return (int(a)&65535)|((int(b)&65535)<<16)
def arr(name,vals,typ='uint32_t'):
 return 'static const __attribute__((section(".encoder_tables"))) '+typ+' '+name+'['+str(len(vals))+']={'+','.join(str(int(x)) for x in vals)+'};\n'
grid=np.array([float(x) for x in re.findall(r'([\d.eE+\-]+)f',s.split('static const float grid[113]={')[1].split('};')[0])]);assert len(grid)==113 and np.all(np.diff(grid)<=0)
# Every input halfword is clamped before accumulation. Bounds exclude int32 overflow.
bound=8191*int(np.sum(abs(coef.real)+abs(coef.imag)));assert bound<2**31
osc=np.exp(-1j*omega*(np.arange(64)-d))
# Re(y*osc) = yr*cos + yi*sin(omega*(n-delay)).
text=arr('coeff_re',[packed(a,-b) for a,b in zip(coef.real,coef.imag)])+arr('coeff_im',[packed(b,a) for a,b in zip(coef.real,coef.imag)])+arr('osc_cos',np.rint(32767*osc.real),'int16_t')+arr('osc_sin',np.rint(-32767*osc.imag),'int16_t')+arr('grid_q20',np.rint(grid*2**20),'int32_t')+f'#define PILOT_Q20 {round(omega*2**20)}\n#define ACC_BOUND {bound}\n'
(D/'compact_tables.h').write_text(text);print('16-tap kernel energy',np.sum(abs(h[k%256])**2)/np.sum(abs(h)**2),'maximum accumulator',bound)
