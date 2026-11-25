.syntax unified
.cpu cortex-m4
.thumb
.section .gate.text,"ax",%progbits
.balign 4
/* ADC3.DR has already been masked to raw 12-bit in r0.
 * Replay overwritten ORR.W r2,r2,#0x400000; resume original instruction.
 * Save eight registers for 8-byte ABI stack alignment into C.
 */
.global gate_adc_entry
.type gate_adc_entry,%function
.thumb_func
gate_adc_entry:
    push.w {r0-r5,r12,lr}
    bl gate_adc_push
    pop.w {r0-r5,r12,lr}
    orr.w r2,r2,#0x400000
    ldr.w pc,.Ladc_cont
    .balign 4
.Ladc_cont: .word 0x080621f1
.size gate_adc_entry, .-gate_adc_entry

/* The current audio-ring slot contains the conditioned signed input.
 * Manipulate *only* that slot, then execute complete unchanged Hilbert.
 */
.global gate_hilbert_entry
.type gate_hilbert_entry,%function
.thumb_func
gate_hilbert_entry:
    push.w {r0-r5,r12,lr}
    ldrsh.w r0,[r12,r1,lsl #1]
    bl gate_sample
    /* r1 and r12 are caller-saved under the ARM ABI; gate_sample uses r1.
     * Reload the ORIGINAL sample index/pointer before storing the result.
     * r0 must also reflect the gated sample on resume, matching Stage B.
     */
    ldr.w r1,[sp,#4]           /* saved original r1 */
    ldr.w r12,[sp,#24]         /* saved original r12 */
    strh.w r0,[r12,r1,lsl #1]  /* correct audio-ring slot */
    str.w r0,[sp,#0]           /* restore gated r0, not original audio */
    pop.w {r0-r5,r12,lr}
    b.w original_compact_hilbert
.size gate_hilbert_entry, .-gate_hilbert_entry

/* Start each TX with a closed gate; original voice_begin still runs. */
.global gate_voice_begin_entry
.type gate_voice_begin_entry,%function
.thumb_func
gate_voice_begin_entry:
    push.w {r0-r3,r12,lr}
    bl gate_start_reset
    pop.w {r0-r3,r12,lr}
    b.w original_voice_begin
.size gate_voice_begin_entry, .-gate_voice_begin_entry

/* Original R1 reporter, then telemetry editing before the UART sender. */
.global gate_report_entry
.type gate_report_entry,%function
.thumb_func
gate_report_entry:
    push {r4,lr}
    movw r4,#0x4d09
    movt r4,#0x0806
    blx r4
    bl gate_format_frame
    pop {r4,pc}
.size gate_report_entry, .-gate_report_entry
