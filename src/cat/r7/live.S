.syntax unified
.cpu cortex-m4
.thumb
.section .text.live,"ax",%progbits
.balign 4
.global live
.thumb_func
live:
    /* Replace only R6B's hardcoded BCD word. No writes to SRAM. */
    movw r2,#0xa562
    movt r2,#0x2000
    ldrb r0,[r2]
    cmp r0,#2
    bhi invalid
    movs r3,#0x58
    mul r0,r0,r3
    adds r2,#0x16
    ldr r0,[r2,r0]
    /* OEM frequency believed to be in 10 Hz units. */
    movw r2,#10000
    cmp r0,r2
    blo invalid
    movw r2,#0xe0ff
    movt r2,#0x05f5
    cmp r0,r2
    bhi invalid
    movs r2,#10
    movs r3,#8
    movs r12,#0
pack_digit:
    udiv r1,r0,r2
    mls r0,r1,r2,r0
    lsrs r12,r12,#4
    orr r12,r12,r0,lsl #28
    mov r0,r1
    subs r3,#1
    bne pack_digit
    rev r12,r12
    movw r1,#0x4c00
    movt r1,#0x4000
    b.w resume_reply
invalid:
    bx lr
