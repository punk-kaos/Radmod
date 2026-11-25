.syntax unified
.thumb
.cpu cortex-m4
.section .text.lsb,"ax"
.global freq,phase,rx
.thumb_func
freq:
 push {r1,r2,lr}
 bl mode
 cmp r1,#3
 it eq
 subweq r0,r0,#625
 pop {r1,r2,lr}
 b.w stock_set
.thumb_func
phase:
 push {r1,r2,lr}
 bl mode
 cmp r1,#3
 pop {r1,r2,lr}
 beq mirror
 add.w r0,r1,r0,lsl #2
 b.w resume
mirror:
 sub.w r0,r5,r12
 add r0,r6
 b.w resume
.thumb_func
mode:
 ldr r1,=0x2000a468
 ldrb.w r2,[r1,#0xfa]
 cmp r2,#2
 bhi invalid
 add.w r1,r1,r2,lsl #6
 add.w r1,r1,r2,lsl #4
 add.w r1,r1,r2,lsl #3
 ldrb.w r1,[r1,#0x148]
 and r1,r1,#3
 bx lr
invalid:
 movs r1,#0
 bx lr
.thumb_func
rx:
 cmp r0,#3
 it eq
 moveq r0,#2
 add sp,#8
 pop {r4,r5,r7,pc}
.ltorg
