.syntax unified
.thumb
.section .text.main_usb_badge,"ax",%progbits
.global main_usb_badge
.type main_usb_badge,%function
.thumb_func
main_usb_badge:
  @ Preserve OEM caller state across three bitmap calls; never leak volatile
  @ register changes back to the middle of the OEM drawing routine.
  ldrb.w r3,[r6,#0x148]
  ands r3,r3,#3
  cmp r3,#2
  bne .Loriginal
  push.w {r0,r1,r2,r3,r4,r5,r7,r12,lr}
  sub sp,#12
  cmp r5,r8
  beq .Ltheme0
  ldr r7,=.Ltheme1tab
  b .Lstart
.Ltheme0:
  ldr r7,=.Ltheme0tab
.Lstart:
  ldr r12,[r7,#0]
  str r12,[sp,#0]
  add.w r0,r4,#0x21
  movs r1,#0x99
  movs r2,#0x06
  movs r3,#0x0b
  bl display_bitmap
  ldr r12,[r7,#4]
  str r12,[sp,#0]
  add.w r0,r4,#0x21
  movs r1,#0x9f
  movs r2,#0x06
  movs r3,#0x0b
  bl display_bitmap
  ldr r12,[r7,#8]
  str r12,[sp,#0]
  add.w r0,r4,#0x21
  movs r1,#0xa5
  movs r2,#0x07
  movs r3,#0x0b
  bl display_bitmap
  add sp,#12
  pop.w {r0,r1,r2,r3,r4,r5,r7,r12,lr}
  @ Return through OEM flow after custom USB bitmap so status redraw/state updates occur.
  ldrb.w r3,[r6,#0x148]
  bx lr
.Loriginal:
  ldrb.w r3,[r6,#0x148]
  bx lr
  .balign 4
.Ltheme0tab:
  .word 0x0806f600,0x0806f684,0x0806f708
.Ltheme1tab:
  .word 0x0806f7a4,0x0806f828,0x0806f8ac
.size main_usb_badge, .-main_usb_badge
