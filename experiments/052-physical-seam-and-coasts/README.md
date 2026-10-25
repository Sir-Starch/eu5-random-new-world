# 052 — Physical terrain seam and comb-shaped coasts

2026-10-25; generator 0.12.3, epoch 33. Target: EU5 1.4.4 executable (build
26142040), 1.4.3 data (26105915), unchanged map contract. No game launch.

## Owner evidence

[V-GAME owner C293] Four screenshots show a physical seam and repeated straight
teeth on coasts. [V-LOCAL] The session mounts **RNW: Supercontinent 5WCY**, generator
0.12.2, code `RNW1-081WG-1HAWD-H0XFH-T0060-40830-3C082-243AG-0D43G-ER`.
The screenshots, logs and binary/raster audits remain under ignored
`local_data/physical-seam/`, never in source control.

## Fixes and evidence boundaries

[V-EXEC C294] Value-noise interpolation uses 16-bit rather than 8-bit fractions.
The 3,600-pixel octave previously advanced in roughly fourteen-pixel steps, turning
thresholded coasts into a comb. The controlled 1,599-step slice changes from 1,486
flat steps / largest jump 195 to zero flat steps / largest jump 11. Tests constrain
the derivative at periods 1,600, 3,600 and 4,096, in addition to native/reference,
strip and cross-platform equality. The field is corrected before coast extraction.

[V-LOCAL/V-EXEC C295] Vanilla's decal test covers [0,1). Original placements omit
the x=65,536 world boundary and outside halo samples. Eight periodic placements
reuse first/last-column textures, shifted by ±65,536; matching cache and instance
records supply periodic sources and leave interior coverage unchanged. No binary
layout, texture framing, shader or engine change. Synthetic contract tests fail
on the original uncovered endpoint and check exact modulo-world source coordinates,
unique interior coverage and refusal of changed/missing source geometry.

[UNKNOWN] Whether the engine admits the outside placements and removes the visual
crack. Read-only static inspection did not settle CPU mesh extents or admission.
This is a candidate backed by data-interface tests, not a claimed in-game result.
The prior decoded-image tests alone were insufficient. No manual sitting is
requested, and no existing world is patched.

## Release verification

The exact observed seed, supercontinent shape, location density and empire setting
are retained for the new reference. A bounded planning pass selects peoples roll
0 (seven holy sites and every story/formable family) without changing those
parameters or writing a probe mod. Full export, reproducibility and installation
results follow.


[V-EXEC C296] Locked sync and the complete project check pass: **1,888 Python
tests**, 14 skips, **23 Rust tests**, clean formatting/lint/types. The reference
code is `RNW1-081WG-1HAWD-H0XFH-T0060-60840-3C082-243AG-0C700-KHRXR`:
**824 non-metadata files**, digest
`883e1abf7c211cdcefe2e6b822b1d56fcb5c3078ef23f13959094477197a0e7b`.
A fresh no-cache reproduction passes the unchanged all-family assertion and exact
digest in **194.02 s**; twelve other local read-only checks pass in **71.53 s**.
Windows and Linux match on noise and both synthetic bundle goldens.

Independent written-file audit verifies every manifest hash, all **21,728** Old
World hierarchy records and **66,634,570** protected pixels, 57 changed/new closed
water identities with one component each, port access and retained contacts.
The written cache has **16 original and 8 periodic** heightmap placements. All
**40,960** checked boundary/interior/halo positions resolve to the correct source
with no interior overlap. The world has **1,209** seam land-contact rows; decoded
edge heights on land are nonzero (minimum sampled 5,292, a shore-edge sample).
Source textures absent from the mod correctly resolve through the installation.

## Installed candidate

[V-EXEC C296] Updated the main `mod/rnw_exp_hub` **0.12.2 → 0.12.3**: all **3,254**
files match the final package, and all Python sources match the working tree.
The prior 3,254 files have a checked backup outside the profile at
`local_data/physical-seam/hub-backup-before-0.12.3/`. Installed Windows offscreen
self-test and the new noise-precision sample pass.

Added only `mod/rnw_exp_physical_seam`, **RNW: Supercontinent MKEA**, **826** files
including metadata, all checked. Nine profile-root hashes, 4,052 other-mod file
size/time records and the three previous folders are preserved. In particular,
the owner's active `rnw_exp_world_5wcymogcdr` is not patched. The hub contains no
game content; changing it and adding a new world does not rewrite mounted map
assets. No playset, save, library record, game installation or process is changed.

Exact removal, with EU5 closed: `uv run rnw uninstall-mod rnw_exp_physical_seam
--user-dir USER_DIR`. Main-generator removal, only if wanted: `uv run rnw
uninstall-mod rnw_exp_hub --user-dir USER_DIR`. Backups and staged candidates remain
outside the profile. [UNKNOWN] The new candidate's physical seam in the engine;
no game launch or manual sitting was requested or performed.
