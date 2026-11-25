ENTRY(dispatch)
queue_r10 = 0x08071917;
error_r10 = 0x08071929;
ack = 0x08071779;
service_r10 = 0x08071941;
SECTIONS {
 . = 0x08061000;
 .payload : { *(.text.dispatch) *(.text*) *(.rodata*) }
 /DISCARD/ : { *(.ARM.attributes) *(.comment) *(.ARM.exidx*) }
}
