ENTRY(trim)
stock_set_frequency = 0x0801e511;
SECTIONS { . = 0x0807103c; .text : { *(.text.trim) } /DISCARD/ : { *(.ARM.attributes) *(.comment) } }
