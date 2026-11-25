.syntax unified
.cpu cortex-m4
.thumb
.section .about_recovery,"ax",%progbits
.global radmod_about_draw
.type radmod_about_draw,%function
.thumb_func
radmod_about_draw:
    push {r4,lr}
    /* Reuse only the OEM About page setup, without reading any
       dynamic radio metadata, channel records, version buffers, or RAM strings. */
    movs r0, #4
    ldr r3, =0x0800cdc5
    blx r3
    ldr r3, =0x0800cda9
    blx r3
    movs r1, #0
    movs r0, #0x10
    ldr r3, =0x08022fe5
    blx r3
    ldr r0, =brand_text
    ldr r3, =0x08003439
    blx r3
    movs r1, #0
    movs r0, #0x20
    ldr r3, =0x08022fe5
    blx r3
    pop {r4,pc}
    .balign 4
brand_text:
    .asciz "RadMod\r\nV0.1\r\nRT950 Pro\r\n"
.size radmod_about_draw, .-radmod_about_draw
