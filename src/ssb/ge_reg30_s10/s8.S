.syntax unified
.thumb
.cpu cortex-m4
.section .generator,"ax",%progbits
.global generator
.thumb_func
generator:
 push {r4,r5,r6,r7,r8,lr}
 mov r5,r0
 mov r6,r1
 mov r7,r2
 cbz r0,fail_near
 cbz r1,fail_near
 cbz r2,fail_near
 ldrh r0,[r5,#6]
 cmp.w r0,#0x280
 bne fail_near
 ldrb r0,[r5,#4]
 cmp r0,#112
 bhi fail_near
 ldrb r1,[r5,#5]
 cbnz r1,fail_near /* bench zero-mask path only */
 ldrh.w r8,[r7]
 cmp.w r8,#1
 beq regular
 cmp.w r8,#0
 bne restore
 ldr r4,=0x20017ccc
 movs r1,#0
 str r1,[r4,#68]
 add.w r0,r6,#12
 bl copy_template
restore:
 /* reset address and upper data to native REG70 format; low seven bits set below */
 ldr r4,=0x04000800
 mov.w r3,#0x0c000000
 str r4,[r6,#0x14]
 str r3,[r6,#0x4c]
 str r3,[r6,#0x54]
 str.w r3,[r6,#0x84]
 movs r1,#1
 strh r1,[r7]
 b regular
fail_near:
 mov.w r0,#-1
 pop {r4,r5,r6,r7,r8,pc}
regular:
 ldr r4,=0x04000800
 mov.w r3,#0x0c000000
 ldrb r0,[r5,#4]
 /* Encoder raw I/Q power EMA and former spare[0] (gate state). */
 ldr r5,=0x20017ccc
 ldr r2,[r5]
 ldr r1,[r5,#68]
 cmp.w r1,#1024
 beq muted
 cmp.w r2,#400
 bhs clear_count
 adds r1,#1
 cmp.w r1,#1024
 beq edge
 str r1,[r5,#68]
 b emit
clear_count:
 cbz r1,emit
 movs r1,#0
 str r1,[r5,#68]
 b emit
muted:
 cmp.w r2,#600
 blo emit
 movs r1,#0
edge:
 /* Limit PA writes to USB; no mode check on ordinary samples. */
 ldr r2,=0x2000a468
 ldrb.w r12,[r2,#250]
 cmp.w r12,#2
 bhi emit
 add.w r2,r2,r12,lsl #6
 add.w r2,r2,r12,lsl #4
 add.w r2,r2,r12,lsl #3
 ldrb.w r12,[r2,#328]
 and.w r12,r12,#3
 cmp.w r12,#2
 blo emit
 /* swap register address / high data in primary slot, no second transaction */
 str r3,[r6,#0x14]
 str r4,[r6,#0x4c]
 str r4,[r6,#0x54]
 str.w r4,[r6,#0x84]
 movs r2,#2
 strh r2,[r7] /* next use of THIS half restores REG70 header */
 str r1,[r5,#68]
 cmp r1,#0
 ite eq
 moveq r0,#0x7a /* PA on */
 movne r0,#0x72 /* PA off */
emit:
 add.w r2,r6,#0x84
 .set bitoff,64
 .rept 7
 lsrs r0,r0,#1
 ite cs
 strcs r4,[r2,#bitoff]
 strcc r3,[r2,#bitoff]
 .set bitoff,bitoff-8
 .endr
 movs r0,#1
 pop {r4,r5,r6,r7,r8,pc}
 .balign 4
 .ltorg
