.syntax unified
.thumb
.cpu cortex-m4
.section .text.trim,"ax",%progbits
.global trim
.type trim,%function
.thumb_func
trim:
    /* Existing USB-only TX hook has already checked mode and channel. */
    ldr r1, =0x20000c70
    ldrb r1, [r1]
    cmp r1, #1
    beq secondary
    cmp r1, #0
    bne done
    /* Exact legacy 2m correction on primary. */
    ldr r1, =14400000
    cmp r0, r1
    blo done
    ldr r1, =14800000
    cmp r0, r1
    bhs done
    adds r0, #64
    b done
secondary:
    ldr r1, =44120000
    cmp r0, r1
    bls low
    ldr r2, =76000000
    cmp r0, r2
    bhs upper
    /* correction=168+round((f-44120000)*82/31880000) */
    subs r1, r0, r1
    movs r2, #82
    muls r1, r2, r1
    ldr r2, =15940000
    adds r1, r1, r2
    ldr r2, =31880000
    udiv r1, r1, r2
    adds r1, #168
    adds r0, r0, r1
    b done
upper:
    ldr r1, =99999600
    cmp r0, r1
    bhs high
    /* correction=250+round((f-76000000)*40/23999600) */
    subs r1, r0, r2
    movs r2, #40
    muls r1, r2, r1
    ldr r2, =11999800
    adds r1, r1, r2
    ldr r2, =23999600
    udiv r1, r1, r2
    adds r1, #250
    adds r0, r0, r1
    b done
low:
    adds r0, #168
    b done
high:
    addw r0, r0, #290
done:
    b.w stock_set_frequency
.size trim, .-trim
.ltorg
