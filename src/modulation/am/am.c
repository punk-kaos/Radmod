#include <stdint.h>
#include "mic_table.h"
#include "filter.h"
#define U(a) (*(volatile uint32_t*)(a))
#define B(a) (*(volatile uint8_t*)(a))
#define TIM 0x40000400u
#define ADC 0x40013c00u
#define APB1 0x4002101cu
#define APB2 0x40021018u
#define IRQ (1u<<29)
#define MAGIC 0x414d5033u
#define IRQSET 0xe000e100u
#define IRQCLR 0xe000e180u
#define IRQPENDCLR 0xe000e280u
#define GPIOOUT 0x4001180cu
#define GPIOIN 0x40011808u
#define PERIOD 7500u
#define LO 1440u
#define HI 6060u
#define RDBK0 0x0801f375u
#define RDBK1 0x0801ec8du
#define WRBK0 0x0801f441u
#define WRBK1 0x0801f495u
typedef uint32_t(*rd_t)(uint32_t);
typedef void(*wr_t)(uint32_t,uint32_t);
typedef struct {uint32_t magic,inv,cs,txword,sw,orig30,apb1,apb2,gpio,adc[5],timer[10],prio,nvic; uint16_t saved[64], extra[5]; uint16_t duty; uint32_t count,miss,late,fault,on,sample_due,periods,stage,irqs,edges,recover,start_reg30; int32_t raw,bias,peak,z[4][2];} State;
_Static_assert(sizeof(State)<=0x150,"AM state must fit reserved inactive phase workspace");
#define S ((volatile State*)0x20017b80u)
extern void fast_write(uint32_t,uint32_t,uint32_t);
static const uint8_t extra_regs[5]={0x36,0x47,0x48,0x7d,0x4b};
static const uint8_t tr[10]={0,4,8,12,24,32,36,40,44,52};
static const uint8_t ar[5]={4,8,0x10,0x2c,0x34};
static inline unsigned lock(void){unsigned x;__asm volatile("mrs %0,primask\ncpsid i":"=r"(x)::"memory");return x;}
static inline void unlock(unsigned x){__asm volatile("msr primask,%0"::"r"(x):"memory");}
static inline int active(void){return S->magic==MAGIC && S->inv==~MAGIC;}
static inline unsigned mode(void){uint32_t base=0x2000a468;unsigned i=B(base+250);return i<=2? B(base+88*i+328)&3:0;}
static inline int ptt(void){return (U(GPIOIN)&0x2cu)!=0x2cu;}
static inline int idle(void){return (U(GPIOOUT)&0x8100u)==0x8100u;}
static int edge(unsigned on){unsigned mask=lock();if(!idle()){unlock(mask);return 0;}if(S->on!=on){fast_write(0x30,S->txword^(on?0u:8u),S->cs);S->on=on;S->edges++;}unlock(mask);return 1;}
/* ADC read and software trigger always happen at the same PWM edge. */
static void capture(void){
 if(U(ADC)&2){S->raw=U(ADC+0x4c)&4095;S->sample_due=1;}
 else {S->miss++;S->sample_due=0;S->duty=3750;}
 U(ADC+8)|=1u<<22;
}
static void audio(void){
 int32_t raw=S->raw;S->sample_due=0;
 if(!S->count){S->bias=raw*256;S->peak=48*16;}
 int32_t x=(raw*256-S->bias)>>4;S->bias+=(raw*256-S->bias)>>8;
 for(unsigned i=0;i<4;i++){
  int32_t y=(int32_t)(((int64_t)sos[i][0]*x+S->z[i][0])>>13);
  if(y>32767)y=32767;if(y< -32768)y=-32768;
  S->z[i][0]=sos[i][1]*x-sos[i][3]*y+S->z[i][1];
  S->z[i][1]=sos[i][2]*x-sos[i][4]*y;x=y;
 }
 int32_t a=x<0?-x:x,p=S->peak;
 if(a>p)p=a;else if(p>48*16)p-=1+(p>>12);
 if(p<48*16)p=48*16;S->peak=p;
 int32_t w=3750+3000*x/p;if(w<(int)LO)w=LO;if(w>(int)HI)w=HI;
 S->duty=(uint16_t)w;S->count++;
}
/* Timer IRQ29: update ON; compare OFF; every second period reads ADC.
   DSP after the edge with the longer following interval. */
void am_irq(void){
 unsigned flags=U(TIM+0x10)&U(TIM+0xc)&3u;U(TIM+0x10)=~flags;
 if(!active()){U(TIM+0xc)=0;return;}
 S->irqs++;
 if(!ptt()||S->fault){S->fault=1;if(edge(0)){U(TIM+0xc)=0;U(TIM)=0;}return;}
 /* A blocked/merged edge invalidates this PWM period. Never generate a
    catch-up ON edge. Retry OFF on the next interrupt; restart only on
    the next clean update after successful mute. */
 if(flags==3u || S->recover){
  if(flags==3u)S->late++;
  S->sample_due=0;
  S->recover=!edge(0);
  return;
 }
 if(flags&1u){
  unsigned w=S->duty;U(TIM+0x34)=w;
  /* Skip a period if update delivery is too late for a safe ON interval. */
  if(U(TIM+0x24)>w-1140u || !edge(1)){S->late++;S->sample_due=0;S->recover=!edge(0);return;}
  if(!(S->periods++&1u)){capture();if(S->sample_due && w>=PERIOD/2)audio();}
 } else if(flags&2u){
  if(!edge(0)){S->late++;S->recover=1;S->sample_due=0;return;}
  if(S->sample_due)audio();
 }
}
void am_stop(void){
 if(!active())return;
 unsigned mask=lock();U(TIM+0xc)=0;U(TIM)=0;U(IRQCLR)=IRQ;U(IRQPENDCLR)=IRQ;U(TIM+0x10)=0;S->magic=0;S->inv=0;unlock(mask);
 /* OEM transition will restore TX BK after this; never re-enable its PA. */
 mask=lock();if(idle())fast_write(0x30,S->txword&~8u,S->cs);unlock(mask);
 wr_t w=(wr_t)S->sw;w(0x30,0);
 for(unsigned i=64;i>0;i--){unsigned r=nic_seq[i-1]>>16;uint16_t v=S->saved[i-1];if(r!=0&&r!=9&&r!=0x30&&v!=0xffff)w(r,v);}
 for(unsigned i=0;i<5;i++)w(extra_regs[i],S->extra[i]);w(0x30,S->orig30);
 U(ADC+8)=0;for(unsigned i=0;i<5;i++)if(i!=1)U(ADC+ar[i])=S->adc[i];U(ADC+8)=S->adc[1];U(0x40010800)=S->gpio;
 for(unsigned i=1;i<10;i++)U(TIM+tr[i])=S->timer[i];U(TIM+0x10)=0;U(TIM)=S->timer[0];B(0xe000e41d)=S->prio;
 if(S->nvic)U(IRQSET)=IRQ;
 if(!(S->apb1&2))U(APB1)&=~2u;
 /* Keep ADC/GPIO clocks enabled as in legacy audio cleanup. */
}
void am_start(void){
 if(mode()!=1||active())return;
 if(!ptt()){S->stage=10;return;}
 volatile uint32_t *p=(volatile uint32_t*)S;for(unsigned i=0;i<sizeof(State)/4;i++)p[i]=0;
 S->stage=1;
 uint32_t txw=U(0x20000c78),txr=U(0x20000c74);rd_t r;wr_t w;unsigned cs;
 if(txw==WRBK0&&txr==RDBK0){cs=0x100;r=(rd_t)RDBK1;w=(wr_t)WRBK1;}
 else if(txw==WRBK1&&txr==RDBK1){cs=0x8000;r=(rd_t)RDBK0;w=(wr_t)WRBK0;}else {S->stage=2;return;}
 unsigned orig=((rd_t)txr)(0x30)&65535u,sec=r(0x30)&65535u;S->start_reg30=orig|(sec<<16);
 /* The late physical TX hook runs after OEM state 2 and GPIO setup. Mute both RF and native mic
    using the stock writer, then read back before allocating any resources.
    On bad state/readback, fall back to RF-disabled REG30, never normal FM. */
 unsigned mask=lock();if(!idle()){unlock(mask);S->stage=3;return;}((wr_t)txw)(0x30,0xc1f2u);unlock(mask);
 unsigned muted=((rd_t)txr)(0x30)&65535u;
 if(muted!=0xc1f2u){((wr_t)txw)(0x30,0u);S->stage=4;return;}
 if(orig!=0xc1feu || !ptt() || sec==65535 || (sec&8)){S->stage=5;return;}
 /* TIM3 must be unused, no interrupt ownership stolen. */
 unsigned clk=U(APB1);U(APB1)=clk|2u;if((U(TIM)&1)||U(TIM+0xc)||(U(IRQSET)&IRQ)){if(!(clk&2))U(APB1)&=~2u;S->stage=6;return;}
 S->apb1=clk;S->cs=cs;S->txword=(orig|8u)&~4u;S->sw=(uint32_t)w;S->orig30=sec;S->on=0;S->duty=3750;
 for(unsigned i=0;i<5;i++){uint32_t v=r(extra_regs[i])&65535u;if(v==65535){if(!(clk&2))U(APB1)&=~2u;S->stage=7;return;}S->extra[i]=v;}
 for(unsigned i=0;i<64;i++)S->saved[i]=r(nic_seq[i]>>16)&65535u;
 /* The historical V143/V148 microphone path, independent of any FSK/REG70. */
 for(unsigned i=0;i<64;i++){uint32_t v=nic_seq[i];w(v>>16,v&65535u);}
 w(0x19,0x9041);w(0x4b,S->extra[4]|0x20u);w(0x47,0x6142);w(0x36,0);w(0x7d,0xe903);w(0x48,0xb3fb);w(0x30,0xc3f6);
 S->stage=8;S->apb2=U(APB2);U(APB2)|=(1u<<15)|(1u<<2);S->gpio=U(0x40010800);U(0x40010800)=S->gpio&~(15u<<8);
 for(unsigned i=0;i<5;i++)S->adc[i]=U(ADC+ar[i]);U(ADC+4)=0;U(ADC+0x10)=(S->adc[2]&~(7u<<6))|(7u<<6);U(ADC+0x2c)=0;U(ADC+0x34)=2;U(ADC+8)=0x001e0001;
 for(volatile unsigned i=0;i<200;i++)__asm volatile("nop");U(ADC+8)|=1u<<22;
 for(unsigned i=0;i<10;i++)S->timer[i]=U(TIM+tr[i]);S->prio=B(0xe000e41d);S->nvic=0;
 U(TIM)=0;U(TIM+4)=0;U(TIM+8)=0;U(TIM+0xc)=0;U(TIM+24)=0;U(TIM+32)=0;U(TIM+0x28)=0;U(TIM+0x2c)=PERIOD-1;U(TIM+0x34)=3750;U(TIM+0x24)=0;U(TIM+0x14)=1;U(TIM+0x24)=PERIOD-1;U(TIM+0x10)=0;
 B(0xe000e41d)=0x50;U(IRQPENDCLR)=IRQ;S->inv=~MAGIC;S->magic=MAGIC;S->stage=9;U(IRQSET)=IRQ;U(TIM+0xc)=3;U(TIM)=1;
}
