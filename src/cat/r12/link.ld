ENTRY(dispatch)
ack = 0x08071779;
old_dispatch = 0x08061001;
old_service = 0x08061019;
native_ptt = 0x0801ce25;
old_tick = 0x0800c9bd;
SECTIONS {
 . = 0x08061400;
 .payload : { *(.text.dispatch) *(.text*) *(.rodata*) }
 /DISCARD/ : { *(.ARM.attributes) *(.comment) *(.ARM.exidx*) }
}
