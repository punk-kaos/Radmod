#include <stdint.h>
#ifndef XTAL_STEPS
#define XTAL_STEPS 2
#endif
#ifndef CLARIFIER_HZ
#define CLARIFIER_HZ 0
#endif
#ifndef RAW_PROFILE
#define RAW_PROFILE 0
#endif
#ifndef MUTE_TEST
#define MUTE_TEST 0
#endif
#define AF_TARGET (MUTE_TEST ? 0x6040u : 0x6540u)
_Static_assert(XTAL_STEPS>=-8 && XTAL_STEPS<=8,"xtal bounds");
_Static_assert(CLARIFIER_HZ>=-2000 && CLARIFIER_HZ<=2000 && CLARIFIER_HZ%10==0,"RIT bounds");
typedef uint32_t (*rd_t)(uint32_t);
typedef void (*wr_t)(uint32_t,uint32_t);
#ifdef HOST_TEST
#define EXT
#else
#define EXT __attribute__((section(".ext.text"),used,noinline))
#endif
/* Match F4HWN's normal BK4829 USB profile, plus fixed 3-kHz bandwidth,
   normal AGC, RX gate/compander off. Preserve TX-only register fields.
   Optional RAW experiment uses the same corrected hook positions. */
#define N 19u
static const uint8_t regs[N]={0x3d,0x73,0x31,0x42,0x2a,0x2b,0x2f,0x54,0x55,0x43,0x10,0x11,0x12,0x13,0x14,0x49,0x7b,0x7e,0x28};
static const uint16_t masks[N]={0xffff,0x0010,0x0009,0xffff,0xffff,0x0700,0x3f00,0xffff,0xffff,0x7e30,0xffff,0xffff,0xffff,0xffff,0xffff,0x3fff,0xffff,RAW_PROFILE?0xf007:0xf000,RAW_PROFILE?0x0f00:0x0100};
static const uint16_t values[N]={0,0x0010,0,0x6b5a,0x7400,RAW_PROFILE?0x0700:0,0x1800,0x9009,0x31a9,0x2400,0x007a,0x027b,0x037b,0x03be,0x0019,0x2a38,0x8420,0x3000,0};
/* Pack four small masked fields, freeing four bytes for persistent readback
   mask within the SAME screened 40-byte window used in R2L. */
typedef struct {uint16_t original[15];uint8_t small[4];uint16_t tag;uint32_t result;} Snapshot;
typedef struct {uint16_t af,gain;} AudioSaved;
_Static_assert(sizeof(Snapshot)==40,"snapshot size");
_Static_assert(sizeof(AudioSaved)==4,"audio snapshot size");
static int valid(uint32_t v){return v<0xffffu;}
static int isrx(uint32_t v){return valid(v)&&(v&0x00fbu)==0x00f1u;}
static int safe(uint32_t v){return valid(v)&&!(v&0x000au);}
static int small_index(unsigned j){return j==1?0:j==2?1:j==5?2:j==18?3:-1;}
static unsigned large_index(unsigned j){return j-(j>1)-(j>2)-(j>5)-(j>18);}
static unsigned shift_for(unsigned j){return j==1?4:j==2?0:8;}
static uint16_t saved(volatile Snapshot*s,unsigned j){int k=small_index(j);if(k<0)return s->original[large_index(j)];uint8_t v=s->small[k];return v==0xff?0xffff:(uint16_t)v<<shift_for(j);}
static void save(volatile Snapshot*s,unsigned j,uint16_t v){int k=small_index(j);if(k<0)s->original[large_index(j)]=v;else s->small[k]=v==0xffff?0xff:(uint8_t)((v&masks[j])>>shift_for(j));}
static uint16_t tag(volatile Snapshot*s){uint32_t h=0x6df3u;for(unsigned j=0;j<N;j++){h=((h<<5)|(h>>11))&0xffffu;h^=saved(s,j);}return (uint16_t)(0x8000u|(h&0x7fffu));}
static int has(volatile Snapshot*s){return s->tag!=0&&s->tag==tag(s);}
static uint32_t merge(uint32_t old,uint32_t mask,uint32_t val){return (old&~mask)|(val&mask);}
/* No global rollback merely because one readback is unavailable. Valid
   fields are applied independently. Restore only our still-present fields,
   not unrelated OEM changes. Reapplying retains the original snapshot. */
EXT uint32_t install(volatile Snapshot*s,volatile AudioSaved*a,rd_t r,wr_t w){
    if(!isrx(r(0x30)))return 0;
    if(!has(s)){
        s->tag=0; a->af=a->gain=0xffff;
        for(unsigned j=0;j<N;j++){uint32_t v=r(regs[j]);save(s,j,valid(v)?(uint16_t)v:0xffff);}
        s->tag=tag(s);
    }
    uint32_t applied=0;
    for(unsigned j=0;j<N;j++){
        if(saved(s,j)==0xffff)continue;
        uint32_t v=r(regs[j]);if(!valid(v))continue;
        uint32_t n=merge(v,masks[j],values[j]);if(n!=v)w(regs[j],n);
        uint32_t q=r(regs[j]);if(valid(q)&&(q&masks[j])==(values[j]&masks[j]))applied|=1u<<j;
    }
    s->result=applied;return applied;
}
EXT void restore(volatile Snapshot*s,volatile AudioSaved*a,rd_t r,wr_t w){
    if(!has(s)){s->tag=0;return;}
    if(!safe(r(0x30)))return;
    for(unsigned j=0;j<N;j++){
        if(saved(s,j)==0xffff)continue;
        uint32_t v=r(regs[j]);if(!valid(v))continue;
        if((v&masks[j])==(values[j]&masks[j])){uint32_t n=merge(v,masks[j],saved(s,j));if(v!=n)w(regs[j],n);}
    }
    /* OEM normal unmute writes AF/gain before our overlay; restore only
       when our exact value is still present, never undo a mute/beep. */
    if(a->af!=0xffff&&r(0x47)==AF_TARGET)w(0x47,a->af);
    if(a->gain!=0xffff){uint32_t g=r(0x48);if(valid(g)&&(g&0xfffu)==0x3ffu)w(0x48,merge(g,0xfff,a->gain));}
    s->tag=0;a->af=a->gain=0xffff;
}
/* RX activation establishes product-detector selection directly, not just
   on squelch opening. Intentional later OEM mute/beep requests remain OEM. */
EXT uint32_t select_usb(volatile Snapshot*s,volatile AudioSaved*a,rd_t r,wr_t w,uint32_t result,int gain){
    if(!isrx(r(0x30))||!has(s))return result;
    uint32_t af=r(0x47),g=r(0x48);
    if(valid(af)){
        if(af!=AF_TARGET){if(a->af==0xffff)a->af=(uint16_t)af;w(0x47,AF_TARGET);}
        if(r(0x47)==AF_TARGET)result|=1u<<19;
    }
    if(gain&&valid(g)){
        uint32_t next=merge(g,0xfffu,0x3ffu);
        if(next!=g){if(a->gain==0xffff)a->gain=(uint16_t)g;w(0x48,next);}
        if((r(0x48)&0xfffu)==0x3ffu)result|=1u<<20;
    }
    s->result=result;return result;
}
EXT uint32_t unmute_usb(volatile Snapshot*s,volatile AudioSaved*a,rd_t r,wr_t w){
    if(!isrx(r(0x30)))return 0;
    return select_usb(s,a,r,w,install(s,a,r,w),1);
}
/* Real OEM channel copy 0x2000a8a4 (58h bytes); OEM 0x800b5e8 copies
   selected record then 0x800b648 selects its active RX frequency pointer.
   Use the copied modulation if frequency agrees; otherwise use the same
   selected-VFO field the established FIX2 firmware uses. */
EXT unsigned resolve_mode(uint32_t f,uint32_t active_f,unsigned active_mode,unsigned ui_mode,int copy_valid){
    if(copy_valid && active_f>=100000u && active_f<=130000000u && (f==0 || (f>=active_f-200u && f<=active_f+200u)))return active_mode&3u;
    return ui_mode<=3?ui_mode:99;
}
EXT uint32_t route_value(uint32_t request,uint32_t original,unsigned mode,uint32_t link){
    return request==1u && mode==2u && isrx(link)?AF_TARGET:original;
}
EXT void calibrate_idle(rd_t r,wr_t w){
    if(XTAL_STEPS==0||r(0x30)!=0)return;
    uint32_t hi=r(0x3c),lo=r(0x3b);
    if(valid(hi)&&(hi&0xffc0u)==0x4f80u&&lo==0x5880u)w(0x3b,0x5880+XTAL_STEPS);
}
#ifdef HOST_TEST
const volatile int32_t clarifier_10hz=CLARIFIER_HZ/10;
#else
__attribute__((section(".ext.params"),used,aligned(4))) const volatile int32_t clarifier_10hz=CLARIFIER_HZ/10;
#endif
EXT uint32_t clarify(uint32_t f,unsigned mode){int32_t d=clarifier_10hz;if(mode!=2||f<100000u||f>130000000u||d< -200||d>200)return f;return (uint32_t)((int32_t)f+d);}
#ifndef HOST_TEST
/* Regions are above initial MSP (0x20015f78), outside FIX2 gate state
   0x20015fa0..0x20015fcf, and below established voice state 0x20016000.
   They are statically screened, not proven free dynamically. */
static volatile Snapshot* snap(unsigned i){return (volatile Snapshot*)(i?0x20015fd0u:0x20015f78u);}
static volatile AudioSaved* aud(unsigned i){return (volatile AudioSaved*)(0x20015ff8u+4u*i);}
static unsigned selected(void){const volatile uintptr_t*d=(const volatile uintptr_t*)0x20000c70u;uintptr_t r=d[1],w=d[2];if(r==0x0801f375u&&w==0x0801f441u)return 0;if(r==0x0801ec8du&&w==0x0801f495u)return 1;return 2;}
static rd_t reader(unsigned i){return (rd_t)(i==0?0x0801f375u:0x0801ec8du);}
static wr_t writer(unsigned i){return (wr_t)(i==0?0x0801f441u:0x0801f495u);}
static unsigned ui_modulation(void){const volatile uint8_t*v=(const volatile uint8_t*)0x2000a468u;unsigned i=v[0xfa];return i<=2?v[0x148+0x58*i]&3u:99;}
static unsigned modulation(uint32_t f){
    const volatile uint8_t *c=(const volatile uint8_t*)0x2000a8a4u;
    uintptr_t ptr=*(const volatile uintptr_t*)(c+0x18);
    int ok=ptr==0x2000a8a4u||ptr==0x2000a8b0u;
    uint32_t active_f=ok?*(const volatile uint32_t*)ptr:0;
    return resolve_mode(f,active_f,c[0x38],ui_modulation(),ok);
}
static uint32_t rx_frequency(void){return *(const volatile uint32_t*)0x20000c7cu;}
EXT uint32_t apply_clarifier(uint32_t f){return clarify(f,modulation(f));}
EXT void before_link(uint32_t mode,uint32_t caller){
    unsigned i=selected();if(i>1)return;
    if(mode==2||mode==3||mode==4||(mode==0&&caller==0x0801f2bdu)){
        for(unsigned k=0;k<2;k++)if(has(snap(k)))restore(snap(k),aud(k),reader(k),writer(k));
    }else if(mode==0||modulation(rx_frequency())!=2){if(has(snap(i)))restore(snap(i),aud(i),reader(i),writer(i));}
}
EXT void after_link(uint32_t mode){
    unsigned i=selected();if(i>1)return;rd_t r=reader(i);wr_t w=writer(i);
    if(mode==0){calibrate_idle(r,w);return;}
    if(mode==1&&modulation(rx_frequency())==2&&isrx(r(0x30))){
        uint32_t applied=install(snap(i),aud(i),r,w);
        (void)select_usb(snap(i),aud(i),r,w,applied,1);
    }
}
/* Exact OEM AF write is intercepted; preserve request 0/3/beep etc. */
EXT uint32_t intercept_af(uint32_t request,uint32_t original){
    unsigned i=selected();if(i>1||request!=1u)return original;
    return route_value(request,original,modulation(rx_frequency()),reader(i)(0x30));
}
EXT void audio_route(uint32_t request){
    if(request!=1u)return;unsigned i=selected();if(i>1)return;
    rd_t r=reader(i);wr_t w=writer(i);if(!isrx(r(0x30)))return;
    if(modulation(rx_frequency())!=2){if(has(snap(i)))restore(snap(i),aud(i),r,w);return;}
    (void)unmute_usb(snap(i),aud(i),r,w);
}
#endif
