MEMORY { FLASH (rx) : ORIGIN = 0x0806fb00, LENGTH = 256 }
SECTIONS { .about_recovery 0x0806fb00 : { *(.about_recovery) } > FLASH }
