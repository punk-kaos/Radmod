ENTRY(am_irq)
edge = 0x080617ed;
audio = 0x08061851;
SECTIONS { . = 0x08061694; .payload : { *(.text.irq) } /DISCARD/ : { *(.ARM.attributes*) *(.comment*) } }
