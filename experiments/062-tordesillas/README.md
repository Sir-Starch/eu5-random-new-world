# 062 — TR46 Tordesillas text and saved division line

**2026-10-25.** Read-only follow-up to 053/054, TR46-L05 and TR46-06b.
Original campaign: generator 0.12.3 / epoch 33, EU5 1.4.4 executable / build
26142040 on 1.4.3 data / 26105915. Current generator stays 0.12.8 / epoch 38.

## Result

[V-GAME logs / V-LOCAL / V-EXEC C337] Four original diagnostics at 06:37:42
are one failed localization of `treaty_of_tordesillas.5.c`; debug copies are
mirrors. RNW's full 807-file inventory does not override the event or vanilla
option text; all 55 archived world localization files lack that key. Installed
vanilla uses `overlord` in all 11 official languages, ten with the logged
accessor and Russian with its case-customization accessor. This is a shared
dependency, not eleven observed failures. Mounted-mod attribution remains open.

[V-LOCAL / INFERRED / UNKNOWN C338] The event saves `overlord` only for a
subject, exposes `.c` only for a subject and forwards to the top overlord after
two days; a transfer demand initially schedules it after seven days. It is
also major for the actor. Bare saved scopes occur elsewhere in installed
vanilla; lack of an explicit scope accessor alone is not an established
syntax bug. Missing context could explain the error, but recipient, selected
option, scopes and observer/major rendering are not logged. Neither save's
queued events retains a Tordesillas string. No global text/event patch.

[V-GAME owner / V-EXEC C339] The clarified geography symptom is the **western
continuation of the same mainland**, crossing the seam and drawn at raster
right, counted as Britain's east. Preserve full mainland wrap, as already
chosen. The 1590 save now supplies **SPA west / GBR east**, dates
**1549.10.2–1568.10.22**, and retained line **24717 / `rnw_loc_01224`**;
1497's treaty record is empty. This advances 054's missing-line limit without
recovering the observation-time line, affected location or rendering context.
Two fallback colony rebindings are the only situation-file changes; all map
color/tooltip blocks are identical. Side shading, actual claims and ownership
overrides must remain separate. C305's exact loaded cyclic span is still
unknown; raw raster x and a locator cannot replace the engine evaluation.

Full sources, scope graph, saved values and remaining questions:
[TR46 Tordesillas findings](../../docs/research/tr46-tordesillas.md).

## Verification and installation

[V-EXEC C340] All 37 evidence hashes and 732 copied world hashes pass; both
source saves retain their hashes and pass ZIP CRCs. Prior extraction/structure
manifest hashes pass, no reader token change. Build/executable/map fingerprint
unchanged. Private artifacts and bounded static inspection are registered in
interoperability R-005.

### Generator construction and candidate verification (0.12.9 / epoch 39)

[V-EXEC C341] `eu5_treaty.py` constructs continuous New World dry-land longitude
coordinates on the canvas axis across the raster seam for Tordesillas side
selection, line moves, side-swap estimates, map shading and final province
distribution. Immutable coordinates are exposed via $O(\log(\text{width}))$
vanilla scripted geography bitmasks and script values. Predicates (`is_east_of`)
and distribution iterators (`every_east_of_province_definition` /
`every_west_of_province_definition`) are rewritten with strict count guards.
Vanilla claim gates, religion, ownership, existing claims and province effects
are strictly preserved.

[V-EXEC C342] On TR46 candidate, 1 wrapped mainland crosses the boundary with
164 locations across 30 provinces at raster right (`x >= cut`). Under raw
coordinates (`is_east_of`), all 164 evaluated east of line `rnw_loc_01224`.
Under continuous axis coordinates, all 164 locations and 30 provinces evaluate
west of the line in both triggers and province distribution. All 7,324 dry
generated cells match physical centroids.

[V-EXEC C343] Full test suite: **1,978 Python pass, 14 skip, 23 Rust**, format,
lint and types clean. Golden reference world updated (`RNW1-081WG-1HAWD-H0XFH-T0060-J0840-3C082-243AG-0C700-X3YQR`,
digest `3423df6d…cee01`, 837 files).
Comparing TR46 candidate 0.12.9 (**RNW: Continents QW6O**, 838 mod files, digest
`33ef2ed8…64bd`) against 0.12.8 (RNW: Continents LSI3, 833 files): all 831 other
nonmetadata files are 100% byte-identical; only 5 added treaty files and 2
rewritten situation files differ. Linux/Windows parity matches; Windows offscreen
self-test passes. Runtime engine appearance and treaty events remain unobserved.

[V-EXEC / V-LOCAL C344] With log and live checks confirming EU5 is closed,
installed candidate **RNW: Continents QW6O** in `mod/rnw_exp_tr46_treaty`
(840 files checked) and updated main hub 0.12.8→0.12.9 in `mod/rnw_exp_hub`
(3,264 files checked). The old 3,262-file hub is externally backed up under
ignored `local_data/tr46-treaty-fix/hub-backup-before-0.12.9/` and retained in
`.rnw-install/retired/`. Nine profile-root hashes, 24,498 other-mod size/time
records and nine prior folder entries are preserved. No game launch, process
control, push or publication.
