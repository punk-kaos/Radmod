ENTRY(mode_reply)
SECTIONS { . = 0x08071ac0; .mode : { *(.text.mode) } /DISCARD/ : { *(.ARM.attributes) *(.comment) } }
