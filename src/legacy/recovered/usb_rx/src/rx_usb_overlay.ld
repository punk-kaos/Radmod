ENTRY(rx_usb_reg47_hook)
SECTIONS {
 .rx_usb 0x0806FC00 : { *(.text.rx_usb) }
 /DISCARD/ : { *(.ARM.exidx*) *(.comment*) *(.note*) }
}
