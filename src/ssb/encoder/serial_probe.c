#include <stdint.h>
#include <stddef.h>
#include "compact_tables.h"
#ifndef DRIVE
#define DRIVE 20
#endif
#define TAPS 16u
#define PHASE_LIMIT 3292529 // about pi in Q20
#define MAGIC 0x4c495645u
/* 80 bytes, replaces the private 416-byte phase-kernel SRAM image only.
   R2T initializes that image at each TX start; the old phase entry is redirected. */
typedef struct { uint32_t samples[16]; uint32_t pos, tick; int32_t prev, err; } State;
_Static_assert(sizeof(State)==80,"state size");
static inline int32_t dot(int32_t a,uint32_t x,uint32_t y) {
#if defined(__arm__) || defined(__thumb__)
 __asm__("smlad %0,%1,%2,%0" : "+r"(a):"r"(x),"r"(y));return a;
#else
 return a+(int32_t)(int16_t)x*(int16_t)y+(int32_t)(int16_t)(x>>16)*(int16_t)(y>>16);
#endif
}
static inline int32_t clip(int32_t v,int32_t lo,int32_t hi){return v<lo?lo:(v>hi?hi:v);}
void compact_reset(State *s){for(unsigned j=0;j<TAPS;j++)s->samples[j]=0;s->pos=0;s->tick=0;s->prev=0;s->err=0;}
unsigned compact_step(State *s,int32_t i,int32_t q){
 i=clip(i,-8191,8191);q=clip(q,-8191,8191);
 unsigned p=s->pos&15u;s->samples[p]=(uint16_t)i|((uint32_t)(uint16_t)q<<16);
 /* Inner loop and all 32 packed coefficients reside in SRAM. */
 uint64_t pair=((uint64_t(*)(const uint32_t*,unsigned,const uint32_t*))0x20017b81u)(s->samples,p,(const uint32_t*)0x20017bc0u);
 int32_t re=(int32_t)(uint32_t)pair,im=(int32_t)(pair>>32);
 unsigned t=s->tick&63u;int64_t rot=(int64_t)(re>>12)*osc_cos[t]+(int64_t)(im>>12)*osc_sin[t];
 int32_t phase=(int32_t)(rot>>12)*DRIVE;
 int32_t goal=PILOT_Q20+phase-s->prev+s->err;
 unsigned a=0,b=112;while(b-a>1){unsigned m=(a+b)>>1;if(grid_q20[m]>goal)a=m;else b=m;}
 unsigned code=grid_q20[a]-goal<goal-grid_q20[b]?a:b;
 s->err=clip(goal-grid_q20[code],-PHASE_LIMIT,PHASE_LIMIT);s->prev=phase;s->pos=(p+1)&(TAPS-1);s->tick=t+1;
 return code;
}

#define U8(a) (*(volatile uint8_t *)(a))
#define U16(a) (*(volatile uint16_t *)(a))
#define U32(a) (*(volatile uint32_t *)(a))
#define FLAG U32(0x200177d4u)
#define SUPPLIED U8(0x200177e2u)
#define SERIAL_STATE U8(0x20017e06u)
#define UART_SR U32(0x40004c00u)
#define UART_DR U32(0x40004c04u)
#define UART_CR1 U32(0x40004c0cu)
#define NEW_MAGIC 0x4c495634u
#define ENC ((State*)0x20017c88u)
typedef struct {uint32_t ticks,entered,completed,fallback,frame,mincode,maxcode,encmax,tickmax,encmin,late,badpos,firsterr,firsttick;uint32_t spare[4];} Probe;
_Static_assert(sizeof(Probe)==72,"workspace");
#define S ((volatile Probe*)0x20017cd8u)
static inline void init(void){
 if(FLAG!=NEW_MAGIC){
  compact_reset(ENC);
  volatile uint32_t *p=(volatile uint32_t*)S;for(unsigned n=0;n<sizeof(Probe)/4;n++)p[n]=0;
  S->mincode=112;S->encmin=0xffffffffu;
  for(unsigned n=0;n<16;n++)U32(0x20017b80u+4*n)=U32(0x08065400u+4*n);
  for(unsigned n=0;n<16;n++){U32(0x20017bc0u+8*n)=coeff_re[n];U32(0x20017bc4u+8*n)=coeff_im[n];}
  __asm__ volatile("dsb sy\nisb sy":::"memory");FLAG=NEW_MAGIC;
 }
}
static inline void publish(unsigned c){U8(0x200177e1u)=(uint8_t)c;U32(0x200177e4u)++;if(c!=82)U32(0x200177e8u)++;SUPPLIED=1;}
/* Stage 0: proven R2X fixed output, no FIR. Stage 1: compute FIR but
   still publish the proven fixed output. Stage 2: publish the computed code.
   Delay measured in producer ticks, not wall-clock. */
static inline unsigned stage(void){uint32_t t=S->ticks;return t<4000u?0u:t<16000u?1u:2u;}
static unsigned hexline(volatile char *b,unsigned frame){
 uint32_t a[4];const char *keys;const char *prefix;
 switch(frame%7u){
 case 0:keys="TICF";prefix="ENC0";a[0]=S->ticks;a[1]=S->entered;a[2]=S->completed;a[3]=S->fallback;break;
 case 1:keys="LHPQ";prefix="ENC1";a[0]=S->mincode;a[1]=S->maxcode;a[2]=U8(0x200177e1u);a[3]=U32(0x200177f0u);break;
 case 2:keys="AKDR";prefix="ENC2";a[0]=U8(0x20016081u);a[1]=U32(0x20017f60u);a[2]=U32(0x4000100cu);a[3]=U32(0x40001000u);break;
 case 3:keys="ERDS";prefix="ENC3";a[0]=U32(0x2001604cu);a[1]=U32(0x20017e74u);a[2]=U32(0x2001600cu);a[3]=stage();break;
 case 4:keys="EPTC";prefix="ENC4";a[0]=S->encmax;a[1]=S->tickmax;a[2]=U32(0x20016070u);a[3]=U32(0xe0001000u);break;
 case 5:keys="MQLP";prefix="ENC5";a[0]=U32(0x20017e58u);a[1]=U32(0x20017e5cu);a[2]=U32(0x20017e60u);a[3]=ENC->pos;break;
 default:keys="MLBE";prefix="ENC6";a[0]=S->encmin;a[1]=S->late;a[2]=S->badpos;a[3]=U32(0x20016074u);break;
 }
 unsigned k=0;for(unsigned j=0;j<4;j++)b[k++]=prefix[j];for(unsigned j=0;j<4;j++){b[k++]=' ';b[k++]=keys[j];b[k++]='=';for(int n=28;n>=0;n-=4){unsigned v=(a[j]>>n)&15;b[k++]=(char)(v<10?'0'+v:'A'+v-10);}}b[k++]='\r';b[k++]='\n';return k;
}
__attribute__((used,section(".text.serial"))) void serial_frame(void){if(FLAG!=NEW_MAGIC)return;unsigned n=hexline((volatile char*)0x20017dc8u,S->frame++);U16(0x20017e00u)=0;U16(0x20017e04u)=(uint16_t)n;__asm__ volatile("dmb":::"memory");SERIAL_STATE=3;}

__attribute__((used,section(".text.entry"))) void voice_tick_source(void){uint32_t start=U32(0xe0001004u);init();S->ticks++;((void(*)(void))0x0805c829u)();if(!SUPPLIED){S->fallback++;publish(24);}uint32_t elapsed=U32(0xe0001004u)-start;if(elapsed>S->tickmax)S->tickmax=elapsed;}
__attribute__((used,section(".text.iq"))) void voice_iq(int32_t i,int32_t q){init();S->entered++;unsigned st=stage();if(!st){publish(24);return;}if(ENC->pos>=16u)S->badpos++;uint32_t start=U32(0xe0001004u);unsigned c=compact_step(ENC,i,q);uint32_t elapsed=U32(0xe0001004u)-start;if(elapsed>S->encmax)S->encmax=elapsed;if(elapsed<S->encmin)S->encmin=elapsed;if(elapsed>=15000u)S->late++;S->completed++;if(c<S->mincode)S->mincode=c;if(c>S->maxcode)S->maxcode=c;/* Keep emitted code within R2U measured playback range. */publish(st==1?24:(c>76?76:c));}
