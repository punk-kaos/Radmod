"""Exercise actual AM C control/filter logic with register and BK mocks (not ARM/analog emulation)."""
from pathlib import Path
import subprocess,tempfile
p=Path(__file__).resolve().parent
s=(p/'am.c').read_text()
s=s.replace('#define U(a) (*(volatile uint32_t*)(a))','#define U(a) (*mmio(a))').replace('#define B(a) (*(volatile uint8_t*)(a))','#define B(a) (*mmio8(a))').replace('#define S ((volatile State*)0x20017b80u)','static State state;\n#define S (&state)')
a=s.index('static inline unsigned lock('); b=s.index('static inline int active',a)
s=s[:a]+'static inline unsigned lock(void){return 0;}\nstatic inline void unlock(unsigned x){(void)x;}\n'+s[b:]
s=s.replace('((wr_t)txw)(0x30,','write_bk(txw,0x30,').replace('((rd_t)txr)(0x30)','read_bk(txr,0x30)').replace('sec=r(0x30)','sec=read_bk((uintptr_t)r,0x30)').replace('r(extra_regs[i])','read_bk((uintptr_t)r,extra_regs[i])').replace('r(nic_seq[i]>>16)','read_bk((uintptr_t)r,nic_seq[i]>>16)').replace('w(0x','write_bk((uintptr_t)w,0x').replace('w(r,v)','write_bk((uintptr_t)w,r,v)').replace('w(extra_regs[i],S->extra[i])','write_bk((uintptr_t)w,extra_regs[i],S->extra[i])').replace('w(v>>16,v&65535u)','write_bk((uintptr_t)w,v>>16,v&65535u)').replace('(uint32_t)w','(uint32_t)(uintptr_t)w')
pre='''#include <stdint.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <stddef.h>
static uint32_t ram[0x20000/4], periph[0x22000/4], nv[0x1000/4], bk[2][128];
static uint32_t fast_count, write_count, bad_mute;
static uint32_t *mmio(uint32_t a){if(a>=0x20000000&&a<0x20020000)return &ram[(a-0x20000000)/4];if(a>=0x40000000&&a<0x40022000)return &periph[(a-0x40000000)/4];if(a>=0xe000e000&&a<0xe000f000)return &nv[(a-0xe000e000)/4];assert(0);return 0;}
static uint8_t *mmio8(uint32_t a){return (uint8_t*)mmio(a&~3u)+(a&3u);}
static unsigned rchip(uintptr_t f){assert(f==0x0801f375u||f==0x0801ec8du);return f==0x0801ec8du;}
static unsigned wchip(uintptr_t f){assert(f==0x0801f441u||f==0x0801f495u);return f==0x0801f495u;}
static uint32_t read_bk(uintptr_t f,uint32_t r){assert(r<128);return bk[rchip(f)][r];}
static void write_bk(uintptr_t f,uint32_t r,uint32_t v){assert(r<128);if(!(bad_mute && r==0x30 && v==0xc1f2))bk[wchip(f)][r]=v;write_count++;}
void fast_write(uint32_t r,uint32_t v,uint32_t cs){assert(r==0x30);assert(cs==0x100||cs==0x8000);bk[cs==0x8000][r]=v;fast_count++;}
'''
post='''
static void reset(unsigned mod,unsigned band){memset(&state,0,sizeof state);memset(ram,0,sizeof ram);memset(periph,0,sizeof periph);memset(nv,0,sizeof nv);memset(bk,0,sizeof bk);fast_count=write_count=bad_mute=0;B(0x2000a468+328)=mod;U(0x20000c74)=band?RDBK1:RDBK0;U(0x20000c78)=band?WRBK1:WRBK0;U(GPIOOUT)=0x8100;U(GPIOIN)=0x28;bk[band][0x30]=0xc1fe;bk[!band][0x30]=0xc1f1;bk[!band][0x48]=0xb3b0;U(ADC+0x34)=7;U(0x40010800)=0x44444444;}
static void irq(unsigned f){U(TIM+0x24)=f==2?U(TIM+0x34):0;U(TIM+0x10)=f;am_irq();}
/* Model OEM REG30 state transitions with startup explicitly deferred to the
 * later physical TX GPIO tail. No OEM ARM instructions are executed. */
static void transition(unsigned b,unsigned st){
 static const uint16_t regs[]={0,0xbff1,0xc1fe,0x0302,0xc3fa};
 if(active()){am_stop();U(IRQSET)&=~IRQ;}bk[b][0x30]=regs[st];
}
int main(void){
 for(unsigned m=0;m<4;m++){if(m==1)continue;reset(m,0);am_start();am_stop();assert(!active()&&fast_count==0&&write_count==0);}
 puts("FM/USB/LSB no-op guard passed");
 for(unsigned b=0;b<2;b++){
  reset(1,b);transition(b,0);transition(b,1);assert(!active()&&bk[b][0x30]==0xbff1&&write_count==0);
  transition(b,2);assert(!active()&&bk[b][0x30]==0xc1fe&&!U(TIM+0xc));
  /* OEM completes its other register writes while PWM remains inactive. */
  U(GPIOOUT)=0x0100;assert(!active()&&!U(TIM+0xc));bk[b][0x50]=0x3b18;U(GPIOOUT)=0x8100;
  am_start();assert(active()&&S->stage==9&&S->start_reg30==0xc1f1c1feu&&bk[b][0x30]==0xc1f2&&U(TIM+0xc)==3&&U(TIM+0x24)==7499);
  am_start();assert(active()&&bk[b][0x30]==0xc1f2&&U(TIM+0xc)==3);
  U(GPIOIN)=0x2c;transition(b,0);transition(b,1);assert(!active()&&bk[b][0x30]==0xbff1&&!U(TIM+0xc));
  U(GPIOIN)=0x28;transition(b,2);am_start();assert(active());transition(b,0);assert(!active());
  printf("BK%u deferred start and repeated PTT sequence passed\\n",b);
 }
 reset(1,0);bad_mute=1;am_start();assert(!active()&&bk[0][0x30]==0&&!U(TIM+0xc)&&S->stage==4);puts("Failed mute readback forces REG30 zero");
 reset(1,0);bk[0][0x30]=0xbff1;am_start();assert(!active()&&bk[0][0x30]==0xc1f2&&S->stage==5);puts("Unexpected TX readback remains muted");
 reset(1,0);U(GPIOIN)=0x2c;am_start();assert(!active()&&bk[0][0x30]==0xc1fe&&write_count==0&&S->stage==10);puts("No physical PTT means no AM initialization");
 for(unsigned b=0;b<2;b++){
  reset(1,b);am_start();assert(active()&&S->cs==(b?0x8000:0x100));assert(bk[b][0x30]==0xc1f2&&bk[!b][0x30]==0xc3f6);assert(bk[!b][0x7d]==0xe903&&bk[!b][0x48]==0xb3fb&&U(ADC+0x34)==2);assert(U(TIM+0x2c)==7499&&U(TIM+0xc)==3);
  unsigned min=7500,max=0;double sum=0;
  for(unsigned i=0;i<16000;i++){U(ADC)=2;U(ADC+0x4c)=2048+(int)(45*sin(2*3.141592653589793*400*(i/2)/8000));irq(1);assert(!S->fault&&bk[b][0x30]==0xc1fa);unsigned d=U(TIM+0x34);assert(d>=1440&&d<=6060);if(i>1600){if(d<min)min=d;if(d>max)max=d;sum+=d;}irq(2);assert(bk[b][0x30]==0xc1f2);}
  assert(S->count==8000&&S->miss==0);assert(min<2500&&max>5000);printf("BK%u live 400Hz duty %u..%u, mean %.1f, %u audio samples\\n",b,min,max,sum/14399,S->count);
  irq(1);U(GPIOIN)=0x2c;irq(2);assert(bk[b][0x30]==0xc1f2&&!U(TIM+0xc));am_stop();assert(!active()&&bk[!b][0x30]==0xc1f1&&bk[!b][0x48]==0xb3b0&&U(ADC+0x34)==7&&U(0x40010800)==0x44444444);am_stop();
 }
 reset(1,0);U(TIM)=1;am_start();assert(!active()&&bk[0][0x30]==0xc1f2&&write_count==1);puts("Timer conflict fails muted");
 reset(1,0);am_start();irq(1);U(GPIOOUT)=0x0100;irq(2);assert(S->recover&&S->late==1&&!S->fault);U(GPIOOUT)=0x8100;irq(1);assert(bk[0][0x30]==0xc1f2&&U(TIM+0xc)==3&&!S->recover);irq(2);irq(1);assert(bk[0][0x30]==0xc1fa);irq(2);am_stop();puts("SPI contention at OFF edge: mute and recover without permanent shutdown");
 reset(1,0);am_start();U(GPIOOUT)=0x0100;irq(1);assert(S->recover&&S->late==1&&bk[0][0x30]==0xc1f2);irq(2);assert(S->recover);U(GPIOOUT)=0x8100;irq(1);assert(!S->recover&&bk[0][0x30]==0xc1f2);irq(2);irq(1);assert(bk[0][0x30]==0xc1fa);irq(2);am_stop();puts("SPI contention at ON edge: skipped pulses and recovered");
 reset(1,0);am_start();irq(1);irq(3);assert(!S->fault&&bk[0][0x30]==0xc1f2);irq(1);assert(bk[0][0x30]==0xc1fa);irq(2);am_stop();puts("Merged edge recovery passed");
 reset(1,0);am_start();U(TIM+0x24)=3600;U(TIM+0x10)=1;am_irq();assert(S->late==1&&bk[0][0x30]==0xc1f2);irq(2);irq(1);assert(bk[0][0x30]==0xc1fa);irq(2);am_stop();puts("Late ON interrupt skips unsafe pulse");
 printf("State size %zu; stage=%zu irqs=%zu edges=%zu recover=%zu count=%zu miss=%zu late=%zu fault=%zu start_reg30=%zu\\n",sizeof(State),offsetof(State,stage),offsetof(State,irqs),offsetof(State,edges),offsetof(State,recover),offsetof(State,count),offsetof(State,miss),offsetof(State,late),offsetof(State,fault),offsetof(State,start_reg30));return 0;
}
'''
with tempfile.TemporaryDirectory() as t:
 f=Path(t)/'test.c'; f.write_text(pre+s+post);exe=Path(t)/'test'
 subprocess.run(['cc','-std=gnu11','-O2','-Wno-int-to-pointer-cast','-I',str(p),str(f),'-lm','-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
