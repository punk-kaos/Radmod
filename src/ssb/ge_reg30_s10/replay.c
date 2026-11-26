#include <stdint.h>
#include <stddef.h>
#include "tables.h"
#include "newtable.h"
typedef struct {uint32_t samples[16],pos,tick;int32_t area,prev;} State;
_Static_assert(sizeof(State)==80,"state size");
static int32_t sat(int32_t x){return x<-8192?-8192:x>8191?8191:x;}
static int32_t wrap(int32_t x){return (int16_t)x;}
static int32_t ab(int32_t x){return x<0?-x:x;}
unsigned track_step(State*s,int32_t x,int32_t y){
 int32_t a=ab(x),b=ab(y),m=a+b;int32_t ph=m?newangle[(49*b+m/2)/m]:0;
 if(x<0)ph=32768-ph;if(y<0)ph=-ph;
 int32_t err=wrap(ph-s->area+((s->prev*15204)>>15));int32_t gain=s->tick<220?32:s->tick>=2267?2079:32+(int32_t)s->tick-220;int32_t goal=((err*gain)>>11)-((s->prev*13442)>>15)+4096;
 uint32_t best=0x80000000u;unsigned code=0;
 for(unsigned k=0;k<78;k++){int32_t d=k==77?3576:steps[k],e=wrap(((d*19326)>>15)-goal),v=d-s->prev;uint32_t cost=(uint32_t)(e*e)+((uint32_t)(v*v)>>13);if(cost<best){best=cost;code=k;}}
 int32_t d=code==77?3576:steps[code];s->area=wrap(s->area+d-4096);s->prev=d+(((s->prev-d)*3797)>>15);return code;
}
unsigned ge_step(State*s,int32_t i,int32_t q){
 i=sat(i);q=sat(q);s->tick=(uint32_t)((int32_t)s->tick+((i*i+q*q-(int32_t)s->tick)>>5));unsigned p=s->pos&15;s->samples[p]=(uint16_t)i|((uint32_t)(uint16_t)q<<16);s->pos=(p+1)&15;
 int32_t x=0,y=0;for(unsigned k=0;k<16;k++){uint32_t v=s->samples[(p-k)&15];int32_t a=(int16_t)v,b=(int16_t)(v>>16);x+=a*cr[2*k]+b*cr[2*k+1];y+=a*ci[2*k]+b*ci[2*k+1];}
 return track_step(s,x>>8,y>>8);
}
void replay(const int32_t*x,uint8_t*y,size_t n){State s={0};for(size_t i=0;i<n;i++)y[i]=ge_step(&s,x[2*i],x[2*i+1]);}
