# Alpha2 development continuation

ACC1500 R1 was hardware-confirmed and promoted on November 25, 2026 (Pacific). I400x1 is a host-verified but hardware-untested experiment. Historical filenames retain the UNTESTED suffix; the About version remains V1.0Alpha2.

Run `python3 build_alpha2.py` to build ACC1500 from the checked-in Alpha2 image, or `python3 build_alpha2.py --target i400x1` to build the experimental variant. Every stage is locked to the exact archived SHA-256. The build requires Python 3 (assertions enabled), Clang/LLVM, ld.lld, llvm-objcopy, llvm-objdump and readelf. The stock-to-Alpha1 builder is unchanged.

BT CAT R1 adds BLE alongside wired CAT, with the first accepted handshake owning the parser. Explicit exit or restart releases ownership; unexpected disconnect auto-release is not implemented. FM-only remote PTT is unchanged.

BC203 adds calibrated asymmetric PWM mapping. PAIR R2 skips alternate RF-off pulses without changing timer events. ACC1500 uses a signed error accumulator in the high 16 bits of the existing period counter at 0x20017C8C; the low bits retain the count/parity. The original 16 kHz timer, 8 kHz mic, RF writer and PTT handling remain. No new SRAM or flash allocation. I400x1 adapts the offset without adding persistent state, filling the existing 344-byte ISR allocation; actual MCU interrupt timing is unverified.

Conducted IQ comparisons for BC203 / PAIR R2 / ACC1500: strongest mirror −9.79 / −14.88 / −23.26 dBc; unwanted RF fraction 29.95 / 15.36 / 9.44%; adjacent-band power −16.38 / −11.16 / −12.53 dBc. I400x1 simulation predicts −24.31 dBc strongest mirror and 7.10% unwanted RF. These figures do not establish on-air regulatory compliance. Use a rated dummy load and attenuated SDR.

Rejected experiments: NB32-F10 froze on TX; NB16 Recovery produced carrier only. Neither is in the build chain. Historical simulation packages, test fixtures and full verification logs are not included in this core-source import.
