# 064 — Complete ocean course ends (657Q)

2026-10-26. Generator **0.13.2**, algorithm epoch **41**. Offline work only;
no EU5 launch or request for a manual sitting. C349–C352 in the
[claims ledger](../../docs/research/claims-ledger.md).

## Diagnosis

[V-GAME owner, EU5 1.4.4 / generator 0.13.1] The owner's 657Q screenshot
shows a narrow current lane interrupted by impassable ocean beside
**Ruaziasleir Coast**, with a deep dead end rather than a continuous passage.

[V-LOCAL / V-EXEC C349] The installed world's metadata supplies its exact
supercontinent seed **9781797494467218106**, settings and code:
`RNW1-081RF-FZCZT-X8CJN-T006G-20860-2AG63-YG1W8-8G3GH-149XR-08TM0-31K40-C`.
Read-only build resolution still returns executable 1.4.4 / Steam 26142040 on
1.4.3 data, fingerprint
`592e8309b7ed9bef1cc0df3eaccd798896d75cd3c3d7ecf9ed525bb6aca3009a`.
Rebuilding the pre-fold physical graph reproduces **154 lanes**, **44 closed
zones** and four deep tips, cells **6627, 7029, 7303, 7350**. Every reconstructed
sea cell's final topography matches the installed templates when mapped through
the written location raster. Pre-fold topography must not be compared directly:
folding closed zones changes the subsequent physical analysis of six cells.

The screenshot's displayed name includes `rnw_sea_00875`, the tip at cell 7350.
Cell 7303 (`rnw_sea_00849`) and 7350 both border closed cell **7338**, whose
inherited-course coverage is **480 permille**, below the 500-permille lane
threshold. It is folded into the much larger `rnw_sea_00127` impassable ocean.
Both lane fragments already reach retained water; `_join` therefore has no
unreachable component to connect. They are also outside the local coastal-pair
criterion. The two other tips are incomplete inherited courses in the changed
geography; their exact visual identity in the screenshot is not claimed.

## Construction and checks

[V-EXEC C350] Before closed water is folded, `sea_routes.complete_routes`
continues deep tips to existing navigable water. It excludes the incoming stem
and its junction, prefers the forward 45-degree cone, uses integer water-only
shortest paths, and stops at the first existing water. Land-blocked headings
turn towards the nearest reachable destination; no reachable destination raises
`LaneError`. Each iteration adds closed cells and cannot remove existing lanes
or produce a new tip. No output patch, engine change or companion mod is used.
`verify_seas` independently rejects deep tips away from coastal/retained water,
even if their component is globally reachable.

657Q opens eleven cells: **6624, 6636, 6660, 6689, 6978, 6982, 6984, 7014,
7016, 7020, 7338**. It has **165 lanes**, **47 connected closed zones** and
zero deep tips. A lane can divide a closed ocean, so the increase in closed
component count is expected. Land is never opened as water. Synthetic regressions
cover a gap with both shores globally reachable, continuation beyond an old
course end, a legitimate coastal endpoint, blocked forward water, terminal
stopping and no reachable destination. The two crossing regressions fail when
completion is disabled.

[V-EXEC C351] Full checks pass **1,987 Python tests**, **14 skips**, **23 Rust
tests**, formatting, lint and types. The Windows offscreen generator self-test
passes, and four Linux/Windows lane-planning cases have identical digest
`125b3d0ba844a32480753b6803e452e4b25f374c3f77997bf57d09d7555d0b75`.
The epoch-41 reference retains every story/formable family and hashes **837**
nonmetadata files to
`667a51aa3379cf9016c88e8bb6330b01da81aac4de72fe7d0ef97cf5f747386e`.
The optional installed-game suite passes **12 checks**, with its two explicitly
opt-in reproduction/layer tests skipped; both full exports above ran separately.

Independent read-back of the exported 657Q raster and templates finds the same
four old tips and zero new tips. All **51,341,116 nonsea pixels** keep their
location identity; **30,434,666 retained nonsea RGB pixels**, all **558 terrain2
files**, the river raster, all **54,773 road strips** by semantic endpoints and
coordinates, and all **21,525 populated location records** stay exact. All
**866 canonical bundle entries** pass their hashes. The canonical covered mod
has **838 nonmetadata files**, digest
`cc1ba4e7fe06c9cf11a15c5a6831057eb3e9671fbc71f8e3ee7b8d86fcac24ec`.

The installation follows the owner's existing revealed-world preference through
the application's normal presentation writer. Its **818 nonmetadata files**
hash to `2b9d21108311b1aa441313e63a7e093a94a32ce36115a7dab767c9c4cb60d196`.
The cover's twenty files are absent as in the original 657Q; no new interface or
shader file is introduced into that installed world. Presentation does not
change the geography or the canonical reference record. The new world is
**RNW: Supercontinent EVXP** (`rnw_exp_657q_lanes`), seed/settings retained,
new version code
`RNW1-081RF-FZCZT-X8CJN-T006G-40860-2AG63-YG1W8-8G3GH-149XR-08TM0-33AGE-Y`.

Ignored evidence stays under `local_data/657q-lanes/`: original and final
physical graphs, course/topography audit, build/test logs and complete export
reports. Installation and exact removal are recorded in
[INSTALLED](../INSTALLED.md). The original world and campaign remain intact.
Written-data correctness is separate from an observed engine movement result;
the latter remains **UNKNOWN**.

## Library registration correction (2026-10-26)

[V-LOCAL owner screenshot / V-EXEC C353] EVXP appeared as “Older world” because
its direct export was installed without a library record. This is an installation
integration omission, not an old generator. Registered its existing bundle in
the active library under standard id `rbsvu4fogp`, preserving display name
**Supercontinent EVXP**, full atlas (6,910 locations), previews, code and epoch-41
record. The unreferenced installed folder moved from `rnw_exp_657q_lanes` to
`rnw_exp_world_rbsvu4fogp`; only `.metadata/metadata.json` changed (its id).
All 820 files checked; 7 existing library records, 4,903 other-mod size/time
records and 9 profile-root hashes preserved. No regeneration, map/save/playset
change or game launch. The library now has eight worlds, EVXP is `IN_GAME`,
and no unregistered worlds remain. Version and epoch stay 0.13.2 / 41.
Ignored audit: `local_data/657q-library/registered.json`.
