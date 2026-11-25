#include <stdint.h>
/* R2D: two independent 8 kHz observation/modification hooks.
 * ADC3 hook observes the original 12-bit ADC conversion (untouched).
 * Sample hook applies the gate to the *current* Hilbert audio-ring sample.
 * No phase/IQ/depth/REG70 changes; at gain=256 samples are bit-exact R1.
 * State RAM 0x20015FA0..0x20015FCF (48-byte candidate gap above R1 initial MSP 0x20015F78, below 0x20016000 data).
 */
#ifdef HOST_SIM
static volatile uint8_t host_tx_active=0;
static volatile uint8_t host_frame[64];
static volatile uint32_t host_pre_norm_env_q8=0;
static volatile uint32_t host_adc_misses=0;
#define TX_ACTIVE host_tx_active
#define FRAME host_frame
#define PRE_NORM_ENV_Q8 host_pre_norm_env_q8
#define ADC_MISSES host_adc_misses
#else
#define TX_ACTIVE (*(volatile uint8_t *)(uintptr_t)0x20016081u)
#define FRAME ((volatile uint8_t *)(uintptr_t)0x20017DC8u)
#define PRE_NORM_ENV_Q8 (*(volatile uint32_t *)(uintptr_t)0x200177D0u)
#define ADC_MISSES (*(volatile uint32_t *)(uintptr_t)0x200177ECu)
#endif
#define MAGIC 0x52474732u  /* RGD2 */
#define HANGOVER_SAMPLES 960u  /* 120 ms, 8 kHz */
#define ATTACK_STEP 8u        /* 4 ms, 256 / 8 = 32 samples */
#define RELEASE_STEP 4u       /* 8 ms, 256 / 4 = 64 samples */

typedef struct {
    uint32_t magic;          // +0x00
    int32_t dc_q16;          // +0x04
    uint32_t noise_q16;      // +0x08, absolute deviation baseline during quiet
    uint32_t abs_ema_q16;    // +0x0c, raw absolute deviation low-pass
    uint32_t hangover;       // +0x10
    uint32_t gain;           // +0x14 Q8 0..256
    uint32_t mode;           // +0x18 0 mute, 1 attack, 2 open, 3 release
    uint32_t opens;          // +0x1c
    uint32_t closes;         // +0x20
    uint32_t raw_peak;       // +0x24 since last RAW0 telemetry
    uint32_t samples;        // +0x28
    uint32_t report_flip;    // +0x2c
} GateState;
_Static_assert(sizeof(GateState)==48,"GateState must fit precisely in known gap");
#ifdef HOST_SIM
static volatile GateState host_state;
#define S (&host_state)
#else
#define S ((volatile GateState *)(uintptr_t)0x20015FA0u)
#endif

static __attribute__((always_inline)) inline void init_gate(void) {
    volatile GateState *s=S;
    s->magic=0;  /* cleared at each TX start; first ADC sample initializes */
}

/* Room noise measured at 0.87–1.04 counts RMS; speech includes 3.36, 10.23,
 * 14.96 and 26.32 count RMS bursts. We deliberately cannot infer individual
 * weak consonants from these sparse 16-ms windows. This is a diagnostic,
 * with conservative adjustable 5..8-count instantaneous detection, NOT a
 * finished speech processor. The noise reference tracks only while muted.
 */
static __attribute__((always_inline)) inline uint32_t open_threshold(volatile GateState *s) {
    uint32_t v=(s->noise_q16*4u + 0x8000u)>>16;
    if(v<5) v=5;
    if(v>8) v=8;
    return v;
}
__attribute__((used,noinline,section(".gate.text")))
void gate_adc_push(uint32_t raw) {
    volatile GateState *s=S;
    if(!TX_ACTIVE) { s->magic=0; return; }
    raw &= 0xFFFu;
    if(s->magic!=MAGIC){
        s->dc_q16=(int32_t)(raw<<16);
        s->noise_q16=1u<<16;
        s->abs_ema_q16=0;
        s->hangover=0;
        s->gain=0;
        s->mode=0;
        s->opens=0;
        s->closes=0;
        s->raw_peak=0;
        s->samples=0;
        s->report_flip=0;
        s->magic=MAGIC;
    }
    /* Sub-code DC bias tracking (~0.5 s), no hardcoded 1229 bias. */
    int32_t dc=s->dc_q16;
    int32_t error=((int32_t)raw<<16)-dc;
    dc+=error>>12;
    s->dc_q16=dc;
    int32_t deviation=((int32_t)raw - (dc>>16));
    uint32_t absdev=(uint32_t)(deviation<0?-deviation:deviation);
    if(absdev>s->raw_peak) s->raw_peak=absdev;
    /* 32ms raw AC absolute envelope (decoupled from gated Hilbert). */
    int32_t av=(int32_t)s->abs_ema_q16;
    av+=(((int32_t)absdev<<16)-av)>>8;
    if(av<0) av=0;
    s->abs_ema_q16=(uint32_t)av;

    uint32_t th=open_threshold(s);
    if(absdev>=th){
        if(s->hangover==0 && s->gain==0) s->opens++;
        s->hangover=HANGOVER_SAMPLES;
    } else if(s->hangover) {
        s->hangover--;
    }
    /* Track noise slowly (0.5 s) ONLY with closed gate and no detected
     * activity, avoiding speech being learned into the silence floor. */
    if(s->gain==0 && s->hangover==0 && absdev<th){
        int32_t noise=(int32_t)s->noise_q16;
        noise+=(((int32_t)absdev<<16)-noise)>>12;
        if(noise<0) noise=0;
        s->noise_q16=(uint32_t)noise;
    }
    s->samples++;
}

__attribute__((used,noinline,section(".gate.text")))
int32_t gate_sample(int32_t input) {
    volatile GateState *s=S;
    if(s->magic!=MAGIC || !TX_ACTIVE) return input;
    uint32_t gain=s->gain;
    if(s->hangover) {
        if(gain<256u) {
            gain+=ATTACK_STEP;
            if(gain>=256u) gain=256u;
            s->mode=(gain==256u)?2u:1u;
        } else {s->mode=2u;}
    } else {
        if(gain>0) {
            gain=(gain>RELEASE_STEP)?gain-RELEASE_STEP:0;
            s->mode=gain?3u:0u;
            if(!gain) s->closes++;
        } else {s->mode=0u;}
    }
    s->gain=gain;
    if(gain==256u) return input; /* EXACT R1 value in ordinary speech */
    if(gain==0u) return 0;
    return (int32_t)((input*(int32_t)gain)>>8); /* bounded int16 input */
}

static __attribute__((always_inline)) inline void hex8(volatile uint8_t *dest,uint32_t v){
    for(int shift=28;shift>=0;shift-=4){
        uint32_t x=(v>>shift)&15u;
        *dest++=(uint8_t)(x<10u?'0'+x:'A'+(x-10u));
    }
}
__attribute__((used,noinline,section(".gate.text")))
void gate_format_frame(void){
    volatile GateState *s=S;
    volatile uint8_t *f=FRAME;
    if(!TX_ACTIVE || s->magic!=MAGIC) return;
    /* Original R1 report first; same inherited fixed-width UART frame. */
    if(f[4]!=' '||f[5]!='P'||f[6]!='='||f[16]!='H'||f[17]!='='||
       f[27]!='L'||f[28]!='='||f[40]!='0') return;
    uint32_t type=s->report_flip;
    s->report_flip=(type+1u)%3u;
    if(type==0u){
        f[0]='G';f[1]='A';f[2]='T';f[3]='0';
        hex8(f+7,s->mode);
        hex8(f+18,s->gain);
        hex8(f+29,((s->opens&65535u)<<16)|(s->closes&65535u));
    } else if(type==1u){
        f[0]='E';f[1]='N';f[2]='V';f[3]='0';
        hex8(f+7,PRE_NORM_ENV_Q8);
        hex8(f+18,s->abs_ema_q16);
        hex8(f+29,ADC_MISSES);
    } else {
        f[0]='R';f[1]='A';f[2]='W';f[3]='0';
        hex8(f+7,s->raw_peak);
        hex8(f+18,open_threshold(s));
        hex8(f+29,s->noise_q16);
        s->raw_peak=0;
    }
}

__attribute__((used,noinline,section(".gate.text")))
void gate_start_reset(void){init_gate();}
