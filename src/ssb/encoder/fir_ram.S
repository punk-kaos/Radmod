.syntax unified
.thumb
.section .text.fir_ram,"ax",%progbits
.global fir_ram
.thumb_func
fir_ram:
 push {r4-r7,lr}
 movs r4,#0
 movs r5,#0
 movs r6,#16
 and r1,r1,#15
1:
 ldr r7,[r0,r1,lsl #2]
 ldmia.w r2!,{r3,r12}
 smlad r4,r7,r3,r4
 smlad r5,r7,r12,r5
 subs r1,#1
 and r1,r1,#15
 subs r6,#1
 bne 1b
 mov r0,r4
 mov r1,r5
 pop {r4-r7,pc}
