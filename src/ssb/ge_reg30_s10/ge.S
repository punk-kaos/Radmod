.syntax unified
.thumb
.section .encoder,"ax",%progbits
.global ge
.thumb_func
ge:
 push {r4-r7,lr}
 push.w {r8-r10}
 mov r7,r0
 ssat r1,#14,r1
 ssat r2,#14,r2
 ldr r4,[r7,#64]
 and r4,r4,#15
 pkhbt r1,r1,r2,lsl #16
 /* raw I/Q power EMA in formerly unused tick word. */
 smuad r5,r1,r1
 ldr r6,[r7,#68]
 subs r5,r5,r6
 add.w r6,r6,r5,asr #5
 str r6,[r7,#68]
 subs r6,#220
 usat r10,#11,r6
 add.w r10,r10,#32
 str r1,[r7,r4,lsl #2]
 mov r1,r4
 adds r4,#1
 and r4,r4,#15
 str r4,[r7,#64]
 ldr r3,=0x20017b81
 adds r2,r3,#63
 blx r3
 /* atan2 in signed Q16 turns; shift FIR accumulators first to avoid overflow */
 asrs r0,r0,#8
 asrs r1,r1,#8
 mov r2,r0
 cmp r2,#0
 it mi
 rsbmi r2,r2,#0
 mov r3,r1
 cmp r3,#0
 it mi
 rsbmi r3,r3,#0
 adds r4,r2,r3
 movs r5,#49
 muls r3,r5,r3
 cbz r4,angle
 add.w r3,r3,r4,lsr #1
 udiv r3,r3,r4
 ldr r4,=0x08065140
 ldrh.w r3,[r4,r3,lsl #1]
 cmp r0,#0
 it mi
 rsbmi.w r3,r3,#32768
 cmp r1,#0
 it mi
 rsbmi r3,r3,#0
angle:
 /* area already includes offset. prev is prior settled step. */
 ldrd r8,r9,[r7,#72]
 movw r4,#15204
 mul r2,r9,r4
 add.w r3,r3,r2,asr #15
 sub.w r3,r3,r8
 sxth r3,r3
 mul r3,r10,r3
 asrs r3,r3,#11
 movw r4,#13442
 mul r2,r9,r4
 sub.w r3,r3,r2,asr #15
 add.w r3,r3,#4096
 movw r10,#19326
 ldr r4,=0x080650a4
 movs r5,#0
 mov.w r6,#0x80000000
 movs r0,#0
loop:
 ldrh.w r1,[r4,r5,lsl #1]
 mul r2,r1,r10
 asrs r2,r2,#15
 subs r2,r2,r3
 sxth r2,r2
 muls r2,r2,r2
 sub.w r1,r1,r9
 muls r1,r1,r1
 add.w r2,r2,r1,lsr #13
 cmp r2,r6
 itt lo
 movlo r6,r2
 movlo r0,r5
 adds r5,#1
 cmp r5,#78
 blo loop
 ldrh.w r1,[r4,r0,lsl #1]
 add r8,r1
 sub.w r8,r8,#4096
 sxth r8,r8
 /* prev = step + decay * (prev-step) */
 sub.w r2,r9,r1
 movw r3,#3797
 muls r2,r3,r2
 add.w r9,r1,r2,asr #15
 strd r8,r9,[r7,#72]
 pop.w {r8-r10}
 pop {r4-r7,pc}
 .ltorg
