.syntax unified
.thumb
.cpu cortex-m4
.section .helpers,"ax",%progbits
.global select_table,finish,early,noadc
.thumb_func
select_table:
 bl mode
 cmp r1,#3
 ite eq
 ldreq r4,=0x080704ac
 ldrne r4,=0x080650a4
 ite eq
 moveq r12,#42
 movne r12,#78
 movs r5,#0
 b.w loop_init
.thumb_func
finish:
 cmp.w r12,#42
 it eq
 rsbeq r0,r0,#111
 pop.w {r8-r10}
 pop {r4-r7,pc}
.thumb_func
early:
 bl mode
 cmp r1,#3
 ite eq
 moveq r0,#111
 movne r0,#0
 b.w publish
.thumb_func
noadc:
 bl mode
 cmp r1,#3
 ite eq
 moveq r0,#111
 movne r0,#0
 strb r0,[r4,#13]
 b.w noadc_resume
.balign 4
.ltorg
.section .warm,"ax",%progbits
 cmp.w r9,#256
 blo.w early
.section .cmp,"ax",%progbits
 cmp r5,r12
.section .freq,"ax",%progbits
 subw r0,r0,#50
