# Legacy OEM overlay boundary

`patches/legacy_oem_to_uhf_r1.json` contains the exact decoded byte edits from
OEM V0.29 to the hardware-tested V0.2 dual-BK/UHF R1 baseline. This is a
binary patch expressed as textual, address-checked records, not recovered C
source. It includes early SSB plumbing, UI edits, lookup tables, and flash
extension contents. The later active modules compile against this layout.

`recovered/` contains source fragments and build recipes recovered from R5,
the V330C UI rebase, and the first USB RX port. They are kept for further
source recovery only, not executed by the release build; their original
inputs are not included, and they do not represent the entire legacy overlay.
Some of their code was superseded by later active modules.

Do not describe the repository as a complete OEM firmware source release or
as fully source-reconstructed RadMod. Replacing this legacy patch with
source-built modules is the remaining refactoring task. Preserve absolute
addresses and compare every migration against the verified release hash.
