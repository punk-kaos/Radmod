.syntax unified
.thumb
.text
.p2align 1
apply_b:
 movs r2,#0
 ldrh r3,[r6,#-15]
 ldr r12,[r6,#-19]
 asr r12,r12,#8
 tst r3,#1
 bne is_open
 cmp r12,#36
 blt stay
 b change
is_open:
 cmp r12,#28
 bgt stay
change:
 sub r12,r0,r2
 sxth r12,r12
 cmp r12,#0
 it mi
 rsbmi r12,r12,#0
 cmp r12,#8192
 ble flip
 adds r3,#2
 cmp r3,#16
 blo save
flip:
 eor r3,r3,#1
stay:
 and r3,r3,#1
save:
 strh r3,[r6,#-15]
 tst r3,#1
 bne resume
 @ Cancel the downstream phase-error expression exactly to request zero deviation.
 ldrh r0,[r6,#-7]
 ldr r2,[r6,#-11]
 movw r3,#1762
 mul r2,r2,r3
 sub r0,r0,r2,asr #15
 uxth r0,r0
resume:
 and r1,r1,#15
 bx lr
