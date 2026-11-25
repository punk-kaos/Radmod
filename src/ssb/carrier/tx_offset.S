.syntax unified
.thumb
.section .text,"ax",%progbits
.global tx_offset
.type tx_offset,%function
.thumb_func
tx_offset:
    /* Only called at OEM TX setup 0x0801f2ca. Frequency argument in 10 Hz units.
       Match existing baseline USB mode predicate, not RX channel context.
       Limit measured correction to 144–148 MHz, including upper bound. */
    ldr r1, =0x2000a468
    ldrb.w r2, [r1, #0xfa]
    cmp r2, #2
    bhi 1f
    movs r3, #0x58
    muls r2, r3, r2
    add r1, r2
    ldrb.w r2, [r1, #0x148]
    ands r2, r2, #3
    cmp r2, #2
    bne 1f
    ldr r1, =14400000
    cmp r0, r1
    blo 1f
    ldr r1, =14799936
    cmp r0, r1
    bhs 1f
    adds r0, #64
1:
    b.w oem_tx_frequency
.size tx_offset,.-tx_offset
.ltorg
