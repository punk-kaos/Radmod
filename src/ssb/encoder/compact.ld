ENTRY(voice_tick_source)
SECTIONS {
 . = 0x08071180;
 .overlay : ALIGN(4) { KEEP(*(.text.entry)) KEEP(*(.text.iq)) KEEP(*(.text.serial)) *(.text*) *(.rodata*) }
 .tables 0x080650a4 : ALIGN(4) { KEEP(*(.encoder_tables)) }
 /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) *(.ARM.attributes*) }
}
