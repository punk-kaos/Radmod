#include <stdint.h>
#ifdef HOST_TEST
extern unsigned char ram[];
extern void mock_call(unsigned,unsigned,unsigned,unsigned);
extern unsigned mock_valid(unsigned,unsigned);
#define U8(a) (*(volatile uint8_t *)(ram+(a)-0x20000000u))
#define U16(a) (*(volatile uint16_t *)(ram+(a)-0x20000000u))
#define U32(a) (*(volatile uint32_t *)(ram+(a)-0x20000000u))
#define CALL0(a) mock_call(a,0,0,0)
#define CALL1(a,x) mock_call(a,x,0,0)
#define CALL3(a,x,y,z) mock_call(a,x,y,z)
#define VALID(f,i) mock_valid(f,i)
#else
#define U8(a) (*(volatile uint8_t *)(a))
#define U16(a) (*(volatile uint16_t *)(a))
#define U32(a) (*(volatile uint32_t *)(a))
#define CALL0(a) ((void(*)(void))((a)|1u))()
#define CALL1(a,x) ((void(*)(unsigned))((a)|1u))(x)
#define CALL3(a,x,y,z) ((void(*)(unsigned,unsigned,unsigned))((a)|1u))(x,y,z)
#define VALID(f,i) ((unsigned(*)(unsigned,unsigned))0x0800cc7du)(f,i)
#endif
#define S 0x2000b054u
#define BASE 0x2000a468u
extern void ack(unsigned);
extern void service_r10(void);
static unsigned plain(unsigned i){unsigned v=BASE+0x110+0x58*i;return !(U8(v+0x20)||U8(v+0x28)||U8(v+0x30));}
void service_new(void){
 if(U32(S)!=0x43414152u || U8(S+4)!=5)return;
 unsigned op=U8(S+6),i=U8(S+5),ok=0;
#if !EXPANDED
 if(op==1){service_r10();return;}
#endif
 if(U8(0x2000afc6u)||U8(0x2000a443u)||U8(0x2000a3fdu)==13)return;
 if(U8(0x2000a3fcu)||U8(0x2000a3fdu)||U8(0x2000a31cu)||U8(0x2000eac4u)||i>2||i!=U8(BASE+0xfa)||!plain(i))goto out;
 unsigned v=BASE+0x110+0x58*i, b=BASE+0x2d0+36*i;
 if(op==0x81){
   unsigned next=i==2?0:i+1;
   if(!plain(next))goto out;
   /* OEM VFO key routine, arg 0 skips explicit save. Native A/B/C cycle. */
   CALL1(0x08024778u,0);
   CALL0(0x0801df34u);
   CALL0(0x0800fdf4u);
   ok=U8(BASE+0xfa)==next;
 }else if(op==7){
   unsigned m=U8(S+8),mode;
   switch(m){case 0:mode=3;break;case 1:mode=2;break;case 4:mode=1;break;case 8:mode=0;break;default:goto out;}
   /* Same backing bits as OEM modulation menu; update selected live record,
      refresh OEM active working copy and normal RF/display path. Avoid full
      menu reload/save and confirmation UI. */
   U8(b+0x11)=(U8(b+0x11)&0xfcu)|mode;
   U8(v+0x38)=mode;
   CALL0(0x0800b5e8u);
   CALL0(0x0801f5a0u);
   CALL0(0x0800fdf4u);
   ok=(U8(v+0x38)&3)==mode;
 }
#if EXPANDED
 else if(op==1){
   unsigned f=0;
   for(unsigned j=0;j<4;j++){unsigned x=U8(S+8+j),h=x>>4,l=x&15;if(h>9||l>9)goto out;f=f*100+h*10+l;}
   if(!f)goto out;
   /* OEM validation may change band globals even on rejection. */
   unsigned band=U8(BASE+0x10a),chain=U8(BASE+0x10d);
   if(!VALID(f,i)){U8(BASE+0x10a)=band;U8(BASE+0x10d)=chain;goto out;}
   CALL0(0x0801e164u);U32(v)=f;CALL0(0x0800a9c0u);
   U8(b+0x12)=U8(BASE+0x10a);
   CALL3(0x08026044u,f,b,8);
   CALL0(0x0801f5a0u);CALL0(0x0800fdf4u);
   ok=U32(v)==f;
 }
#endif
out:
 ack(ok?0:0xf0);U8(S+4)=0;
}
