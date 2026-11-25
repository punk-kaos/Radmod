.syntax unified
.cpu cortex-m4
.thumb
.section .text.dispatch,"ax",%progbits
.global dispatch
.thumb_func
dispatch:
    /* R10 parser has completed frame; r0 opcode, r1 state, count=0. */
    cmp r0,#1
    beq queue
    cmp r0,#7
    beq queue
    cmp r0,#0x81
    bne bad
queue:
    strb r0,[r1,#6]
    b.w queue_r10
bad:
    b.w error_r10
