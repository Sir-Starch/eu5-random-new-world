# 051 — Continuous New World across the map wrap

2026-10-25, generator 0.12.2, algorithm epoch 32. Target: EU5 1.4.4 executable
(build 26142040), 1.4.3 data (build 26105915). No EU5 launch.

## Problem and correction

[OWNER report; generator installed: 0.12.1] Four generated worlds all had land near Japan, and no
continent continued through the opposite map edge. [V-EXEC C289] The generator
still deliberately cut a 24 px exclusion band at the wrap and ramped its coasts.
C286 removed a noise-variance bias, but left this independent cause in place.
The wrap already lay inside one continuous rolled crop; it was not a separate
random draw or land quota. The mandatory channel made it behave as a division.

[V-EXEC] 0.12.2 removes that channel from generated land, drawings and coast growth.
Location identities can still split at the seam for compact bounds, with land
and landmass connectivity unchanged. Terrain halo reads wrap horizontally and
fine detail uses the same rolled coordinates as the crop. Water distances, blur
and detail are periodic; spline contacts include the opposite map edge and roads
follow its short cylindrical route. No engine or shader change.

## Verification

[V-EXEC] Synthetic regressions compare whole and seam-split geography, a drawn
continent, decoded terrain height/material pixels before and after rolling, native
cylindrical distances against an independent reference, and serialized road strips
with short steps. The complete project check passes: **1,881 Python tests**, 14 skips, and **23 Rust tests**, including formatting, lint and type checks.

[UNKNOWN] The engine rendering of these new terrain/road wrap contacts. The old
crack observation (C55) stands, but C56's attribution to an engine limitation was
not established; the generator itself clamped samples and restarted fine noise.
No manual test is requested. Existing user worlds are not migrated or replaced.

Raw rasters, game files, audit logs and binaries remain in ignored
`local_data/wrap-continuity/`, `generated/` and `build/windows/`.

[V-EXEC C290] The full candidate `RNW1-0826C-SYW6B-MW73Y-C0060-40813-G11P6-36`
has 813 non-metadata mod files, digest
`1621ae318330529795f46ebd8a43e78e92b8e48c78b58925903edb5203a486cc`.
Read back from its final raster: **1,297** seam-contact rows, one crossing passable
landmass of **2,109,356** pixels; **74** wrapped road strips, maximum step
**2.9981 px** on the cylinder. The independent audit verifies every manifest file,
21,728 protected hierarchy records and 66,634,570 protected pixels, 60 changed
closed-water identities (one component each), all ports and retained Old World
contacts. The five retained vanilla portless sea exceptions are unchanged.

The first candidate has no sacred-centre opportunity. A bounded planning pass
selected peoples roll **3** on the same geography for the epoch reference, with
every story/formable family offered. The reference code is `RNW1-0826C-SYW6B-MW73Y-C0060-40813-G1WRH-5V`, with **815** non-metadata
files and digest `839515dcf5f91705d53061444512d318125f86eea1cde9f77887bc41c577b5e0`.
No test was relaxed and no additional probe mod was written. A superseded fresh-reference run was stopped before its known
coverage failure; it was not counted as a pass.

[V-EXEC C292] Fresh, no-cache reproduction under `PYTHONHASHSEED=7` passes the
unchanged all-family assertion and exact reference digest (**160.12 s**). The
reference and installed candidate have **651 identical map/graphics files**; their
peoples differ. Twelve additional read-only local installation tests pass
(**47.76 s**). The installed main package's source files match the final working
tree, and its metadata and embedded version agree.

## The four owner worlds

[V-EXEC] Read-only metadata inspection finds the same seed
`11974904842465254760` in all four 0.12.1 worlds. [INFERRED] Shared seed explains
part of their similar outlines across presets; it does not excuse the forced
channel. Running their exact geography parameters through the new land stage
(no world export, installation or replacement) gives:

| Preset | Land-contact rows at the wrap | Crossing landmass pixels |
| --- | ---: | ---: |
| islands | 60 | 6,921 |
| archipelago | 537 | 2,298,689 |
| small_continents | 138 | 343,131 |
| supercontinent | 1,392 | 27,440,633 |

All four have a continuous landmass crossing the display seam in the generated
land field; the previous channel made this impossible. These are offline land-stage
results, separate from the fully exported reference and candidate above.

## Installed update

[V-EXEC C291] The main `mod/rnw_exp_hub` is now **0.12.2**, all **3,254** files
verified against the prepared package. Its previous 0.12.1 contents are backed
up and checked outside the profile in
`local_data/wrap-continuity/hub-backup-before-0.12.2/`. The installed Windows
self-test passes; the new wrapped-distance/road sample bytes match Linux.

Added exactly one world folder, `mod/rnw_exp_wrap_continuity`, **RNW: Small
continents SEOH**, with **815** checked files including metadata. All nine
profile-root hashes, 6,442 other-mod file sizes/times and six pre-existing folders
are preserved. No world is replaced, no playset is edited, and no game is launched.
Removal with the game closed: `uv run rnw uninstall-mod rnw_exp_wrap_continuity
--user-dir USER_DIR`. Main-generator removal, only if wanted: `uv run rnw
uninstall-mod rnw_exp_hub --user-dir USER_DIR`. Both commands name only the exact
folder; the local staged files and backup remain outside the profile.
