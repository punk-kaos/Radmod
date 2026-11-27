ENTRY(bc203_map)
SECTIONS { . = 0x08061f80; .payload : { *(.text*) *(.rodata*) } /DISCARD/ : { *(.ARM.exidx*) *(.comment*) *(.ARM.attributes*) } }
