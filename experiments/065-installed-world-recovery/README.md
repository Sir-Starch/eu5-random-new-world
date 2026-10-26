# 065 — Automatic recognition and recovery of installed worlds

2026-10-26. Generator **0.13.3**, algorithm epoch **41**. Application work,
synthetic tests and a local copy of the generator's EVXP world. No EU5 launch
or manual sitting. Claims C354–C356 in the
[ledger](../../docs/research/claims-ledger.md).

## Requirement and cause

[V-LOCAL owner screenshot / V-EXEC C353–C354] The directly installed EVXP
candidate appeared as “Older world” because the application required its separate
library `world.json`. It detected the mod but did not use its readable world
code to restore a record. The owner requested automatic recognition as basic
functionality. C353 records the immediate registration of EVXP; this phase makes
that behaviour automatic for other installed RNW worlds.

## Behaviour

[V-EXEC C354] `app/recovery.py` recognizes valid world codes from installed mod
metadata, or restores the self-description emitted with new application-generated
mods. Discovery writes the library only: it never renames installed mod folders,
changes mod files, or edits playsets. A validated `World.mod_folder` alias binds
manual exports in place. Code/build checks prevent an identically named folder
in another profile from binding or deleting a different world. Imported world
files discard local aliases; built transfers normalize the metadata id and
manifest paths in their private extracted copy.

A metadata-only legacy adoption has its code, type, seed, generator version,
title and, if present, thumbnail. Its original game build and reproducibility
record remain unknown. A thumbnail is not a restored atlas. Mods without a
readable code or supported receipt remain visible as **Unregistered world**,
with their files intact; the interface no longer asserts that they are old.
All revised wording is translated into the installed game's official languages.

New application-generated mods carry `.metadata/rnw-library/world.json` and
existing bundle assets: atlas, previews, input/output manifests, settings/report,
optional drawn-land image and saved country-selection cover. Private notes,
favourites and user tags are omitted. Restoration checks the code/settings,
record, input/output digests, library asset hashes, atlas and pictures in staging.
Publication into the library is atomic. A copied mod can arrive metadata first:
its partial entry is upgraded when valid receipt assets finish arriving, while
preserving its id, custom name, notes and favourites. Failed validation leaves
the prior entry intact; unrelated library files are not overwritten.

The visible Qt window checks small metadata/library-file stat changes every two
seconds. An unchanged poll does not reload or redraw; busy generation skips
polling. New entries appear without restarting the window, selection survives,
and unsaved notes are retained. No whole-map hash pass runs on the UI thread.

## Verification

[V-EXEC C355] Required locked sync and full check pass **1,999 Python tests**,
**14 skips**, **23 Rust tests**, format/lint/types clean. Regressions cover
metadata-only adoption, receipt recovery after library loss, repeat discovery,
bad code, symlinks, atomic failure, delayed/incomplete assets, preserved personal
fields, folder aliases across profiles, correct removal and built transfers.
A real offscreen Qt window automatically discovers an external mod and keeps
selection plus unsaved notes when a second one arrives.

An ignored copy of the existing EVXP world restores its code, exact record,
build, previews and atlas of **6,910 locations**. All **818 nonmetadata mod
files** stay byte-identical. Its **29-file** recovery bundle passes the original
input/output and library-asset integrity checks. The canonical output digest
remains `cc1ba4e7fe06c9cf11a15c5a6831057eb3e9671fbc71f8e3ee7b8d86fcac24ec`.
The restored card was rendered and visually inspected; raw map/preview evidence
stays ignored under `local_data/world-recovery/`.

The packaged Windows generator passes its offscreen window/native/world-code
self-test. Linux and Windows metadata/receipt recovery have identical digest
`46f37475c80f9ffc854eeb7b01abd363f5cab06a75cab70aeca7662a1f3bfd55`.
No geographical algorithm or nonmetadata world file changes. Epoch 41 and
`tests/golden_world.json` remain those of 0.13.2; no new full-world generation
was needed.

[UNKNOWN] Running-game handling of the additional metadata payload has not
been observed in this phase. No engine behaviour, save compatibility or new
patch compatibility is inferred from these application tests. No game sitting
is requested. Installation is recorded in [INSTALLED](../INSTALLED.md).

## Delivery

[V-EXEC C356] Updated the generator-only hub **0.13.2→0.13.3**, verified
**3,266** installed files against the final Windows package, and checked all
source/catalog bytes against the working tree. The first staging guard caught
a concurrently saved maps-panel change before any profile write; the package
was rebuilt and retested with that change included. The prior **3,264-file**
hub has verified external and retired backups; no retired-folder sweep.

The immediate pre-install snapshot had **one library record**, **820 other-mod
files** (EVXP) and **nine profile-root files**; all remain exact through this
installation. Counts describe that snapshot, not earlier user activity. A later
read-only check of the generator's own log sees a native **0.13.3** generation
complete independently and verifies its **29-file** receipt against its library
record. No world was generated, removed or edited by the hub update itself.
No game launch, process control, playset/save/settings change, push or publication.

Ignored evidence: `local_data/world-recovery/` (`check.log`, Qt render, actual
receipt round trip, Linux/Windows parity, final package build/test logs,
`installed.json`, source-guard log and verified old-hub backup). Source changes
are in local commit `434df83`; the algorithm reference remains unchanged.

## EVXP preview correction in the Windows library

[V-EXEC C357] The owner's subsequent screenshot shows a square EVXP preview
beside four wide previews. The installed 0.13.2 EVXP mod has no recovery
receipt. Windows 0.13.3 adopted it through `_legacy` / `_restore`, copying
`.metadata/thumbnail.png` into both library preview files. All three 512×512
files have SHA-256 `3c1e861c…c46336`. The main viewer displays an already cropped
source; zoom is not the cause. The prior reply attributing the crop to zoom
was unsupported and incorrect.

The original full previews remain in the Linux library and direct export:
2048×1024, revealed SHA-256 `c37fb418…8ad0`, hidden `50b34c4c…14362`.
C355's successful recovery used a receipt added to a temporary copy; it did
not establish that the existing installed EVXP carried that receipt. This
explains why the generator opened through the game had incomplete data while
the native library had the full bundle. The world's older generator version
does not require cropping its preview.

Restored the Windows library entry from the verified original bundle, retaining
its id, installed-folder alias, name, visibility and personal fields. All 29
staged/installed files match; record/manifests pass recovery checks and the
atlas contains 6,910 locations. Both full previews were checked and the revealed
image was visually inspected. The three previous files are backed up in ignored
`local_data/evxp-preview-restoration/original-library-entry/` and retained at
`generated/.rnw-evxp-preview-before-restoration` in the Windows library. Four
other records, 7,491 installed mod-file size/time records, nine profile-root
hashes, preferences and the source Linux bundle remain exact.

This is a library-data repair: no source/package, mod file, product version or
algorithm change. Legacy thumbnail substitution in 0.13.3 remains a known
limitation; this correction does not claim a general implementation fix. The
open viewer caches its loaded pixmap until another world is selected. No game
launch or process control. Ignored audit: `local_data/evxp-preview-restoration/`.
