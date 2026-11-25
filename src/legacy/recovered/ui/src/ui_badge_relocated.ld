PROVIDE(display_bitmap = 0x0802a715);
ENTRY(main_usb_badge)
SECTIONS { .main 0x0806fa00 : { *(.text.main_usb_badge) } /DISCARD/ : { *(.ARM.exidx*) *(.comment*) *(.note*) }}
