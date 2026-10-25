# 057 — Local sea routes, closed-water identity and expedition access

2026-10-25. Generator **0.12.7**, epoch **37**. EU5 1.4.4 executable,
Steam build 26142040, on the previously fingerprinted 1.4.3 data (26105915).
Map-contract SHA-256:
`592e8309b7ed9bef1cc0df3eaccd798896d75cd3c3d7ecf9ed525bb6aca3009a`.
C317–C320 in the [ledger](../../docs/research/claims-ledger.md).

Related owner entries: [TR46-03/04 and L02/L03](../../docs/research/tr46-observer-audit.md).
The owner authorized implementation after the retrospective audit. This phase
uses the frozen campaign and offline generation; no EU5 launch or manual
sitting. The chosen full mainland wrap remains supported.

## Diagnosis

[V-EXEC C317] Reconstructing the exact TR46 seed/settings reproduces the old
249 lanes and 38 physical closed zones. The five adjacent names **Tziskoas →
Vakkwaukmoal → Giaxhuihoax → Xuatchian → Taichuaxlak Ocean** correspond to keys
`rnw_sea_00240`, `00023`, `00177`, `00284`, `00455` (each prefix `rnw_sea_`).
They are parts of one closed-water stretch arbitrarily divided at a target of
48 internal cells. Coastal-region naming gives each part an unrelated ocean
name. This is a matching reconstructed example; the owner's exact chain was
not identified in the screenshots.

[V-LOCAL / V-EXEC C317] Vanilla also has adjacent distinct closed waters: ten
pairs, including Baffin Bay/Labrador Sea and Barents Sea/Kara Sea. Thus adjacency
alone is not a defect. Preserve distinct geographic/retained identities; remove
the artificial generated size partitions. Enclosed seas and navigable coastal,
ocean, narrows and current-lane locations remain governed by their existing
physical classifications.

[V-EXEC C317] A sea-only shortest-path audit of coastal pairs within 720 raster
pixels, summing rounded centroid lengths, finds 32 TR46 pairs over twice the
unrestricted distance or disconnected inside the generated graph, out of 2,755
pairs. Finite within-canvas detours reach 9.44 times the local water route.
Including retained vanilla water resolves the apparent disconnections, but
leaves northern detours roughly 20–24 times the local route. For example,
`rnw_sea_00025` → `rnw_sea_00103` is 593 px by unrestricted water and 14,397 px
through available generated/retained water. Do not call these globally
unreachable. The same 720-pixel audit on vanilla has 64,791 finite pairs, seven
unreached cases, four finite detours over two, and a maximum finite factor of
2.60. These are geometric proxies, not engine path cost or travel time.

[V-LOCAL / INFERRED C317] Vanilla's western voyage uses three port landfalls
(Guanahani, Inagua, Bahama) and a sea alternative. The generic nearest-land
remapper sends them to `rnw_loc_02659`, `rnw_loc_02759`, `rnw_loc_02500`; all
three are inland and lack ports. The frozen definitions are byte-identical to
the pre-maritime candidate. Applying the existing one-based definition-index
contract (C162) maps logged IDs **21039 → rnw_loc_02500** and **21247 →
rnw_loc_02659**: exactly two of those landfalls. This supports a concrete cause
for the three western-voyage failures. It is an inference from the known index
contract, matching scripts and logs; no runtime save was decoded, and the
original Workshop-mount confounder remains recorded.

[V-LOCAL / UNKNOWN C317] Limited static tracing places the separate
port/water assertion in a destination-change routine, with port/water checks
and recursion over associated objects. There is no runtime caller or failing
location. Do not attribute L02 to the voyage or mark it resolved. Mining-survey
exhaustion, invalid resumes/leaders and other lifecycle diagnostics remain open.

## Construction rules

[V-EXEC C318] `sea_routes.py` adds a local requirement before final water
identities are serialized:

- Endpoints are coastal sea cells and contacts with retained navigable water.
- A local pair is at most **six typical sea-cell widths** apart along the
  unrestricted water graph. Land is never traversed.
- Its navigable route is at most **twice** that distance. Lengths are integer
  square-root centroid distances, at least one per edge. This is a deliberate
  generator policy, not a claim that vanilla uses these constants.
- Keep inherited current lanes and the existing global connections. Open every
  deep retained-water contact, then process short local pairs first with stable
  cell-number ties, opening only required cells on a shortest water path.
- Fold each connected remainder of closed deep water into one physical zone.
  The existing ocean planner can still join it through connected retained water
  or retain distinct vanilla identities. There is no size quota.

`RemapAccess` keeps a removed port on a generated port and removed navigable
sea on navigable sea. The same global replacement applies to literal waypoints,
callbacks and other references to the place. Incompatible destinations fail
export rather than falling back to another family. Ordinary closed-water
references keep their existing nearest-family behaviour. All changes construct
the model before serialization; there is no output repair, shader change,
companion mod or change to the installed game.

## Verification

[V-EXEC C319] Full locked check: **1,962 Python tests pass, 14 skip; 23 Rust
tests pass**, with format/lint/types clean. New synthetic cases cover locally
distant routes despite global connectivity, continuation of retained contacts,
connected closed water without a size quota, coastal and navigable replacement
roles, matching callbacks and failure when no compatible destination exists.

Exact TR46 settings/seed now produce **RNW: Continents BU2A**, code:

```text
RNW1-040XN-DR20S-1RQ4T-Z0060-E02AN-B0G
```

There are **278 lanes**, **35 physical closed zones** and **30 distinct closed
identities touching the generated model** after retained-water aliases. The
29 newly opened cells satisfy all **3,700** local pairs (scale 118 px); the
independent read-back maximum detour is **1.90849**, below two. No adjacent
generated closed cells have different final identities. Every retained
navigable-water contact is open. The old 556/5,237 px route from
`rnw_sea_00308` to `rnw_sea_00403` is now 556 px (integer metric).

All **20 literal sea-expedition waypoints** found in the effective base/world
definitions are passable water or port land. The western voyage now uses
`rnw_loc_02465`, `rnw_loc_02503`, `rnw_loc_02465`, `rnw_sea_00608`; the repeated
port is a valid shared nearest destination for two former islands. Dynamic
waypoint expressions and actual expedition outcomes remain unobserved.

The exporter reads back **4,325** total port rows, 278 lane/current records,
7,919 locators and five army crossings; no lost Old World contacts, inaccessible
generated sea cells or coastal land without port access. Army crossings remain
a separate interface from shipping paths.

Independent comparison preserves **50,987,808 nonsea pixels by location key**,
including **30,434,666 retained nonsea RGB pixels exactly**. Geography is
unchanged. Twenty-five generated land/lake identities have 25,652 recoloured
pixels because cell numbering changed; their keys and geometry remain exact.
All terrain2 assets (including water textures) and `rivers.png` are byte-exact.
Every nonempty population record is exact; country setup differs only in
discovered sea-area lists. All **59,404 road strips**, keyed by location pair,
retain exact point coordinates: only numeric indexing changes in the binary.
There are **61 changed nonmetadata files**, no added/removed mod paths; these
cover water identity/ports/locators/adjacency, scripts, texts, empty sea-pop
records, discovered areas and spline indexing. All **861 bundle entries** hash
correctly. No game assets or raw derived maps are committed.

BU2A has **833 nonmetadata files**, digest
`9bea353cf4d9b7ee7fee6500c944e45c39cd5e23b57454299fa61edf6d41746e`.
The epoch-37 reference retains all story/formable families: **832 files**,
`2cccf2b2fb512540cc2ff9d43fb1e89cdf668bbaaf9eb043d1fabe3d601e770f`,
code `RNW1-081WG-1HAWD-H0XFH-T0060-E0840-3C082-243AG-0C700-B2JT8`.
Fresh no-cache reproduction at hash seed 7 passes **13 local checks, one skip,
220.16 seconds**. Linux/Windows four-case maritime/access parity has digest
`6a3db0718a974a980af3f728dff980894f29f08d6d8d384629b49410af93ff2b`;
the isolated offscreen Windows generator self-test passes.

Ignored evidence: `local_data/tr46-maritime/` (`physical.pickle`, original
`audit.json`, `vanilla.json`, `retained-routes.json`, `output-audit.json`,
`file-diff.json`, `local-routes.png`, export/check/build/parity/install records).
The original audit predates the code change; rerunning it against the new
planner would change the measured subject. No later session replaces the
frozen campaign evidence.

## Remaining limits and handover

TR46-03/04 and the western-voyage part of L03 have identified written-data
causes and offline corrections. Engine movement cost, navigation appearance,
regional naming appearance and successful voyage execution are **UNKNOWN**.
L02 and other L03 lifecycle failures remain open. The original owner observations
are not closed merely because the tests pass. No new game sitting is requested.

Installation is recorded in [INSTALLED](../INSTALLED.md), C320. The next
independent block is impassable-land grouping and physical mountain relief
(TR46-01/02), with separate evidence needed for each.
