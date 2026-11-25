#include <stdint.h>
#include <stddef.h>
#include "compact_tables.h"
#ifndef DRIVE
#define DRIVE 20
#endif
#define TAPS 16u
#define PHASE_LIMIT 3292529 // about pi in Q20
#define MAGIC 0x4c495645u
/* 144 bytes, replaces the private 416-byte phase-kernel SRAM image only.
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
 int32_t re=0,im=0;
 unsigned j=0;
 for(unsigned k=p+1;k!=0;){uint32_t v=s->samples[--k];re=dot(re,v,coeff_re[j]);im=dot(im,v,coeff_im[j++]);}
 for(unsigned k=TAPS;j<TAPS;){uint32_t v=s->samples[--k];re=dot(re,v,coeff_re[j]);im=dot(im,v,coeff_im[j++]);}
 unsigned t=s->tick&63u;int64_t rot=(int64_t)(re>>12)*osc_cos[t]+(int64_t)(im>>12)*osc_sin[t];
 int32_t phase=(int32_t)(rot>>12)*DRIVE;
 int32_t goal=PILOT_Q20+phase-s->prev+s->err;
 unsigned a=0,b=112;while(b-a>1){unsigned m=(a+b)>>1;if(grid_q20[m]>goal)a=m;else b=m;}
 unsigned code=grid_q20[a]-goal<goal-grid_q20[b]?a:b;
 s->err=clip(goal-grid_q20[code],-PHASE_LIMIT,PHASE_LIMIT);s->prev=phase;s->pos=(p+1)&(TAPS-1);s->tick=t+1;
 return code;
}


unsigned compact_state_bytes(void){return sizeof(State);}
