# RadMod V1.0Alpha2 — official development baseline
User approved S10 and requested promotion on 2026-11-25 (Pacific). Alpha2 changes only the About screen version from V1.0Alpha1 to V1.0Alpha2. All executable instructions, calibration tables, RF modulation, silence gating, receive and other mode behavior are identical to S10. The version-only binary itself has not been independently hardware tested. See S10's included source package for implementation details and remaining hardware verification limitations. No claim of measured regulatory compliance is made.

## Reproduce
Run `python build_version.py` in this folder. The script locks the input hash, checks the About pointer and renderer, verifies the BTF encode/decode roundtrip and asserts exactly one byte changes in both the decoded image and encoded BTF. See manifest.json and build.log.

## Rollback
The exact user-approved S10 binary is included, along with its original source/verification/rollback archive. Preserve Alpha1 separately as an older known baseline. Use Alpha2 for subsequent development unless the user explicitly changes the baseline.
