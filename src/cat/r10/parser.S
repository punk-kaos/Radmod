.syntax unified
.cpu cortex-m4
.thumb
.section .text.parser,"ax",%progbits
.global parser
.thumb_func
parser:
    /* OEM CPS buffer tail, only while explicitly activated and OEM idle. */
    movw r1,#0xafc4
    movt r1,#0x2000
    ldrb r2,[r1,#2]
    cbnz r2,pass
    movw r2,#0xa3fc
    movt r2,#0x2000
    ldrb r3,[r2,#1]
    cmp r3,#13
    beq pass
    ldrb r3,[r2,#0x47]
    cbnz r3,pass
    adds r1,#0x90 /* 0x2000b054, 12 bytes inside 144-byte OEM ring */
    ldr r2,[r1]
    movw r3,#0x4152
    movt r3,#0x4341
    cmp r2,r3
    beq active
    cmp r0,#0x7e
    bne pass
    str r3,[r1]
    movs r2,#0
    str r2,[r1,#4]
    str r2,[r1,#8]
    b.w echo_r9
active:
    ldrb r2,[r1,#4]
    cmp r2,#5
    bhs done /* pending setter or corrupt state; don't overwrite */
    cmp r2,#4
    beq dispatch
    adds r3,r1,#8
    strb r0,[r3,r2]
    adds r2,#1
    strb r2,[r1,#4]
done:
    bx lr
dispatch:
    movs r2,#0
    strb r2,[r1,#4]
    cmp r0,#3
    beq query
    cmp r0,#0xff
    beq exitcat
#if SETTER
    cmp r0,#1
    bne error
    /* snapshot selected VFO; publish pending flag last */
    movw r2,#0xa562
    movt r2,#0x2000
    ldrb r2,[r2]
    strb r2,[r1,#5]
    movs r2,#5
    strb r2,[r1,#4]
    bx lr
#endif
error:
    movs r0,#0xf0
    b ack
exitcat:
    movs r2,#0
    str r2,[r1]
    movs r0,#0
    b ack
query:
    b.w query_r9
pass:
    b.w oem_rx
/* same PC10 and UART setup as working R9; r0 reply preserved in r12 */
.section .text.ack,"ax",%progbits
.global ack
.thumb_func
ack:
    mov r12,r0
    movw r1,#0x4c00
    movt r1,#0x4000
    ldr r2,[r1]
    tst r2,#0x80
    beq ack_done
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
    str r12,[r1,#4]
ack_done:
    bx lr
#if SETTER
.section .text.forehook,"ax",%progbits
.global forehook
.thumb_func
forehook:
    push {r4,lr}
    bl service
    pop {r4,lr}
    b.w oem_poll
#endif
