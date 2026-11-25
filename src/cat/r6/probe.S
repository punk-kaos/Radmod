.syntax unified
.cpu cortex-m4
.thumb
.section .text.probe,"ax",%progbits
.balign 4
.global probe
.thumb_func
probe:
    /* Diagnostic only: zero padding is consumed, command 03 triggers reply.
       Keep original R4 ~ -> ! as a control. */
    cmp r0,#0
    beq ignore
    cmp r0,#0x7e
    beq echo
    cmp r0,#3
    bne pass
#if MULTI
    movs r12,#1
#else
    movs r12,#0
#endif
    b configure
echo:
    movs r12,#0
configure:
    /* Exact register setup from hardware-confirmed R4. */
    movw r1,#0x4c00
    movt r1,#0x4000
    ldr r2,[r1]
    tst r2,#0x80
    beq pass
    movw r3,#0x1004
    movt r3,#0x4001
    ldr r2,[r3]
    movs r0,#0xb
    bfi r2,r0,#8,#4
    str r2,[r3]
    ldr r2,[r1,#0xc]
    orr r2,r2,#0x2000
    orr r2,r2,#8
    str r2,[r1,#0xc]
    dsb sy
#if MULTI
    cmp r12,#0
    bne multi
#endif
    movs r2,#0x21
    str r2,[r1,#4]
ignore:
    bx lr
#if MULTI
multi:
    /* 144.200 MHz USB, synthetic known test vector; not actual VFO. */
    movw r12,#0x4214
    movs r3,#4
next:
    uxtb r2,r12
    str r2,[r1,#4]
    lsrs r12,r12,#8
    /* One finite wait per subsequent byte, no calls, no memory state. */
    movw r0,#4096
wait:
    ldr r2,[r1]
    tst r2,#0x80
    bne ready
    subs r0,#1
    bne wait
    bx lr
ready:
    subs r3,#1
    bne next
    movs r2,#1
    str r2,[r1,#4]
    bx lr
#endif
pass:
    /* R4 used r0 unchanged if TX not ready. */
    b.w oem_rx
