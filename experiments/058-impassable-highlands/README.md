# TR46 — Impassable locations and mountain relief

2026-10-25. Generator **0.12.8**, algorithm epoch **38**. Follows
[057](../057-local-sea-routes/README.md); addresses TR46-01/02 in the
[observer audit](../../docs/research/tr46-observer-audit.md). Evidence C321–C324.
No EU5 launch, game-installation edit, shader change or manual-test request.

## Diagnosis and vanilla comparison

[V-LOCAL / V-EXEC C321] Current installation remains the 1.4.4 executable
(Steam 26142040) on 1.4.3 data (26105915), map fingerprint
`592e8309b7ed9bef1cc0df3eaccd798896d75cd3c3d7ecf9ed525bb6aca3009a`.
The exact TR46 physical model contains **668** impassable cells in **10**
connected land components; their cell counts are 252, 178, 110, 90, 23, 10,
2, 1, 1, 1. They were retained as individual locations irrespective of size.

[V-LOCAL / V-EXEC C321] Vanilla does not merge all impassable land globally.
Among 1,364 impassable locations outside the American continent hierarchy,
the contact graph has 1,180 components; 93 adjacent pairs share climate,
vegetation and topography, while 129 pairs differ. These are location-graph
counts, not an assertion that every vanilla location is one raster component.
Siberian examples already occupy hundreds of thousands of location pixels:
`siberian_forests_2` 353,562, `siberian_wasteland_13` 329,790,
`siberian_hills_8` 249,317 and `omchikan_range` 248,305. Their attributes
also differ. The exact algorithm Paradox used to draw these units is unknown.

[INFERRED C321] Large connected generated units, bounded by biome differences,
address the reported fragmentation without introducing one universal wasteland.
The conservative compatibility rule is a generator decision supported by these
examples, not a claim to have recovered vanilla's authoring algorithm.

[V-LOCAL / V-EXEC C321] The primary heightmap is not the complete vanilla
mountain surface. The installed cache contains 1,741 `mountain_01`, 670
`mountain_02` and 1,295 `mountain_03` placements, in addition to jagged mountains
and volcanoes. Their locally decoded height sources are 1,024 square, with
peaks near 65,535; median strengths are 0.24, 0.20 and 0.23. Median horizontal
scales are 0.20, 0.30 and 0.25. The installed shader's additive mode adds the
transformed stamp height to the base. RNW disabled the former American
placements, but supplied no corresponding fine eroded mountain shapes.

[V-EXEC C321] TR46's physical wasteland height median is 15,661, 90th percentile
23,909 and maximum 38,446. The installed primary height alone at non-American
mountain/mountain-wasteland pixels has median 16,754, 90th percentile 32,162
and maximum 43,017. These cohorts differ and the latter excludes extra mountain
stamps; neither is a measurement of the final game surface or camera scale.
[INFERRED] Missing stamp detail explains a concrete visual discrepancy;
fragmented location identities cannot explain the underlying field's height.
The owner's complete runtime symptom may have additional causes.

## Construction

[V-EXEC C322] `wastelands.location_units` contracts touching impassable physical
cells only when climate, vegetation, topography and resource attributes match.
Every other cell is its own unit. Union roots and ties are deterministic; unit
centres are weighted by pixel area. No size quota, proximity merge across gaps,
new land, coastline edit or retained Old World identity is involved.

`eu5_newworld` partitions this contracted graph before assigning administrative
parents, expands its members for checks on the original contact graph, and gives
each impassable unit one identity. A province, area or region cannot split it.
The physical samples still drive biomes, drainage, terrain and native geography;
they are not replaced by one mean elevation. Compatibility prevents a shared
location from concealing a different biome template. Connected units may cross
the display seam; geography still uses the continuous rolled crop.

[V-EXEC C322] `eu5_mountains` reads the three mountain height sources from the
player's installation and plans overlapping detail on elevated land. A 32-location-
pixel lattice has seed-drawn jitter, 56–72-pixel footprints and eight integer
rotations. Strength is 0.20, inside the measured vanilla range. The sampler uses
integer bilinear interpolation and a short edge fade. Overlapping contributions
take their maximum rather than accumulate into a raised plateau; this is our
construction rule, not a byte-exact simulation of vanilla's decal stack.

The primary height-band constructor samples these shapes in the same continuous
coordinates as relief and detail noise. Gain rises from zero at 14,000 height
units to full at 20,000. River pixels receive zero added height, with a six-
location-pixel transition around them. Outside-canvas and low/coastal samples
receive none. The same sampling supplies opposite-edge source padding. An
out-of-range height or changed source dimensions fails loudly.

This is initial terrain synthesis into the existing primary sources, before
serialization, not a pass repairing an exported map. It avoids new outside-only
placements and adds no engine/shader override or companion mod. The working-set
allowance grows from 600 to 800 bytes per location pixel of a band; allocation
still adapts to available memory. The three decoded source images add about
6 MiB. No new whole-map raster or binary layout is introduced.

## Evidence and remaining limits

[V-EXEC C323] Exact TR46 seed/settings produce **RNW: Continents LSI3**, code:

```text
RNW1-040XN-DR20S-1RQ4T-Z0060-G00F6-A2G
```

The 833-file nonmetadata digest is
`69cafca4b98adfcfaa8fd0fec8ea352be9ce0a6fb851ab5c9dbfdf77df1b6392`.
The 668 physical impassable cells now form **88 compatible locations**; the
largest contains 154 samples and 426,155 pixels. Different biome boundaries and
separate land components remain separate.

[V-EXEC C323] A 512-square location-pixel crop, shown at identical illumination,
height colour scale and vertical exaggeration before/after, has median primary
height 16,094 → 17,515, 99th percentile 18,167 → 23,236 and maximum
19,087 → 28,238. Of its 1,048,576 source samples, 929,913 rise and none fall;
maximum addition is 9,714. The locally rendered comparison shows sharper eroded
crests following the existing highland field. It is a height-source visualization,
not an EU5 screenshot or proof of engine appearance.

[V-EXEC / INFERRED C323] Administrative repartitioning changes regional-family
features used by the existing native homeland matching. Culture/religion labels,
local names and dependent setup can therefore change in this new epoch. This is
not a civilization-balance fix or an isolated before/after trial of native AI.
The unmodified `eu5_natives` also places small diaspora groups; their distribution
must be audited separately from the main physical population model. Older world
mods and saves remain the references for the original observer campaign.

[V-EXEC C323] Independent written-file verification checks all **570,425,344**
level-zero primary height samples (padding included): **12,103,913** increase,
none decrease, maximum addition **13,099**, maximum final height **52,690**.
Outside the generated domain, at river pixels and below the gain threshold,
samples remain exact. All opposite-edge padding matches its corresponding
in-world source. Material layers, water textures, placement/cache files and
`rivers.png` remain byte-identical to BU2A.

All **88** final wasteland identities are independently raster-connected after
restoring continuous crop coordinates, and every merged member has its original
biome attributes. **87,396,814** retained-identity RGB pixels remain exact;
**108,823,408** land/lake/retained identity pixels keep their semantic keys.
The physical class raster is identical everywhere. All **59,404** road paths
retain coordinates by location key despite definition renumbering. All **861**
bundle entries hash correctly; **76** nonmetadata files change, with no added or
removed mod paths. The exporter retains all Old World contacts and finds no
unreachable generated seas or land without port access.

All **16,399** nonempty population records with retained keys are byte-exact.
For the **23,055** nonempty records in all, the only differences are generated
culture/religion assignments and the existing small diaspora rows (size 0.050).
**1,228** records change; **151** have changes in those additional rows beyond
label replacement. The main physical population total stays 45,197,553 milli-
units, with 202 states, 457 tribes, two great empires and 3,218 held locations.
Matching now uses 253 rather than 267 main culture identities and 51 rather than
53 religions; placed holy sites change 10 → 7. Country text and dependent
content also change; they are not claimed identical except for discovery lists.
No change to the native algorithm or AI policy is made here.

The final full check passes **1,951 Python tests**, skips 14 and fails **18**
pre-existing Workshop-description tests from the separate committed revision
`0735263` (ten stale source fingerprints and eight descriptions above Steam's
byte limit). Those files and tests are unchanged by this phase. Format, lint
and types pass; the Rust checks separately pass **23** tests. The complete
`make check` is therefore **not green**, and no contrary claim is made. The
Workshop text problem is recorded rather than folded into this map work.

The reference has 832 nonmetadata files, all story/formable families, digest
`711a0e0296b0118baf81b8cea447e00e018fd864aa5ff5da7857ffdb61c88800`, code
`RNW1-081WG-1HAWD-H0XFH-T0060-G0840-3C082-243AG-0C700-EE2Z0`.
Fresh no-cache/hash-seed-7 reproduction passes 13 local checks, one skip, in
248.40 seconds. Windows/Linux four-case sampling and unit-graph parity has digest
`8aa077f590792652716b22cc4690f337bd136f4c2d845da11ca5b2c6ae942da1`;
the final isolated offscreen Windows generator self-test also passes.

[UNKNOWN] Engine appearance of the enlarged locations, final mountain rendering
and the owner's visual comparison at the same camera settings remain unobserved.
TR46-02 is not closed by the grouping check. No new owner sitting is requested.
Native expansion (TR46-05) is a separate next investigation.

## Local evidence

Ignored `local_data/tr46-highlands/` holds the diagnosis, decoded crop comparison,
independent written-file audit, complete check output, reference reproduction,
Windows parity/build/self-test and installation records. Generated assets remain
under `generated/rnw_exp_tr46_highlands/` and `generated/rnw_exp_highlands_reference/`.
No logs, screenshots, derived rasters or proprietary height sources enter Git.

## Installed candidate

[V-EXEC / V-LOCAL C324] With log and live-process checks agreeing EU5 is closed,
installed new `mod/rnw_exp_tr46_highlands`, **LSI3**, all **835** files checked.
Updated main generator **0.12.7 → 0.12.8**, all **3,262** files checked against
its source, wheel, locked dependencies and metadata. The wheel digest is
`c336a7a4082fd2f72a394e497b76ad99493aaf020a5b647f4003da42b69e1a58`.
The old 3,258-file generator is checked in external
`local_data/tr46-highlands/hub-backup-before-0.12.8/` and retained at
`mod/.rnw-install/retired/rnw_exp_hub_before_highlands_0128/`; no retired sweep.
Nine profile-root hashes, 20,405 other-mod file size/time records and eight prior
mod-directory entries are preserved. No old world, save, playset, setting or
library record is altered; no launch, process control, push or publication.
Removal, with EU5 closed: remove only `mod/rnw_exp_tr46_highlands/`. Hub rollback
is separate; no rollback/removal was performed.
