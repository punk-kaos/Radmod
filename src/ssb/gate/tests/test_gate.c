/* Compile native to test the REAL gate.c state machine with mapped host state. */
#define HOST_SIM 1
#include "../src/gate.c"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static int32_t tick(int raw,int16_t processed){
    gate_adc_push((uint32_t)raw);
    return gate_sample(processed);
}

static void idle_sample(int index){
    static const int8_t noise[]={0,1,-1,0,0,1,0,-1,0,1,-1,1,0,0,0,-1};
    assert(tick(1229+noise[index&15],32)==0);
}
static void ensure_frame_shape(void){
    const char *str="V148 P=00000000 H=00000000 L=00000000 F=0\n";
    memset((void*)host_frame,0,sizeof(host_frame));
    memcpy((void*)host_frame,str,strlen(str));
}
int main(void){
    host_tx_active=1;
    gate_start_reset();
    for(int i=0;i<16000;i++)idle_sample(i);
    assert(S->mode==0 && S->gain==0 && S->opens==0 && S->closes==0);
    assert(S->samples==16000);
    assert(open_threshold(S)==5);
    assert(S->noise_q16 < (2u<<16));
    /* Speaking opens immediately; ramp is 4 ms. */
    for(int i=0;i<32;i++) {
        int32_t y=tick(1229+(i%8<4?18:-18),1000);
        assert(y>=0 && y<=1000);
    }
    assert(S->mode==2 && S->gain==256 && S->opens==1);
    for(int i=0;i<8000;i++)assert(tick(1229+(i&1?18:-18),1000)==1000);
    /* Sample-perfect passthrough in ordinary speech, including negative. */
    assert(tick(1229+18,-1127)==-1127);
    /* Silence after 120-ms hangover + 8-ms release; no stuck gate. */
    for(int i=0;i<960+100;i++) {
        static const int8_t noise[]={0,1,-1,0};
        tick(1229+noise[i&3],250);
    }
    assert(S->mode==0 && S->gain==0 && S->closes==1);
    for(int i=0;i<2000;i++)idle_sample(i);
    /* A weak but discernible signal above threshold must reopen. */
    for(int i=0;i<48;i++)tick(1229+(i&1?-6:6),-200);
    assert(S->mode==2 && S->gain==256 && S->opens==2);
    assert(tick(1229+6,-1111)==-1111);
    /* Format all three telemetry states without altering any stock TX path. */
    host_pre_norm_env_q8=256*19;host_adc_misses=0;
    ensure_frame_shape(); gate_format_frame();
    assert(memcmp((void*)host_frame,"GAT0",4)==0);
    ensure_frame_shape(); gate_format_frame();
    assert(memcmp((void*)host_frame,"ENV0",4)==0);
    assert(memcmp((void*)host_frame+7,"00001300",8)==0);
    ensure_frame_shape(); gate_format_frame();
    assert(memcmp((void*)host_frame,"RAW0",4)==0);
    /* On PTT release state must not leak to next transmit. */
    host_tx_active=0;gate_adc_push(1229);
    assert(S->magic==0);
    host_tx_active=1;gate_start_reset();
    for(int i=0;i<2000;i++)idle_sample(i);
    assert(S->mode==0 && S->gain==0 && S->opens==0);
    printf("PASS: 2s no-mic mute, 4ms onset, unmodified speech, 120+8ms closure, weak-speech reopen, telemetry, TX reset\n");
}
