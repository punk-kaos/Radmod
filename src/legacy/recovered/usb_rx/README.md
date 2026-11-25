# Radtel RT950 Pro — R5 FAST_PRIMER + V330C UI + V328 USB RX

**Status:** Firmware generated and static/binary verified. **NOT yet validated on a radio.**

## Delivered image

`build/RT950_V029_R5_FAST_PRIMER_V330C_UI_V328_USB_RX_PORT_UNTESTED.BTF`

SHA-256: `b9cd9b32764a6c08f7921b28fd7dc3046511dbf91649ce3cd63882a82df8bbc5`

The base is `R5_UI_base.BTF` (the previous R5 fast-primer firmware with the physically tested V330 C UI transplanted). This port does not rebase on old V328 TX code.

## What is ported

The **exact** 116-byte V328 BK4829 receive assembly at a new flash location. The original R5 receiver's `movs r0,#0x47; blx r2` sequence at `0x0801F2C2` is replaced with a four-byte Thumb BL to a relocatable RX routine. The new routine is byte-identical to V328's, linked at `0x0806FC00` instead of `0x08064600` (occupied in R5).

On modulation option 2 (USB), it sets BK REG47 to `0x6542` (BASEBAND2), REG3D to `0x0000` (zero IF), and sets REG73 bit 4 to disable AFC, using OEM BK register callbacks. Other options write the original REG47; REG3D normal IF (`0x2AAB`) is restored if zero, and REG73 AFC is re-enabled for FM. The other mode retains its original AFC policy. Existing menu options remain **FM / AM / USB**.

**This is not selective SSB RX.** It is an experimental DSB-like/zero-IF baseband receive path. It does not suppress an LSB interferer on the same frequency. The exact RX method previously used in V328 is preserved without enhancements or RF changes.

## What is deliberately unchanged

- R5 fast-primer TX startup and REG70 live-voice engine, including DMA/interrupt vectors and UART banner `RADMOD REG70 LIVE 5`
- V330 C working USB main-screen badge and `Modulation` heading
- Three-mode FM / AM / USB selector; SDSB remains disabled
- Working safe About renderer (`RadMod / V0.1 / RT950 Pro`)
- Original receive setup outside one BL instruction and the RX overlay
- R5 original timing and TX duration behavior (neither modified nor claimed unlimited)

## Memory and verification

| Item | Address | Size |
|---|---|---:|
| Original RX REG47 call patch | `0x0801F2C2` | 4 bytes |
| V328 RX overlay relocated | `0x0806FC00` | 116 bytes |
| V330 C USB badge renderer | `0x0806FA00` | unchanged |
| V330 C About renderer | `0x0806FB00` | unchanged |

The candidate differs from the R5 UI firmware in **120 decoded bytes total**, confined to those two RX regions. The original RX dispatch's surrounding instructions match the earlier V328 receiver exactly. All other bytes, including startup/voice and relocated UI, are identical.

The verification suite covers source SHA locks, exact compiled V328 RX overlay byte match, disassembly-level register operations, Thumb branch target, UI/SDSB state, RX dispatch context, R5 overlay preservation, changed-byte allowlist, and BTF encode/decode roundtrip.

Rebuild/check using Clang/LLVM and Python:

```bash
python3 build_rx.py
python3 tests/verify_rx.py
```

## Initial radio validation

1. Flash this bench candidate; retain `baseline/R5_UI_base.BTF` for rollback.
2. Confirm About opens/closes repeatedly, the USB badge displays, and the menu offers only FM / AM / USB.
3. Confirm FM reception on a known VHF/UHF signal and normal AM reception.
4. Select USB on the same band, open monitor/squelch, and listen for a known USB signal; vary tuned frequency to check for pitch tracking.
5. Cycle USB → FM → AM → USB → FM and confirm each mode's RX behavior restores.
6. Only after that, bench-check the R5 fast-primer USB TX using your normal dummy-load and attenuated SDR setup.

These receive functions have not been validated by the compile/binary tests and may require additional radio debugging.
