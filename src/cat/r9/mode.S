.syntax unified
.cpu cortex-m4
.thumb
.section .text.mode,"ax",%progbits
.balign 4
.global mode_reply
.thumb_func
mode_reply:
    /* r1 still points to UART4, TX buffer ready. Only replace the fifth byte. */
    movw r2,#0xa562
    movt r2,#0x2000
    ldrb r0,[r2]
    cmp r0,#2
    bhi unknown
    movs r3,#0x58
    mul r0,r0,r3
    adds r2,#0x4e
    ldrb r0,[r2,r0]
    ands r0,r0,#3
    lsls r0,r0,#2
    /* Candidate RadMod enum FM, AM, USB, LSB -> FT817 8,4,1,0. */
    movw r2,#0x0148
    lsrs r2,r2,r0
    ands r2,r2,#15
    b send
unknown:
    movs r2,#255
send:
    str r2,[r1,#4]
    bx lr
