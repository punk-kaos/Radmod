mode = 0x0807047b;
loop_init = 0x080716d1;
publish = 0x080713ab;
noadc_resume = 0x08071257;
SECTIONS {
 . = 0x0807044e; .freq : { *(.freq) }
 . = 0x08070f60; .helpers : { *(.helpers) }
 . = 0x080713a2; .warm : { *(.warm) }
 . = 0x080716fa; .cmp : { *(.cmp) }
 /DISCARD/ : { *(.ARM.attributes) *(.comment) }
}
