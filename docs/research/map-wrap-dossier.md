# World-wrap terrain fissure and river discontinuity

Working evidence dossier for a possible Paradox bug report. **2026-10-28**.
No report has been submitted. New crack investigations, comparisons and results belong
here; earlier experiment records remain historical evidence, linked rather than copied.
Agent-run EU5 tests are prohibited by the owner. Future game comparisons are owner-run.

## Vanilla reproduction and scope (C412)

[V-GAME owner] On EU5 1.4.4 the owner restarted with every mod disabled before
startup, started a vanilla game and still saw the black terrain fissure on
**Kitagnaq**. Two supplied screenshots show the same island at different distances.
The crack also occurs in RNW at country selection and after starting a campaign.
It appears at close terrain zoom in lenses showing physical geography; stepping
back makes it disappear. Textures and trees remain continuous. These observations
separate the crack from a particular generated world or campaign age.

[INFERRED from this reproduction and C413] Treat this as a vanilla rendering
limitation in the tested installation, not evidence of corrupt RNW geography.
The exact engine operation, render-path dependence and hardware scope remain
[UNKNOWN]. File integrity does not identify the renderer's internal cause.
The initial 0.13.18–0.13.19 policy removed the terrain-source extension. The
owner subsequently requested its restoration (C418 below). No engine/shader patch
or artificial strait is introduced; mechanical support remains in place.

[V-GAME owner C58, C345] The owner previously saw the crack disappear. Those
observations remain valid for those sittings. The present vanilla reproduction
does **not** retrospectively invalidate them. What is no longer established is
that one of those changes permanently fixes the engine at every relevant zoom
and setting. Reproducing the earlier disappearance is planned below.

The three latest owner attachments are retained only under ignored
`local_data/quxq-wrap/audit/owner-*.png`; the earlier QUXQ images and offline
measurements are under `local_data/quxq-wrap/`. Game assets, logs, executable
excerpts and screenshots are not committed.

## Installation integrity (C413)

[V-EXEC] A read-only comparison checked **55,370 files / 13,915,597,647 bytes**
against the cached Steam manifests named by `appmanifest_3450310.acf`, build
**26142040**. Content SHA-1 and sizes match; no missing, changed or extra files.
Twenty Windows filename case differences were resolved without changing a file;
fifteen zero-length placeholders have Steam's zero digest and are actually empty.
This is a local manifest comparison, not a Steam client repair or a new download.

| Depot | Installed manifest | Manifest SHA-256 |
|---|---|---|
| 3450311 | 2022712378228074636 | `ffea14e41a850b7207770ac97e4e36d8bf86ed1bc5340f938987311c7631a1c7` |
| 3450312 | 2485611827423162497 | `f9010d4cf04f378a327485d8db60584e112b6ff46faaadbc5106df995f051c26` |
| 3450313 | 4102298837448582430 | `74616a2973cf4644862311deea2691145100db9d1b51f53844410c1798fcc8b8` |

The 1.4.4 executable on fingerprinted 1.4.3 map data remains the known target:
map fingerprint `592e8309b7ed9bef1cc0df3eaccd798896d75cd3c3d7ecf9ed525bb6aca3009a`.
No game installation file was written. Audit and independent comparison script:
ignored `local_data/quxq-wrap/audit/integrity.{py,json}`.

## Nine QUXQ locator warnings (C414)

[V-LOCAL / V-EXEC] The nine C411 messages concern **three locations**, not nine.
Every warned locator lies on a pixel of its own identity in the installed
`locations.png`. Each identity continues across the map edge. Expressing its
compact horizontal box across x=0 gives these half-open bounds:

| Identity | Pixels | Compact x box | Locator x | Logged distance |
|---|---:|---|---:|---:|
| `rnw_loc_00821` | 2,682 | [-36, 39) | 16372.5 | 16333.5 |
| `rnw_loc_00873` | 3,052 | [-39, 47) | 16378.5 | 16331.5 |
| `rnw_sea_00398` | 317,264 | [-408, 742) | 16290.5 | 15548.5 |

City, combat, unit-stack and VFX share the first two coordinates; the third
message is VFX only. In each case **locator x minus the compact box's upper
boundary exactly equals the logged distance**. Subtracting the map width,
16,384, from the locator instead puts it inside the box, as the raster does.

[INFERRED] This strongly supports a bounding-box diagnostic comparing two
coordinate representations without wrap normalization. It does not establish
every implementation detail of that diagnostic, or prove every game system
handles those objects correctly [UNKNOWN]. There is no evidence here of a
misplaced locator, and no reason to disable expansion solely for these warnings.
Do not suppress the warnings or move correct anchors just to silence them.
Measurements: ignored `local_data/quxq-wrap/audit/locators.{py,json}`.
The two retained-vanilla ocean warnings remain outside this attribution.

## Rivers: a separate content and engine contract (C415)

[V-GAME owner] The Rivers lens shows the same RNW gaps as the terrain view.
Thus a visual bridge alone would not establish a connected gameplay river.
The owner reports no vanilla river crossing the display edge. [V-LOCAL C390]
The installed vanilla river raster contains no channel pixels in either outer column.

[V-EXEC] In 0.13.17–0.13.18, `eu5_rivers.encode_rivers` intentionally omitted
last-column channel pixels and gave the planar fragments independent sources. The QUXQ reference
reports **5 cut networks, 29 fragments and 56 omitted boundary pixels**, while
valley carving uses the original continuous physical network. This directly
explains a content-side discontinuity and why valleys need not match the game's
separate river identities. It does not prove that it alone explains the full
visible fade length or the terrain fissure.

[V-LOCAL executable C309/C390] Earlier bounded inspection found different
boundary behavior in the river walker and leftover-component discovery; merely
restoring edge pixels is not a verified fix. Those findings retain their narrow
interoperability value ([R-004](interoperability.md)). No supported data interface
joining a complete cross-edge river has been established [UNKNOWN].

### Approved watershed policy, 0.13.19 / epoch 56 (C417)

[OWNER, 2026-10-28] Retain the expanded canvas, mainland crossings and continuous
location identities. Treat the seam as a watershed boundary, generate flow on each
side independently and require actual water outlets. Do not truncate channels on
land or create artificial mouths on the seam. This replaces the pending proposal.

[V-EXEC] The exporter now plans each side as a separate closed drainage domain.
Each gets its own coarse relief/rain grid, deterministic noise stream, catchment
accumulation and river-density threshold. Rain is sampled at each domain's actual
world coordinates, including divides not aligned to the coarse grid. The native
priority flood seeds only genuine water inside that domain; the outside border
is closed, never water. A domain with no coarse water outlet fails explicitly.

The first and last world raster columns are reserved **before generation**, as
required by the existing river-walker contract. This is a channel-domain constraint,
not a cut through an existing river: land, water and uncarved relief are unchanged.
No mountain ridge or strait is inserted. Drawing writes directly into disjoint views
of shared role/flow buffers, retaining bounded working memory without an additional
whole-map merge. Valleys and final codes consume that same planned network.

The former fragment cutting and source/join reorientation are removed. The
serializer preserves every channel pixel and fails if one occupies the closed
boundary. A separate validator follows each main line from its source, excluding
incoming tributary joins, and requires its terminal to be in or beside **actual
water on its own side**. A wet tributary cannot excuse a dry main-line end.

[V-EXEC] Synthetic tests cover 24 seed/divide combinations, partial coarse cells,
divides at crop ends and outside it, independent changes to the opposite side's
relief and rainfall, rejection of an outlet-free side, and a dry main line with a
wet tributary. Placement tests validate the final world raster without pretending
its edges are water. Linux and Windows agree on role, accumulated flow and palette
bytes for three independent cases. Full checks: **2,107 Python pass / 14 skip;
23 Rust pass**, clean format/lint/types; local installation contract **12 pass /
2 optional long checks skip**. The Windows generator self-test passes.

[V-EXEC] Independent read-back of the written reference finds **328 complete
networks**, all 328 main outlets at real water, **340,898 channel pixels**, **zero
edge channels and zero pixels lost by serialization**. The canonical 835-file
reference digest is
`30f266abefbdae047540bb6ed9329fd00229b403743c6ebe564f2dc6c6ee7586`.
Eleven relevant location, hierarchy, adjacency, locator and spline files match the
previous reference exactly. No route/hang correction or physical land mask was
removed. Installation and exact removal are in [INSTALLED](../../experiments/INSTALLED.md).
Raw candidate, byte-level audit and parity evidence stay under ignored
`local_data/seam-watersheds/`. No EU5 launch or in-game check was performed;
rendering and gameplay acceptance of these new networks remain [UNKNOWN].

## Visual rollback boundary (C416)

[V-EXEC] **0.13.18 / epoch 55** removes the 0.12.6 primary-source extension:
512 location pixels / 1024 source samples at each outer edge, source resizing,
placement shifts and rewritten primary instance files. Primary source dimensions
and placements follow vanilla again. The former outside-only duplicates of
0.12.3 were already replaced in 0.12.6; they are not restored.

Retained: cylindrical land and field sampling, continuous noise, water and coast
support, continuous location/province identities, pathfinding/hang corrections,
road/contact support, rivers' loader-validity rules, and binary header validation.
No engine, shader or game-installation patch is introduced. Existing worlds,
saves and playsets are not rewritten. This is removal of an unneeded visual
workaround; it is not claimed to remove the vanilla crack.

Full offline checks: **2,080 Python tests pass, 14 skip; 23 Rust tests pass**;
format, lint and types clean. The installed-game read-only suite passes 12 tests
with 2 optional long checks skipped; the Windows generator self-test passes.
Independent read-back verifies the 835-file canonical reference digest
`e694e0b479e29280afe1a40d50d3103c49237b932c28eb2306adad6ec44bbbd9`.
All **41 changed/removed paths** are under terrain2 (25 common files changed,
16 removed, none added); everything outside it, including rivers, locations,
roads, setup and water assets, is byte-identical to the previous reference.
All **536,870,912** original level-zero samples of the 16 affected height/material
layers match, and all **16 primary placements** equal vanilla exactly. The
canonical hidden-world reference includes the 20 optional selection-cover files
retained separately for the revealed candidate. Delivery is recorded in
[INSTALLED](../../experiments/INSTALLED.md).

## Visual source extension restored, 0.13.20 / epoch 57 (C418)

[V-GAME owner report] After the visual rollback, the owner reports that the seam
is much more prominent, including at the furthest zoom, and asks to restore the
previous successful visual approach. This is a new observation under the owner's
current conditions, not a reason to discard the earlier zoom-specific vanilla
reproduction or the earlier genuine disappearance. The exact rendering cause
remains unknown.

[OWNER / V-EXEC] Restore the **exact** `eu5_terrain.py` implementation from
`ebec95e` (0.13.17), with its synthetic coverage and source-padding tests. Each of
eight edge sources again has 512 location pixels / 1024 source samples of periodic
support, 9216 × 4096 source dimensions and matching primary/cache placement.
Do not restore the old river cutter, outside-only duplicate placements or a seam
strait. The 0.13.19 independent watersheds, outlet checks, continuous identities
and route/hang corrections remain unchanged.

This is a data-only visual workaround, generated directly from the installed
sources and current physical fields. It does not claim to repair the engine or
establish every zoom/LOD's appearance. Original source interfaces and compatibility
guards remain those documented in [R-004](interoperability.md) and experiment 056.
Raw builds and verification stay under ignored `local_data/wrap-visual-restored/`.

[V-EXEC] Full checks pass: **2,116 Python tests / 14 skips, 23 Rust tests**,
clean formatting/lint/types. The Windows generator self-test passes. Independent
read-back of the 851-file candidate (digest
`de9fa8ae001c436bf3a5b6fb90ea342787069da4c326cdf84e0c8ec8d98e9995`)
finds changes in **41 terrain2 paths only** (25 modified, 16 added). All files
outside terrain2 and all river statistics are exact against 0.13.19, retaining
its 328 genuine outlets and 340,898 channel pixels. All **536,870,912 original
height/material samples** match the unpadded reference, and **67,108,864 halo
samples** match their opposite sources. Eight padded primary placements agree
with their written active instances. Delivery is recorded in
[INSTALLED](../../experiments/INSTALLED.md); this does not establish the restored
candidate's rendered appearance.

The owner-run historical comparison remains useful for the potential report;
restoring the previous technique does not replace that evidence.

## Planned historical comparison, owner-run only

[PLANNED; owner 2026-10-28] Reproduce the earlier **actual disappearance**, rather
than assume it was an observation error. Prepare one bounded comparison sitting;
do not launch the game or ask for another long campaign now.

| Historical source / candidate | Evidence and purpose |
|---|---|
| `80b0a2d` (V1a.1, C58) | Early accepted absence with a seam strait. Distinguish hiding the edge under water from rendering continuous land. |
| `dc24d5d` (0.12.6, experiment 056) | Primary-source padding introduced; offline construction, not itself an owner acceptance. |
| `f2eae15` (0.12.9), acceptance `64a7f0c` / C345 | Accepted QW6O candidate `rnw_exp_tr46_treaty`, code `RNW1-040XN-DR20S-1RQ4T-Z0060-J01KM-KKG`. Preserve this exact installed candidate if present. |
| Current source without visual padding | Same seed/settings and reference coordinates, compared with the accepted candidate's pixels. |

Before the sitting, bind each package to its commit, world code and hashes; retain
historical inputs where available, and label rebuilding against newer game data
as a changed-input comparison. Stage only fresh world-mod folders, preserving
current mods/saves/playsets. First compare written geometry, source dimensions,
materials and shader overrides offline. Do not infer that a whole historical
commit's other changes caused the disappearance.

The owner's game instructions will compare the **same coordinates, maximum and
slightly reduced zoom, physical-geography lens and Rivers lens, country selection
and a paused new game**, recording the exact build, display/render settings and
screenshots. Historical candidates predate the unit-route fix: this comparison
needs no time advancement or troop routing. Do not change global graphics settings
or wipe caches automatically. Hold those conditions fixed first; isolate any
later variation explicitly. Exact rendering cause and the disappearance's
reproducibility stay [UNKNOWN] until that evidence exists.

## Public search and potential report

[SOURCE search, 2026-10-28] Searches for EU5/Europa Universalis V with map seam,
map-edge crack, black line, Alaska/Aleutian islands and Kitagnaq, including Paradox
forum and Steam/Reddit-targeted queries, did not locate a directly matching public
report or documented river-wrap solution. Unrelated graphics reports are not
supporting evidence. This does not establish that no report exists, and does not
supply a developer acknowledgment or promised fix.

A potential forum submission should lead with the **mod-free Kitagnaq reproduction**,
verified installation and exact zoom/lens behavior. Attach the owner's vanilla
screenshots and version/render information. Present RNW river parsing and locator
normalization as separate additional observations, each with its own reproduction
and uncertainty, rather than claim one established root cause for all three.
Publication remains the owner's decision; no account action is authorized here.
