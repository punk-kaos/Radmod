# RadMod — Radtel RT-950 Pro Firmware

**More modes. More control. No hardware modifications.**

RadMod is an aftermarket firmware modification for the Radtel RT-950 Pro that brings new modulation modes and computer control to the original radio, while retaining its familiar interface and FM functionality.


## Features

### USB and LSB

- Live-voice upper and lower sideband transmission.
- Independently selectable USB and LSB modes.
- Experimental SSB reception.

### AM

- Experimental live-voice AM transmission.
- Retains the radio's original AM reception.

### CAT control

- Computer control using a subset of the Yaesu FT-817 CAT protocol.
- Read and set frequency and modulation mode.
- VFO selection.
- Signal strength and transmit status reporting.

### User interface

- Unified **Modulation** menu for FM, AM, USB and LSB.
- USB mode indication on the operating display.
- Original FM functionality and familiar operating interface retained.

## Supported modes

| Mode | Receive | Transmit |
| --- | --- | --- |
| FM | Supported | Supported |
| AM | Supported | Experimental |
| USB | Experimental | Supported |
| LSB | Experimental | Supported |

## Development status

USB and LSB transmission have been tested on physical radios. AM transmission is working in an experimental development build and is not yet part of the main baseline.

SSB transmission still has residual carrier and unwanted spectral components. SSB reception does not yet provide independent receive-side sideband rejection. CAT compatibility is partial, and remote PTT is currently limited to FM.

## Compatibility

RadMod is based on the original V0.29 firmware for the Radtel RT-950 Pro. No hardware modifications are required. Other radio models and hardware revisions have not been verified.

Keep a known-working firmware image available for recovery. Experimental transmit modes should be evaluated on a dummy load before on-air use.

## Building

### Requirements

Python 3, Clang/LLVM (verified with Clang 17.0.0, llvm-objcopy and llvm-objdump), `ld.lld`, GNU `readelf` and `nm`, native C compiler available as `clang` or `cc`. Commands must be on PATH. On macOS install LLVM and binutils and put their executable directories on PATH; Apple Clang alone is not the tested ARM toolchain. The verified run was on Linux, not macOS. No Python packages are needed for the release build. Do not use Python `-O`.

### Build

Place your own OEM firmware in `stock/` (see `stock/README.md` for the exact SHA-256), then:

```sh
python3 build.py --oem stock/RT_950Pro_V0.29_260617.BTF
# or
make OEM=stock/RT_950Pro_V0.29_260617.BTF
```

The build creates the following in `build/`:

- `RT950_R5_RadMod_V1.0Alpha1.BTF`: exact verified release image
- `radmod.patch.json`: generated decoded-address patch from OEM to Alpha1
- `manifest.json`: hashes of each build stage and final image
- `build.log`: tool commands and regression output

The source tree is not modified by the build. Intermediate firmware images are generated in an isolated temporary directory and removed on completion. The default build fails if the final SHA-256 differs from Alpha1.

### Standalone patching (no compiler required)

A reference release patch is included for convenience:

```sh
python3 tools/patch.py stock/RT_950Pro_V0.29_260617.BTF \
  patches/alpha1.release.json build/RT950_R5_RadMod_V1.0Alpha1.BTF
```

Use `build/radmod.patch.json` instead after building modified source. The patcher checks the exact OEM digest, patch boundaries, old bytes, encoding round-trip and final digest. It refuses to overwrite its input. It patches files only; it does not connect to or flash a radio.

### Inspecting the BTF container

`tools/btf.py` decodes and re-encodes the BTF container and reports its layout:

```sh
python3 tools/btf.py info   RT950_R5_RadMod_V1.0Alpha1.BTF
python3 tools/btf.py decode RT950_R5_RadMod_V1.0Alpha1.BTF build/alpha1.rom
python3 tools/btf.py encode build/alpha1.rom build/rebuilt.BTF --template stock/RT_950Pro_V0.29_260617.BTF
python3 tools/btf.py verify build/*.BTF
python3 tools/btf.py diff   stock/RT_950Pro_V0.29_260617.BTF build/RT950_R5_RadMod_V1.0Alpha1.BTF
python3 tools/btf.py scan   .
```

The format is documented in `docs/btf-format.md`. The 1 KiB key block is fixed per model and the body uses a repeating 128-byte keystream with `0x00`/`0xFF` passthrough. It is obfuscation, not cryptographic protection. `diff` classifies changed bytes as active OEM code, OEM `0xFF` caves, or new flash beyond the OEM image.

### Development builds

```sh
python3 build.py --dev --oem stock/RT_950Pro_V0.29_260617.BTF --out build/dev
```

Development builds produce `RT950_R5_RadMod_DEV_UNTESTED.BTF`. This allows changed stage/final digests but retains local preimage and cave checks. Some historical overlays have fixed ROM entry addresses and dependencies on exact machine instructions in prior stages. Changes to code layout can therefore require coordinated hook/linker changes and will not automatically be safe. A new image hash is not proof of correct hardware behavior. Use a fresh output folder for experimental builds. `make test` runs the independent patcher unit tests. The build also runs gate, RX and AM host regressions.

## Roadmap

- Further improve SSB voice quality and spectral purity.
- Refine AM transmission and integrate it into the main firmware.
- Improve SSB reception and sideband selectivity.
- Expand CAT support and third-party software compatibility.

## Contributing

Feedback, bug reports, feature suggestions and radio test results are welcome. When reporting an issue, please include your RadMod version, operating mode and steps to reproduce it.

## Licensing

RadMod is an independent project and is not affiliated with or endorsed by Radtel. 
The original firmware and third-party components retain their respective rights and licenses.
