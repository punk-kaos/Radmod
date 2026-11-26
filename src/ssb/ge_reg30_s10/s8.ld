ENTRY(generator)
copy_template = 0x0806381d;
SECTIONS { . = 0x080636f0; .generator : { *(.generator) } /DISCARD/ : { *(.ARM.attributes) *(.comment) } }
