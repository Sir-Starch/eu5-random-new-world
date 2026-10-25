# 056 — Periodic source support in the primary heightmaps

2026-10-25. Generator **0.12.6**, epoch **36**, EU5 **1.4.4 executable** /
Steam build 26142040 on **1.4.3 data**, build 26105915. Map fingerprint:
`592e8309b7ed9bef1cc0df3eaccd798896d75cd3c3d7ecf9ed525bb6aca3009a`.
Evidence C313–C316. Continuation of [055](../055-wrap-river-raster/README.md)
and the owner's decision to support full mainland wrap. No EU5 launch.

## What the existing evidence establishes

[V-GAME owner / V-LOCAL C313] TR46 on 0.12.3 still has a physical seam. The
0.12.3 candidate's eight periodic heightmap placements lie entirely outside the
world and only touch its bounds. The installed shader checks half-open decal
bounds, and its decal-list lookup clamps query cells to the in-world spatial
grid. These facts are separate: testing a decal's transformed bounds does not
establish that the CPU put that decal into the queried grid cell. The former
synthetic tests checked the first fact only. Exact CPU admission and the cause
of the owner's rendered crack remain **unproved**; no new claim that the engine
always rejects outside placements is made.

[V-LOCAL C313] The virtual-texture interface explicitly carries a UV scale for
non-power-of-two source dimensions. Height/material `.info` declares source
size, the cache declares decal size/transform, and the active instance declares
the same placement. The new candidate uses these existing data mechanisms. No
shader, engine, GUI or game-installation file is changed.

## Construction

[V-EXEC C314] Each of the eight primary edge heightmaps now includes **512
location pixels** of periodic source support beyond its outer edge: **1024
source samples / 2048 terrain units**. Its source becomes **9216 × 4096**,
its primary centre shifts toward that edge by half the added physical span, and its
interior world-to-source alignment stays unchanged. Left padding reads the
opposite right source, and right padding reads the opposite left source.
The padded inputs are synthesized directly in the existing bands, with wrapped
field coordinates and an explicit split if the rolled noise cut falls inside
the padding. Retained source samples remain intact.

Cache geometry and each original active instance agree. The primary centres
stay strictly within the world and their bounds overlap the edge grid cells;
world-edge vertices and tested outside halos lie inside primary source bounds.
There are still **16** primary placements, including **8** padded ones, and
**no** outside-only duplicate. No interior overlap or added terrain blend layer
is introduced. All eight edge sources are emitted, even where an original
source was not otherwise touched, so geometry cannot name unpadded source data.
The global material raster takes only each source's in-world portion.

All layer headers must match the written sample dimensions; a mismatch now
fails loudly before serialization. Missing/ambiguous opposite sources, changed
scale/rotation or disagreeing cache/instance geometry also fail. No full-map
repair pass, geographic restriction, seam strait or later repair of an emitted
binary is used. Binary formats and local-only distribution rules remain in
[interoperability R-004](../../docs/research/interoperability.md).

## Verification

[V-EXEC C315] Synthetic checks compare padded synthesis against the opposite
sides of independently rebuilt original tiles: every interior and halo sample
matches across band sizes 13/500, one/three workers and rolled-noise cuts inside
both sides of the padding. Geometry checks cover unique primary coverage,
unchanged sample addressing, cache/instance equality and guard failures.
The complete project check passes: **1,956 Python tests, 14 skips**, **23 Rust
tests**, clean format/lint/types. Linux and Windows produce the same eight
synthetic layer files (digest
`52dfd598ae9c50a00ac0960ab7fa3b430a88daf45a4984f08b26dfcb0eae2ee2`);
the isolated offscreen Windows self-test passes.

The reference retains its previous seed/settings and all story/formable
families:

```text
RNW1-081WG-1HAWD-H0XFH-T0060-C0840-3C082-243AG-0C700-2QGH4
```

**832** nonmetadata files, digest
`2bebfb66cffff1fa539f46686d4380318e29331392b7f0fb016a8fb56dc0f8dc`.
Fresh independent hash-seed-7/no-cache reproduction passes **13 local checks
with one skip in 210.43 seconds**.

The exact TR46 seed/settings become **RNW: Continents KUIG**:

```text
RNW1-040XN-DR20S-1RQ4T-Z0060-C05RD-5A0
```

**833** nonmetadata files, digest
`9b5a912ec9908dba4969164896b3a85844a151eeee53eecd8f8e1934cf15c3d2`.
Independent read-back against 0.12.5 verifies **536,870,912** original level-zero
height/material samples exactly and **67,108,864** periodic support samples
against their opposite source. All **861** bundle manifest entries hash
correctly. Exactly **25** common files change, **16** are added and the **8**
outside-only instance files are omitted; every changed path is under terrain2.
The cache contains 16 primaries, eight padded; their existing active instance
positions match. Boundary vertices and ±1536-terrain-unit halo queries have
one primary source at each of four row bands.

All files outside terrain2 remain byte-identical, including locations, river
codes (and the 055 starts/joins), societies/content, water DDSs, objects and
roads. The original TR46 world is not rewritten. Raw evidence stays ignored in
`local_data/tr46-boundary/` (`terrain-output-audit.json`, `*-terrain-report.json`,
check/build/parity logs); generated assets are not committed.

## Delivery and limits

The new candidate and main-generator update are recorded in
[INSTALLED](../INSTALLED.md), with exact removal. No playset/settings/save/library
change, game launch, new sitting or publication is performed.

TR46-06a remains **open pending engine appearance**. The new data eliminates
the half-open source gap while avoiding dependence on outside-only admission;
it does not prove the owner's crack is gone. Level-zero retained samples are
exact, but source dimensions naturally change their mip pyramid; distant
rendering and every engine LOD are not claimed identical or validated. Likewise
CPU admission, mesh behaviour and full halo reach require engine evidence,
which is not replaced by synthetic tests. The existing batch-testing policy
applies; no new owner check is requested here. The remaining audit items retain
their original evidence and IDs.
