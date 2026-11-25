.syntax unified
.thumb
.section .ext.text,"ax",%progbits
.align 2
.global link_entry
.type link_entry,%function
.thumb_func
link_entry:
    /* preserve original arguments, mode and return address; original
       code may tailcall the BK writer. No changes to its body. */
    push.w {r0-r3,r4,r5,r12,lr}
    mov r4,r0
    mov r1,lr
    bl before_link
    pop.w {r0-r3,r4,r5,r12,lr}
    push {r4,lr}
    mov r4,r0
    bl link_original
    push {r0-r3}
    mov r0,r4
    bl after_link
    pop {r0-r3}
    pop {r4,pc}
.size link_entry,.-link_entry
.type link_original,%function
.thumb_func
link_original:
    push {r4,r5,r6,lr}
    mov r4,r0
    b.w link_resume
.size link_original,.-link_original
.align 2
.global clarifier_entry
.type clarifier_entry,%function
.thumb_func
clarifier_entry:
    push {r4,lr}
    bl apply_clarifier
    pop.w {r4,lr}
    b.w oem_freq
.size clarifier_entry,.-clarifier_entry
.align 2
/* direct frequency-update function writes 38/39 then selects RX; replay
   its saved prologue and original argument after the clarifier. */
.global direct_freq_entry
.type direct_freq_entry,%function
.thumb_func
direct_freq_entry:
    push {r4,lr}
    bl apply_clarifier
    pop.w {r4,lr}
    push {r4,r5,r6,lr}
    mov r4,r0
    b.w direct_freq_resume
.size direct_freq_entry,.-direct_freq_entry
.align 2
.global af_write_entry
.type af_write_entry,%function
.thumb_func
af_write_entry:
    /* original code: movs r0,#47; ldr r2,[r5,#8]; blx r2.
       r4 holds original request, r1 holds OEM AF value. */
    push {r4,lr}
    mov r0,r4
    bl intercept_af
    mov r1,r0
    movs r0,#0x47
    ldr r2,[r5,#8]
    pop.w {r4,lr}
    bx r2
.size af_write_entry,.-af_write_entry
.align 2
.global audio_entry
.type audio_entry,%function
.thumb_func
audio_entry:
    push {r4,lr}
    mov r4,r0
    bl audio_original
    push {r0-r3}
    mov r0,r4
    bl audio_route
    pop {r0-r3}
    pop {r4,pc}
.size audio_entry,.-audio_entry
.type audio_original,%function
.thumb_func
audio_original:
    push {r4,r5,r6,lr}
    mov r4,r0
    b.w audio_resume
.size audio_original,.-audio_original
