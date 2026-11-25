.syntax unified
.cpu cortex-m4
.thumb
.section .text.rx_usb,"ax",%progbits
.global rx_usb_reg47_hook
.type rx_usb_reg47_hook,%function
.thumb_func
rx_usb_reg47_hook:
    @ Replacement for OEM RX-only REG47 write at 0x0801F2C2.
    @ Entry: r4 points to OEM BK register callbacks, r1=0x6142, r2=BK write cb.
    @ Never replace the main TX path, ISR, DMA vector or modulator.
    @ Preserve all callee-saved regs and keep SP 8-byte aligned during callbacks.
    push {r4-r7,lr}
    sub sp,#4
    mov r5,r2              @ original BK write callback
    mov r6,r1              @ original REG47 value
    ldr r7,=0x2000a468    @ OEM channel state base
    ldrb.w r0,[r7,#0xfa]   @ active VFO index: 0..2
    cmp r0,#2
    bhi .Loem
    movs r1,#0x58
    muls r0,r1,r0
    adds r7,r7,r0
    ldrb.w r0,[r7,#0x148] @ per-channel modulation selector
    ands r0,r0,#3
    cmp r0,#2
    bne .Loem
.Lusb:
    @ BK4829 BASEBAND2 AF route 5 (stock RX = 1) with OEM low control bits.
    movw r1,#0x6542
    movs r0,#0x47
    blx r5
    @ Zero-IF direct conversion. This is NOT an RF USB image-rejecting filter.
    movs r1,#0
    movs r0,#0x3d
    blx r5
    @ Freeze AFC (REG73 bit 4) without destroying unrelated flags.
    movs r0,#0x73
    ldr r3,[r4,#4]         @ OEM BK read callback
    blx r3
    orr r1,r0,#0x10
    movs r0,#0x73
    blx r5
    b .Lend
.Loem:
    mov r7,r0            @ retain non-USB mode (or invalid VFO sentinel)
    mov r1,r6
    movs r0,#0x47
    blx r5
    @ If we are leaving the zero-IF USB mode, restore the regular IF
    @ and resume AFC. Do not change an already configured FM/AM IF.
    movs r0,#0x3d
    ldr r3,[r4,#4]
    blx r3
    cbnz r0,.Lcheck_afc
    movw r1,#0x2aab       @ normal IF config used by BK4819 FM firmware
    movs r0,#0x3d
    blx r5
.Lcheck_afc:
    @ AM receivers may intentionally keep AFC off; only enable it for FM.
    cmp r7,#0
    bne .Lend
    movs r0,#0x73
    ldr r3,[r4,#4]
    blx r3
    bic r1,r0,#0x10    @ restore AFC on ordinary receive path
    movs r0,#0x73
    blx r5
.Lend:
    add sp,#4
    pop {r4-r7,pc}
.size rx_usb_reg47_hook, .-rx_usb_reg47_hook
