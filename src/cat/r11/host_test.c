#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
_Alignas(4) unsigned char ram[0x20000];
#define HOST_TEST
#include "service.c"
static unsigned calls[16],nc,nack,reply,valid,delegated;
void service_r10(void){delegated++;U8(S+4)=0;}
void ack(unsigned a){nack++;reply=a;}
unsigned mock_valid(unsigned f,unsigned i){(void)f;(void)i;U8(BASE+0x10a)=2;U8(BASE+0x10d)=1;return valid;}
void mock_call(unsigned a,unsigned x,unsigned y,unsigned z){assert(nc<16);calls[nc++]=a;if(a==0x08024778){assert(x==0);U8(BASE+0xfa)=(U8(BASE+0xfa)+1)%3;}if(a==0x08026044){assert(z==8);for(int j=7;j>=0;j--){U8(y+j)=x%10;x/=10;}}}
static void init(unsigned i,unsigned op){memset(ram,0,sizeof ram);nc=nack=delegated=0;valid=1;U32(S)=0x43414152;U8(S+4)=5;U8(S+5)=i;U8(S+6)=op;U8(BASE+0xfa)=i;U32(BASE+0x110+0x58*i)=14420000;}
static void set_bcd(unsigned f){for(int j=3;j>=0;j--){unsigned d=f%100;f/=100;U8(S+8+j)=((d/10)<<4)|(d%10);}}
static void reject(void){service_new();assert(nack==1&&reply==0xf0&&nc==0&&U8(S+4)==0);}
int main(void){unsigned cat[]={0,1,4,8}, modes[]={3,2,1,0};for(unsigned i=0;i<3;i++){init(i,0x81);service_new();assert(reply==0&&nack==1&&U8(BASE+0xfa)==(i+1)%3&&nc==3&&calls[0]==0x08024778);for(unsigned j=0;j<4;j++){init(i,7);U8(S+8)=cat[j];U8(BASE+0x2e1+36*i)=0xb0;service_new();assert(reply==0&&nack==1&&nc==3&&U8(BASE+0x148+0x58*i)==modes[j]&&U8(BASE+0x2e1+36*i)==(0xb0|modes[j])&&U32(BASE+0x110+0x58*i)==14420000);}}
init(0,7);U8(S+8)=3;reject();init(0,0x81);U8(BASE+0x130+0x58)=1;reject();init(0,0x81);U8(BASE+0xfa)=2;reject();init(0,7);U8(0x2000a31c)=1;reject();init(0,7);U8(0x2000afc6)=1;service_new();assert(nack==0&&nc==0);init(0,1);set_bcd(43562550);service_new();
#if EXPANDED
assert(nack==1&&reply==0&&nc==5&&U32(BASE+0x110)==43562550);init(0,1);set_bcd(14420000);valid=0;U8(BASE+0x10a)=4;U8(BASE+0x10d)=0;reject();assert(U8(BASE+0x10a)==4&&U8(BASE+0x10d)==0);init(0,1);U8(S+8)=0xfa;reject();init(0,1);reject();
#else
assert(delegated==1&&nack==0&&nc==0);
#endif
puts("PASS: foreground dispatch, 3 VFOs, 4 modes, guards, frequency variant");}
