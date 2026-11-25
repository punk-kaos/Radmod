ENTRY(reg30_transition)
stock_reg30 = 0x08070501;
stock_tx_gpio = 0x0801d5a5;
SECTIONS { .  =  0x08061630; .payload : { *(.text.hooks) *(.text*) *(.rodata*) } /DISCARD/ : { *(.ARM.exidx*) *(.comment*) *(.ARM.attributes*) } }
