#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../src/rx.c"
static uint16_t rmap[128],orig[128];static unsigned writes,failreg=999;
static uint32_t rd(uint32_t r){return rmap[r];}
static void wr(uint32_t r,uint32_t v){writes++;if(r!=failreg)rmap[r]=v;}
int main(void){
 Snapshot s={0};AudioSaved a={0};
 for(unsigned j=0;j<128;j++)rmap[j]=(uint16_t)(0x1234+j);
 rmap[0x30]=0xbff1;rmap[0x47]=0x6142;rmap[0x48]=0xb14f;rmap[0x2b]=0x1007;rmap[0x2f]=0x98d8;rmap[0x7e]=0x302e;rmap[0x43]=0x3028;
 memcpy(orig,rmap,sizeof(orig));
 assert(install(&s,&a,rd,wr)==(1u<<N)-1);assert(rmap[0x47]==0x6142);assert(rmap[0x43]==0x2408);assert((rmap[0x2b]&7)==7);assert((rmap[0x2f]&0xff)==0xd8);
 assert(unmute_usb(&s,&a,rd,wr)==(1u<<21)-1);assert(rmap[0x47]==AF_TARGET&&rmap[0x48]==0xb3ff);
 assert(unmute_usb(&s,&a,rd,wr)==(1u<<21)-1);assert(s.result==(1u<<21)-1);restore(&s,&a,rd,wr);assert(!memcmp(orig,rmap,sizeof(orig)));assert(!has(&s));
 rmap[0x30]=0xc1fe;writes=0;assert(!install(&s,&a,rd,wr));assert(!unmute_usb(&s,&a,rd,wr));assert(writes==0);
 rmap[0x30]=0xbff1;failreg=0x42;uint32_t got=install(&s,&a,rd,wr);assert(got==((1u<<N)-1-(1u<<3)));assert(rmap[0x3d]==0);restore(&s,&a,rd,wr);failreg=999;assert(!memcmp(orig,rmap,sizeof(orig)));
 rmap[0x30]=0;rmap[0x3c]=0x4f80;rmap[0x3b]=0x5880;calibrate_idle(rd,wr);assert(rmap[0x3b]==0x5880+XTAL_STEPS);calibrate_idle(rd,wr);assert(rmap[0x3b]==0x5880+XTAL_STEPS);
 assert(clarify(14500000,2)==14500000+CLARIFIER_HZ/10);assert(clarify(14500000,0)==14500000);assert(clarify(14500000,1)==14500000);
 assert(resolve_mode(14500000,14500000,2,0,1)==2);assert(resolve_mode(14500000,44000000,2,0,1)==0);assert(resolve_mode(14500000,14500000,0,2,1)==0);assert(resolve_mode(14500000,14500000,0,2,0)==2);
 assert(route_value(1,0x6142,2,0xbff1)==AF_TARGET);assert(route_value(0,0x6042,2,0xbff1)==0x6042);assert(route_value(3,0x6342,2,0xbff1)==0x6342);assert(route_value(1,0x6142,2,0xc1fe)==0x6142);assert(route_value(1,0x6142,0,0xbff1)==0x6142);
 assert(sizeof(Snapshot)==40);assert(__builtin_offsetof(Snapshot,result)==36);
 puts("PASS: RX-only install, 19 register readbacks, unmute routing/gain, repeat, restoration, failed-write isolation, TX exclusion, crystal idempotence, clarifier mode isolation");
}
