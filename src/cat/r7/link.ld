ENTRY(live)
resume_reply = 0x08071b59;
SECTIONS { . = 0x08071b84; .live : { *(.text.live) } /DISCARD/ : { *(.ARM.attributes) *(.comment) } }
