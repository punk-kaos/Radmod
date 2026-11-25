#include <stdint.h>
#define U8(a) (*(volatile uint8_t *)(uintptr_t)(a))
#define U32(a) (*(volatile uint32_t *)(uintptr_t)(a))
#define S 0x2000b054u
#define MAGIC 0x43414152u
#define BASE 0x2000a468u
extern void ack(unsigned);
extern void old_dispatch(unsigned,unsigned);
extern void old_service(void);
extern void native_ptt(void);
static inline unsigned tx(void){return !!(U32(0x4001100cu)&0x2000u);}
void dispatch(unsigned op,unsigned state){
 if(op==0xe7){unsigned s=U8(0x20000224); if(s>9)s=0; ack(s|(U8(0x2000a41a)?0:0x80));return;}
 if(op==0xf7){ack(tx()?0:0xff);return;}
#if PTT
 if(op==0x88){U8(S+7)=0;ack(0);return;}
 if(U8(S+7)||tx()){ack(0xf0);return;}
 if(op==8){U8(S+5)=U8(BASE+0xfa);U8(S+6)=8;U8(S+4)=5;return;}
#endif
 old_dispatch(op,state);
}
#if PTT
void service(void){
 if(U32(S)!=MAGIC||U8(S+4)!=5||U8(S+6)!=8){old_service();return;}
 unsigned i=U8(S+5),ok=0;
 if(i<=2&&i==U8(BASE+0xfa)&&!U8(0x2000a3fc)&&!U8(0x2000a3fd)&&!U8(0x2000a443)&&!U8(0x2000afc6)&&!U8(0x2000a31c)&&!U8(0x2000eac4)&&!tx()){
  unsigned v=BASE+0x110+0x58*i,f=U32(v);
  if(U8(v+0x38)==0&&!U8(v+0x20)&&!U8(v+0x28)&&!U8(v+0x30)&&((f>=14400000&&f<=14800000)||(f>=42000000&&f<=45000000))&&(U32(0x40011808)&0x4c)==0x4c&&(U8(0x080308cbu+U8(0x2000a925u))!=1||(U32(0x40011808)&0x20)))ok=1;
 }
 if(!ok){ack(0xf0);U8(S+4)=0;return;}
 /* Publish lease and free parser atomically; release can arrive during native TX. */
 unsigned mask; __asm volatile("mrs %0, primask\ncpsid i":"=r"(mask)::"memory");
 U8(S+7)=200;U8(S+4)=0;ack(0);
 __asm volatile("msr primask,%0"::"r"(mask):"memory");
 if(U32(S)==MAGIC&&U8(S+7))native_ptt();
 U8(S+7)=0;
}
unsigned ptt_input(unsigned port,unsigned pin){
 if(!(U32(port+8)&pin))return 0;
 return !(U32(S)==MAGIC&&U8(S+7));
}
#endif
