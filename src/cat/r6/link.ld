ENTRY(probe)
oem_rx = 0x0800c4ed;
SECTIONS { . = 0x08071b00; .probe : { *(.text.probe) } /DISCARD/ : { *(.ARM.attributes) *(.comment) } }
