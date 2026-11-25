ENTRY(link_entry)
link_resume = 0x0801ed55;
oem_freq = 0x0801e511;
direct_freq_resume = 0x0801f0f5;
audio_resume = 0x0801efb5;
SECTIONS {
 .ext.text 0x08070500 : ALIGN(4) { KEEP(*(.ext.text)) KEEP(*(.ext.text.*)) *(.text*) *(.rodata*) KEEP(*(.ext.params)) }
 /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment) *(.note*) *(.eh_frame*) }
}
