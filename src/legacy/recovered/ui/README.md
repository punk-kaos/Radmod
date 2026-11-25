# RadMod R5 + V330 C UI — Rebased bench firmware

**Base:** User-supplied `RT950_V029_REG70_LIVE_VOICE_FAST_PRIMER_R5(1).BTF` (SHA-256: `4988be0aabe7c16b86113a7dd34b2cb3aeb76f5e54f25a0b11ee14e9502c4b29`).  
**UI reference:** Hardware-confirmed V330 C `RT950_V029_V330_ABOUT_MINIMAL_USB_BADGE_RC.BTF` (SHA-256: `568f5bf45f381355854d4126504d57be87a68b1938712300809a577149fa8d00`).

**Flashable test image:** `build/RT950_V029_REG70_FAST_PRIMER_R5_V330C_UI_PORT_UNTESTED.BTF`.

## UI changes

- Mode menu **FM / AM / USB**, with `PHASE` relabeled to `USB`.
- **SDSB removed** from the selector (menu count 4→3, fourth entry aliases FM, legacy SDSB TX/RX entry handlers disabled).
- `RX Modulation` and `RX MODULATION` labels renamed **Modulation**.
- USB indicator on the main screen, using exactly the RGB565 image tiles and OEM bitmap draw method from V330 C for both themes.
- Safe About screen **RadMod / V0.1 / RT950 Pro**, using the exact fixed-text rendering implementation that worked on physical V330 C.

## Memory relocation

**Important:** R5 occupies the V330 C UI overlay addresses (`0x08064000`–`0x08064954`). The port **does not overwrite them**. R5's existing code is preserved; unused high-flash space is used instead:

| New address | Payload |
|---|---|
| `0x0806F600` | USB indicator tiles, 6 fragments |
| `0x0806FA00` | Original V330 C USB bitmap handler, compiled for new address |
| `0x0806FB00` | Original V330 C safe About renderer, compiled for new address |

Only the OEM hook at `0x0800F932` (USB badge), OEM About draw call at `0x08019E7E`, selector UI resources, and inert legacy SDSB wrappers are changed. These were cross-checked with V330 C. The original R5 transmit code, FSK priming, timing, ISR vectors, receive path, and debug banner remain byte-for-byte unchanged. Note: RX is the **original R5 RX implementation**, not V328's experimental USB/zero-IF receive overlay; this task was a UI-only port.

## Verification

Run from the package root:

```bash
python3 build_ui.py
python3 tests/verify_rebase.py
```

The build requires `clang`, `ld.lld`, `llvm-objcopy`. All inputs are SHA-locked. The build confirms decoded patch allowlist, compare against V330 C working machine code with only allowed address relocations, Thumb branch destinations, unchanged R5 overlays and UART banner, and BTF re-encode/decode roundtrip.

**Status:** Passed static builds and host verification, but the rebased image has **not yet been flashed/verified on physical Radtel hardware**.

## Radio check

Flash with your standard Radtel method, retaining the original R5 firmware for rollback. Check menu order/absence of SDSB, USB badge on both light/dark themes, About open and close repeatedly, original FAST_PRIMER_R5 live USB voice startup and PTT behavior, and ordinary FM/AM. The debug banner stays `RADMOD REG70 LIVE 5`, so your existing R5 UART capture script remains compatible.
