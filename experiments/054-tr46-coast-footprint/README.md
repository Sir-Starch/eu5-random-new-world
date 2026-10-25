# 054 — Vanilla Alaska, treaty coordinates and the removed coast's visual footprint

2026-10-25; generator **0.12.4 / epoch 34**. Target: EU5 1.4.4 executable,
Steam build 26142040, with the unchanged 1.4.3-data map fingerprint
`592e8309b7ed9bef1cc0df3eaccd798896d75cd3c3d7ecf9ed525bb6aca3009a`.
No game launch. Follows the [TR46 register](../../docs/research/tr46-observer-audit.md).

## Vanilla and treaty findings

[V-LOCAL C304] Vanilla American land occupies both ends of the 16,384-column
raster. In the first 128 columns it covers 7,856 pixels; in the last 128, 2,969.
The right-side keys include `qawalangin`, `akuugun`, `amiq`, `sivuqaq`, `savoonga`
and `kitagnaq`. The rightmost 512 columns also contain `niigugis`, `naahmigus`,
`qaxun` and `st_matthew`. These are American hierarchy records, not retained
Asian land. Removing every American pixel on the right would not reproduce the
vanilla boundary policy. This does not establish that vanilla has a large
mainland crossing or that the generated terrain renders seamlessly.

[V-LOCAL C305] The Tordesillas situation selects sides using `is_east_of` and
`var_line_location`; claimability separately checks colonial eligibility and
claims. [V-LOCAL executable / INFERRED C305] Read-only registration, RTTI and
evaluator tracing identifies `CIsEastOfTrigger`. Its comparison uses a
map-dependent positive and negative coordinate span, not simply `x > line_x`.
The exact numeric span has not been established here. There is no basis for
patching the treaty to a linear right/left comparison, or for declaring the
owner's right-edge allocation wrong solely from its raster position.

[UNKNOWN] The precise line location and affected runtime location in the
owner's treaty were not recovered from the binary save. The exact vanilla
treaty side for each Alaska location remains conditional on that line. Land
wrap is retained; no new policy choice or engine/shader change is made in this
phase. The visible crack remains open as TR46-06a.

## Source of the Chukotka remnants

[V-LOCAL/V-EXEC C306] `Canvas.mask` describes replaced location pixels, not the
full offshore visual footprint of an original island. The height/material
writer previously wrote only under that mask; water colour and foam used the
same restriction. The retained shelf can therefore surround the newly lowered
island interior, making the raised, angular rim in the owner's pictures.

On the northern right-edge source tile, the first eight location pixels around
replaced American land include 525 unmasked water pixels above the deep-water
height, seven at or above the shore threshold in the downsampled source. These
figures are a measured local case, not a global count of bad vanilla pixels.

## Change made before synthesis

[V-EXEC C306] Height/material input windows include original water within the
support of a changed coastline. The eight-location-pixel reach comes from the
material and height shelf/smoothing support at two decal samples per location
pixel. Retained land remains outside this extension. Neighbouring decals,
including the opposite map edge, are considered when selecting touched layers.
The existing band/halo renderer and serializer then generate the final assets
directly; no second layer repairs written output.

Water colour and foam include original water whose old/new distance-to-land
field changes, plus the blur's support. Original pixels along unaffected shores
and common open ocean are retained. Location colours, hierarchy, gameplay sea
identities, relief model, treaty scripts and the existing terrain placements do
not change. New synthetic tests start with a removed island surrounded by a
raised original shelf and verify the rim disappears, including through the map
wrap, while retained land stays exact. Band/thread and whole-image/strip
comparisons exercise the resulting fields independently.

## Written-world verification

[V-EXEC C307] Complete project check: **1,896 Python tests passed**, 14 skipped;
**23 Rust tests passed**; formatting, lint and types clean. The locked Windows
wheel and 3,254-file hub pass source/version/dependency checks and the isolated
offscreen window/native/world-code self-test. Windows and Linux produce the same
new coast-code, footprint-mask and height sample hashes.

The epoch-34 reference retains epoch 33's seed and all settings:

```text
RNW1-081WG-1HAWD-H0XFH-T0060-80840-3C082-243AG-0C700-FEY0E
```

It has **824 non-metadata files**, digest
`e36228d2d0ea3b2bd5b1eeef0ad34328eff6ce8dddc17e06773313f2c7f769a6`.
Against the epoch-33 reference exactly **10** non-metadata files change: height
and material `.info`/`.bin` pairs of the two northern edge tiles and the two
water DDS files. The other **814** files are identical. The all-story/formable
family assertion remains satisfied. A fresh no-cache reproduction with hash
seed 7 and the local read-only suite pass: **13 tests passed, one skipped in
193.36 s**, including exact reference digest and the unchanged all-family gate.

The exact TR46 seed/default settings produce **RNW: Continents 56AP**, code:

```text
RNW1-040XN-DR20S-1RQ4T-Z0060-801CM-6D0
```

Its **825 non-metadata files** have digest
`b8a8417db97aec4e429d034b854f73575c3be296a5e57d5eadc5c175b958a853`.
All **853** bundle manifest entries are checked against disk; the mod itself
contains **827** files including metadata. The same ten common files change against
the owner-installed TR46; map PNGs, hierarchy, countries and scripts shared by
both remain identical. Twenty additional pre-play cover files reflect that the
owner had revealed the old world's New World while the new export uses the
normal covered default; they are not terrain fixes.

Independent decoded checks cover **19,950,952 retained land samples** on the
two changed tiles: heights and materials are byte-identical there. Outside the
old location canvas, **5,850 water height samples** change; **19** previously at
or above the shore threshold become **zero** such samples. Engine appearance
remains [UNKNOWN]; no new owner sitting is requested. Source assets, plots,
disassembly excerpts, logs, full reports and inventories stay ignored under
`local_data/tr46-boundary/` and `generated/`.

## Related boundary work still open

[V-EXEC] A read-back of TR46's original river raster finds six unwrapped
connected channel components without a green source, all touching the map edge.
Five sizes match the loader's recorded failures exactly (107, 502, 65, 16, 8).
The additional 48-pixel fragment has no matching failure in that log. The
generator's river-network check runs before the crop is placed across the
world edge, so that check alone does not validate the serialized fragments.
TR46-L01 is not fixed by this coast release; river export is the next related
investigation. No claim is made that this explains the terrain crack.

## Installation

[V-EXEC C308] Installed only the new **RNW: Continents 56AP** world in
`mod/rnw_exp_tr46_coast` (all **827** files hash-identical to the export), and
updated the main **`mod/rnw_exp_hub` 0.12.3 → 0.12.4** (all **3,254** files
hash-identical to the checked package). The prior generator has a checked
3,254-file backup outside the profile at
`local_data/tr46-boundary/hub-backup-before-0.12.4/` and is retained under the
installer's retired folder. Existing retired content was not swept.

Nine profile-root hashes, **4,061** other-mod size/time records and all three
prior mod folders are preserved. The original TR46, its campaign, settings,
playset and library records are unchanged. No EU5 launch or process control.
Installation and exact removal: [INSTALLED](../INSTALLED.md). The corrected
world remains an offline-verified candidate, with no requested owner sitting.
