.syntax unified
.thumb
.cpu cortex-m4
.section .text.hooks,"ax"
.global reg30_transition,tx_complete,fast_write
/* Entry tail branch preserves original LR for stock caller-sensitive wrapper. */
.thumb_func
reg30_transition:
 push {r0-r3,r12,lr}
 bl am_stop
 pop {r0-r3,r12,lr}
 b.w stock_reg30
/* Original 0x0801D93E tail call to OEM RF-path GPIO configuration.
 * Call it first, then AM startup, and return to original PTT caller.
 * Preserve the OEM return registers. Stack is aligned at both calls. */
.thumb_func
tx_complete:
 push {r4,lr}
 bl stock_tx_gpio
 push {r0-r3,r12,lr}
 bl am_start
 pop {r0-r3,r12,lr}
 pop {r4,pc}
.thumb_func
fast_write:
 push {r4-r7,lr}
 lsls r4,r0,#16
 orrs r4,r1
 ldr r5,=0x40011800
 mov.w r6,#0x400
 str r6,[r5,#0x14]
 str r2,[r5,#0x14]
 ldr r7,=0x00800000
 mov.w r0,#0x800
1:
 str r6,[r5,#0x14]
 tst r4,r7
 ite ne
 strne r0,[r5,#0x10]
 streq r0,[r5,#0x14]
 nop
 nop
 nop
 nop
 str r6,[r5,#0x10]
 nop
 nop
 nop
 lsrs r7,r7,#1
 bne 1b
 str r2,[r5,#0x10]
 pop {r4-r7,pc}
.ltorg
