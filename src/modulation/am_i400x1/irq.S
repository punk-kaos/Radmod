.syntax unified
.thumb
.cpu cortex-m4
.section .text.irq,"ax",%progbits
.global am_irq
.thumb_func
am_irq:
 push {r3-r7,lr}
 ldr r4,=0x20017c70
 ldr r5,=0x40000400
 ldr r0,[r5,#16]
 ldr r1,[r5,#12]
 ands r0,r1
 movs r7,#3
 ands r7,r0
 mvns r0,r7
 str r0,[r5,#16]
 ldr r0,[r4,#-240]
 ldr r1,=0x414d5033
 cmp r0,r1
 bne inactive
 ldr r0,[r4,#-236]
 mvns r1,r1
 cmp r0,r1
 bne inactive
 ldr r0,[r4,#36]
 adds r0,#1
 str r0,[r4,#36]
 ldr r0,=0x40011808
 ldr r0,[r0]
 and r0,#0x2c
 cmp r0,#0x2c
 beq fault
 ldr r0,[r4,#16]
 cbnz r0,fault
 cmp r7,#3
 beq late
 ldr r0,[r4,#44]
 cbnz r0,recover
 cmp r7,#1
 beq update
 cmp r7,#2
 bne done
 /* Only count an active period; preserve the original compare schedule.
    periods word: low16 successful updates modulo 65536; high16 signed error.
    Startup clears the entire word. No new SRAM addresses. */
 ldr r0,[r4,#20]
 cmp r0,#0
 beq audio_if_due
 ldr r0,[r4,#28]
 asrs r1,r0,#16
 ldr r3,[r5,#52]
 movw r2,#7500
 subs r2,r2,r3
 movw r3,#1875
 subs r3,r2,r3
 it mi
 rsbmi r3,r3,#0
 subs r3,#64
 it mi
 movmi r3,#0
 cmp r3,#400
 it hi
 movhi.w r3,#400
 subw r6,r2,#1500
 subs r3,r6,r3
 it mi
 movmi r3,#0
 adds r1,r1,r3
 cmp r2,r1,lsl #1
 it le
 suble r1,r1,r2
 bfi r0,r1,#16,#16
 str r0,[r4,#28]
 bgt audio_if_due
 movs r0,#0
 bl edge
 cmp r0,#0
 bne audio_if_due
 b late
fault:
 movs r0,#1
 str r0,[r4,#16]
 movs r0,#0
 bl edge
 cmp r0,#0
 beq done
 movs r0,#0
 str r0,[r5,#12]
 str r0,[r5]
 b done
inactive:
 movs r0,#0
 str r0,[r5,#12]
 b done
late:
 ldr r0,[r4,#12]
 adds r0,#1
 str r0,[r4,#12]
recover:
 movs r0,#0
 str r0,[r4,#24]
 ldr r1,[r4,#28]
 uxth r1,r1
 str r1,[r4,#28]
 bl edge
 eor r0,#1
 str r0,[r4,#44]
 b done
update:
 /* Preserve original BC203 duty and CCR1 timing. */
 ldrh r6,[r4,#2]
 str r6,[r5,#52]
 subw r1,r6,#1140
 ldr r0,[r5,#36]
 cmp r0,r1
 bhi late
 movs r0,#1
 bl edge
 cmp r0,#0
 beq late
 ldr r0,[r4,#28]
 adds r1,r0,#1
 bfi r0,r1,#0,#16
 str r0,[r4,#28]
 lsls r0,#31
 bpl done
 ldr r0,=0x40013c00
 ldr r1,[r0]
 lsls r1,#30
 bmi adc_ok
 ldr r1,[r4,#8]
 adds r1,#1
 str r1,[r4,#8]
 movs r1,#0
 str r1,[r4,#24]
 movw r1,#5625
 strh r1,[r4,#2]
 b trigger
adc_ok:
 ldr r1,[r0,#76]
 ubfx r1,r1,#0,#12
 str r1,[r4,#52]
 movs r1,#1
 str r1,[r4,#24]
trigger:
 ldr r1,[r0,#8]
 orr r1,#0x400000
 str r1,[r0,#8]
 movw r0,#3750
 cmp r6,r0
 blo done
audio_if_due:
 ldr r0,[r4,#24]
 cbz r0,done
 pop.w {r3-r7,lr}
 b.w audio
done:
 pop {r3-r7,pc}
.ltorg
