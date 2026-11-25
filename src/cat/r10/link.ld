ENTRY(parser)
query_r9 = 0x08071b0d;
echo_r9 = 0x08071b13;
oem_rx = 0x0800c4ed;
oem_poll = 0x0800d2d5;
SECTIONS {
 . = 0x08071778; .aux : { *(.text.ack) *(.text.forehook) }
 . = 0x080718b0; .payload : { *(.text.parser) *(.text.service) *(.text*) *(.rodata*) }
 /DISCARD/ : { *(.ARM.attributes) *(.comment) *(.ARM.exidx*) }
}
