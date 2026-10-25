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
interoperability R-005. No game launch, source/output/version/epoch/install/
profile/save/settings/playset change, process control, push or publication.
LSI3 and hub 0.12.8 remain installed; no new owner test is requested.

Required locked sync/full checks: **1,969 Python pass, 14 skip, 23 Rust**,
format/lint/types clean. Private check SHA-256:
`1c783df9697a439f48403fc83775e0d4631d043df5eec022b40c767d7e3c7023`.
