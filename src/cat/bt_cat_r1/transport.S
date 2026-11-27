.syntax unified
.cpu cortex-m4
.thumb
.section .text,"ax",%progbits
/* owner word uses four more bytes of existing idle OEM ring. Tag 0x42544300;
 * bit 7 is parser busy; low byte 1 wired / 2 BLE. No new global allocation. */
.global wire_rx,ble_rx,ack_hook,reply_hook,packed_hook
.thumb_func
wire_rx:
 push {r4,lr}
 mov r4,r0
 movs r1,#1
 bl route
 cmp r0,#0
 mov r0,r4
 pop {r4,lr}
 beq.w oem_wire
 bx lr
.thumb_func
ble_rx:
 uxtb r0,r0
 mov r6,r0
 movs r1,#2
 bl route
 cbnz r0,ble_done
 mov r1,r6
 ldr r0,=0x2000a3fc
 b.w ble_resume
ble_done:
 pop {r4,r5,r6,pc}
/* r0 byte, r1 source. Returns 1 consumed, 0 OEM. */
.thumb_func
route:
 push {r4-r8,lr}
 mov r4,r0
 mov r5,r1
 ldr r6,=0x2000b050
 ldr r8,=0x42544300
 mrs r7,primask
 cpsid i
 ldr r0,[r6]
 bic r1,r0,#0xff
 cmp r1,r8
 bne check_magic
 tst r0,#0x80
 bne consume
check_magic:
 ldr r1,[r6,#4]
 ldr r2,=0x43414152
 cmp r1,r2
 bne idle
 orr r1,r8,r5
 cmp r0,r1
 bne consume
 b guards
idle:
 cmp r4,#0x7e
 bne pass
 /* Don't intercept a tilde inside an OEM Bluetooth frame. */
 ldr r0,=0x2000b22c
 ldr r1,[r0]
 ldr r2,[r0,#8]
 orrs r1,r2
 bne pass
 guards:
 ldr r0,=0x2000afc4
 ldrb r1,[r0,#2]
 cbnz r1,guard_fail
 ldr r0,=0x2000a3fc
 ldrb r1,[r0,#1]
 cmp r1,#13
 beq guard_fail
 ldrb r1,[r0,#0x47]
 cbnz r1,guard_fail
 orr r0,r8,r5
 orr r0,r0,#0x80
 str r0,[r6]
 msr primask,r7
 mov r0,r4
 bl parser
 /* Keep routing correct through final ACK; parser clears magic before ACK. */
 mrs r7,primask
 cpsid i
 ldr r0,[r6,#4]
 ldr r1,=0x43414152
 cmp r0,r1
 ite eq
 orreq r0,r8,r5
 movne r0,#0
 str r0,[r6]
 b consume
 guard_fail:
 ldr r0,[r6,#4]
 ldr r1,=0x43414152
 cmp r0,r1
 beq consume
 pass:
 movs r0,#0
 b restore
 consume:
 movs r0,#1
 restore:
 msr primask,r7
 pop {r4-r8,pc}
/* r1 owner check, r2 scratch, r0/r12 preserved. */
.thumb_func
is_ble:
 ldr r1,=0x2000b050
 ldr r1,[r1]
 bic r1,r1,#0x80
 ldr r2,=0x42544302
 cmp r1,r2
 bx lr
.thumb_func
ack_hook:
 /* no change to wired ack, no GPIO writes for BLE */
 push {r0,lr}
 bl is_ble
 pop {r0,lr}
 bne wired_ack
 ldr r1,=0x40013800
 ldr r2,[r1]
 tst r2,#0x80
 it ne
 strne r0,[r1,#4]
 bx lr
wired_ack:
 mov r12,r0
 movw r1,#0x4c00
 b.w ack_resume
.thumb_func
reply_hook:
 /* r12=0 handshake or 1 query. Preserve LR and r12. */
 push {r0,lr}
 bl is_ble
 pop {r0,lr}
 bne wired_reply
 ldr r1,=0x40013800
 ldr r2,[r1]
 tst r2,#0x80
 beq reply_done
 cmp r12,#0
 bne.w pack_freq
 movs r2,#0x21
 str r2,[r1,#4]
reply_done:
 bx lr
wired_reply:
 movw r1,#0x4c00
 movt r1,#0x4000
 b.w reply_resume
.thumb_func
packed_hook:
 push {r0,lr}
 bl is_ble
 pop {r0,lr}
 ite eq
 ldreq r1,=0x40013800
 ldrne r1,=0x40004c00
 b.w packed_resume
.ltorg
