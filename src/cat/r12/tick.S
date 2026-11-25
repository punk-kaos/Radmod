.syntax unified
.cpu cortex-m4
.thumb
.section .text.tick,"ax",%progbits
.global tick
.thumb_func
tick:
 mrs r12,primask
 cpsid i
 ldr r0,=0x2000b054
 ldr r1,[r0]
 ldr r2,=0x43414152
 cmp r1,r2
 bne done
 ldrb r1,[r0,#7]
 cbz r1,done
 ldr r2,=0x200001ec
 ldrb r2,[r2]
 adds r2,#1
 movs r3,#10
 udiv r1,r2,r3
 mls r2,r1,r3,r2
 cbnz r2,done
 ldrb r1,[r0,#7]
 subs r1,#1
 strb r1,[r0,#7]
done:
 msr primask,r12
 b.w old_tick
