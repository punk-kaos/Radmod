ENTRY(gate_adc_entry)
original_compact_hilbert = 0x08063CD8;
original_voice_begin = 0x0806472C;
SECTIONS {
  .gate.text 0x0806FCC0 : {
    KEEP(*(.gate.text))
    *(.text .text.*)
    *(.rodata .rodata.*)
    . = ALIGN(4);
  }
  /DISCARD/ : { *(.comment) *(.note*) *(.ARM.exidx*) *(.eh_frame*) }
}
ASSERT(ADDR(.gate.text)+SIZEOF(.gate.text)<=0x08071800,"Overlay exceeds original empty R1 code cave");
