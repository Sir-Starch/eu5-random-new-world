# EU5 1.4.9 compatibility check

Audit date 2026-11-18. The installed public branch reports Steam build **26655995**, and its
map fingerprint matches the one in the RNW 1.2.2 player report. The public build was posted
on November 18. [V-LOCAL] [SOURCE] [SteamDB build record](https://steamdb.info/patchnotes/26655995/)

Of the ten map-contract files, only `game/in_game/map_data/location_templates.txt` changed. The
reference export carries nine Old World raw-material corrections from camels to horses in
Arabia and Yemen. The exact 1.4.9 map fingerprint is
`8c02119a78a80506c900f582b3673cee025afa52e22ee40f2456d7f0578058ce`. [V-LOCAL] [V-EXEC]

Against the epoch-64 reference on EU5 1.4.7, 576 of 14,925 recorded files and eight of 4,145
directory listings changed. All recorded inputs are still present. The 1.4.9 export also reads
`game/in_game/common/auto_modifiers/castile.txt`. Of the 884 generated files outside `.metadata`,
22 differ, including the location templates, remapped events and setup scripts. The map rasters
and location hierarchy match. The 1.4.9 output digest is pinned in `tests/golden_world.json`.
The 1.4.7 reference and the frozen epoch goldens remain available. [V-LOCAL] [V-EXEC]

The installed-game contract suite passed 15 checks, including content binding, localization,
and the selection cover. Full generation and the Keep the real Americas route completed with
their export validators. The native offscreen self-test passed for both windows. Game loading
and gameplay were outside the offline check. [V-EXEC]

The reported `super(type, obj)` error came from `contextlib` setting `__traceback__` on a frozen
exception while propagating `UnsupportedBuildError`. The exceptions for unsupported and missing
map inputs now allow traceback propagation. Both windows explain an unsupported installation
and preserve its fingerprint in the diagnostic trace. [V-EXEC]

## Workshop hotfix for RNW 1.2.2

The owner requested a Workshop-only package based on tagged RNW 1.2.2 (epoch 63). The source
change adds only the exact game fingerprint above. The published Workshop ZIP matched the
tagged release checksum before repacking. Of its 3,920 entries, only `eu5_export.py`, its
Python bytecode and its package `RECORD` entry changed. The three Windows program hashes
match the tagged release and retain their existing scan evidence. The repacked hash is
`3b4a27ecaf7eb9a7f3fd7aafb7bba297478cb491e91383dfb0b168c5cc0d9b42`. [V-EXEC]

Locked checks passed (3,266 Python tests, 21 optional skips and 29 Rust tests), along with 15
read-only checks on EU5 1.4.9 and a complete Keep the real Americas export. The epoch 63
reference completed and all 884 installed world files matched the export; its digest is
`b7d4cfa6599a81aa7b3c8ab8015df2fd837c18d22494f2d23f878b2af4128918`. A CPython 3.12 test
loaded the packaged bytecode and accepted the installed build without an override. The classic
window passed the native offscreen self-test. Wine stopped before startup because the sandbox
would not allow `wineserver` to bind its socket. [V-EXEC]
