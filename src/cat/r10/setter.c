#include <stdint.h>
#ifdef HOST_TEST
extern unsigned char ram[];
extern void mock_call(unsigned);
extern unsigned mock_valid(unsigned,unsigned);
extern void mock_backing(unsigned,unsigned,unsigned);
#define U8(a) (*(volatile uint8_t *)(ram+(a)-0x20000000u))
#define U32(a) (*(volatile uint32_t *)(ram+(a)-0x20000000u))
#define CALL0(a) mock_call(a)
#define VALID(f,i) mock_valid(f,i)
#define BACKING(f,a,n) mock_backing(f,a,n)
#else
#define U8(a) (*(volatile uint8_t *)(a))
#define U32(a) (*(volatile uint32_t *)(a))
#define CALL0(a) ((void(*)(void))((a)|1u))()
#define VALID(f,i) ((unsigned(*)(unsigned,unsigned))0x0800cc7du)(f,i)
#define BACKING(f,a,n) ((void(*)(unsigned,unsigned,unsigned))0x08026045u)(f,a,n)
#endif
#define S 0x2000b054u
#define BASE 0x2000a468u
extern void ack(unsigned);
/* Main-loop only. No changes to RF IRQ handlers. */
void service(void){
 if(U32(S)!=0x43414152u || U8(S+4)!=5)return;
 unsigned i=U8(S+5),f=0,ok=0;
 if(U8(0x2000afc6u)||U8(0x2000a443u)||U8(0x2000a3fdu)==13)return;
 if(U8(0x2000a3fcu)||U8(0x2000a3fdu)||U8(0x2000a31cu)||U8(0x2000eac4u)||i>2||i!=U8(BASE+0xfa))goto out;
 unsigned v=BASE+0x110+0x58*i;
 /* Only normal frequency VFO, no offset/reverse, no band crossing in this bench build. */
 if(U8(v+0x20)||U8(v+0x28)||U8(v+0x30))goto out;
 for(unsigned j=0;j<4;j++){
    unsigned b=U8(S+8+j),h=b>>4,l=b&15;
    if(h>9||l>9)goto out;
    f=f*100+h*10+l;
 }
 unsigned old=U32(v);
 /* Restrict first tuning experiment to 2m and 70cm, within same band. */
 if(!((old>=14400000u&&old<=14800000u&&f>=14400000u&&f<=14800000u)||
      (old>=42000000u&&old<=45000000u&&f>=42000000u&&f<=45000000u)))goto out;
 /* OEM direct-entry validation also sets band selector. */
 if(!VALID(f,i))goto out;
 CALL0(0x0801e164u);
 U32(v)=f;
 CALL0(0x0800a9c0u);
 U8(BASE+0x2e2+36*i)=U8(BASE+0x10a);
 /* RAM backing representation only, skip OEM EEPROM-save tail. */
 BACKING(f,BASE+0x2d0+36*i,8);
 CALL0(0x0801f5a0u);
 CALL0(0x0800fdf4u);
 ok=U32(v)==f;
out:
 ack(ok?0:0xf0);
 U8(S+4)=0;
}
