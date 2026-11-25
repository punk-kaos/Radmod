ENTRY(freq)
stock_set = 0x0801e511;
resume = 0x080716b1;
SECTIONS { . = 0x08070444; .text : { *(.text*) } /DISCARD/ : { *(.ARM.attributes) *(.comment) } }
