# 055 — Rivers crossing the world seam

2026-10-25. Generator **0.12.5**, epoch **35**, EU5 **1.4.4 executable**
(Steam build 26142040) on **1.4.3 data** (26105915). Current map fingerprint:
`592e8309b7ed9bef1cc0df3eaccd798896d75cd3c3d7ecf9ed525bb6aca3009a`.
Evidence: C309–C312; [TR46 register](../../docs/research/tr46-observer-audit.md),
TR46-L01 and 06a/06b. No EU5 launch or new manual sitting.

## Decision and cause

[OWNER] Keep full mainland crossing through the seam and fix its support. Do not
restore the seam strait removed in 0.12.2 or constrain the generated land shape.
This decision does not establish the reported treaty allocation as a defect.

[V-EXEC C309] Original TR46 has six planar river components without a green
start, all touching a horizontal map edge. Five component sizes, **107, 502, 65,
16 and 8 pixels**, exactly match the five loader errors (698 pixels). The sixth,
**48 pixels**, has no matching diagnostic; the reason remains unknown. These
are pieces of **one** continuous logical tree, split into seven raster pieces.
The former validator checks the rolled tree before world placement, so it does
not discover the missing starts after that placement.

[V-LOCAL executable / INFERRED C309] Limited read-only xref/disassembly tracing
of the installed missing-source diagnostic identifies four-neighbour component
discovery bounded by raster coordinates, with no horizontal wrap, and a count
of green markers. Zero and multiple markers have separate error paths. This is
not a complete specification of the later mesh builder. Raw executable material
remains ignored/local; [interoperability R-004](../../docs/research/interoperability.md)
records the method and its limits. No code/process/installation is changed.

## Construction

[V-EXEC C310] `eu5_rivers.py` is the PNG adapter for logical `Rivers`. It visits
only trees with an edge crossing the world seam, using sparse traversals. It
constructs planar tree fragments with one leaf start and one valid tributary
marker per confluence. A retained original start has priority; another piece
starts at the endpoint furthest upstream along the original tree. Width classes
stay attached to their channel samples. Trees without a seam contact retain
exact codes. The initial palette is written in strips.

An isolated point has no segment to draw: its omission from the raster drawing
is explicitly counted, while the logical network and carved valley retain it.
Invalid trees or unrepresentable junctions fail loudly. This is initial
serialization, not a repair of an exported world, a fallback geography, a new
spring/drainage basin or a shader/engine patch. Drainage, relief, rainfall and
valley construction are unchanged.

## Verification

[V-EXEC C311] Synthetic tests cover every cut position of a fork, cuts through
its source/junction/tributary, meanders and nested branches on three generated
trees, uncut-byte equality, singleton accounting and invalid-input refusal.
The independent consumer moves the raster into world coordinates and checks
planar topology, starts, joins, mouths/boundary terminals and unchanged widths.
The complete project check passes: **1,949 Python tests, 14 skips**, **23 Rust
tests**, clean formatting/lint/types. Windows and Linux agree for **180** seam
positions (digest `fb77f6a1e2c9c8d42251012ada59f49c7bf61584c9d52857109bd9fe1dbf0628`),
and the isolated offscreen Windows self-test passes.

The reference keeps the prior seed/settings and all story/formable families:

```text
RNW1-081WG-1HAWD-H0XFH-T0060-A0840-3C082-243AG-0C700-XB6NE
```

Its **824** nonmetadata files have digest
`0016e1ad19eca7e2dfe77c670e1d0073e458411439ac3c4fd5e10385f49c00d9`.
A fresh hash-seed-7, no-cache reproduction passes **13 local checks with one
skip in 236.01 seconds**.

The exact TR46 seed/settings become **RNW: Continents R7SE**:

```text
RNW1-040XN-DR20S-1RQ4T-Z0060-A01VN-AKG
```

**825** nonmetadata files, digest
`b392f2c9a5f29425f6765cdb2b43e84326af89697186a1a0ffdac22da95b972b`.
Independent read-back against the 0.12.4 coast candidate changes **only
`rivers.png`**, at **12 marker pixels**. All **792,805** channel pixels and
remaining body widths are identical. All **716** planar components now have
exactly one start; no isolated point is omitted in TR46. Every other one of the
825 mod files is identical, including locations, relief/materials, water,
vegetation, countries and gameplay content. Thus the prior coast correction
and the geographic/Old World preservation checks remain intact.

Local evidence: ignored `local_data/tr46-boundary/` (`*-river-report.json`,
`river-output-audit.json`, `river-check.log`, `river-local-check.log`, Windows
build/parity/self-test records). Generated binaries and raw game material are
not committed.

## Delivery and remaining boundary work

Installation and exact removal are recorded in [INSTALLED](../INSTALLED.md).
The game remains closed; existing worlds, saves, settings, playsets and library
records are preserved. A new world contains this serialization; existing TR46
and its saves are not rewritten.

TR46-L01's written-data cause is addressed. Absence of loader errors and the
rendered continuity/caps of the new pieces remain **unobserved in engine**.
The separate physical terrain crack (TR46-06a), exact treaty runtime allocation
(06b) and the other audit items remain open. River tests do not close them.
