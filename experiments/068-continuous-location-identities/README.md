# Continuous location identities at the raster edge

## Corrected premise

[V-GAME owner C374] The owner reports that vanilla American land and southern
ocean routes cross the raster boundary normally, while RNW cuts both land and
sea locations into distinct identities with an exactly vertical boundary.
They request a generator fix following vanilla's working representation.

[INFERRED correction C374–C375] Experiment 067 localized a real failure in
the refiner and reproduced its intermediate arithmetic. It did **not** prove
the mod's input valid, the absence of a data-level repair, or that continuous
mainland is unsupported by the engine. Treating the generator's already-split
locations as evidence against a generator defect reversed the relevant
comparison. C373's broad repair boundary is superseded here; C371's captured
arithmetic remains a separate observation.

The installation is still EU5 1.4.4 executable **26142040** on fingerprinted
1.4.3 map data, contract **592e8309…03009a**. The original world is EVXP
**0.13.2 / epoch 41**, seed **9781797494467218106**. No new game launch occurs.

## Vanilla comparison and failing regression

[V-LOCAL / V-EXEC C375] At raster width 16,384 and height 8,192, vanilla has
**8,127** rows whose first and last pixels have the same location identity,
**65** whose identities differ, and **54** identities present on both edges.
Vanilla includes American land in that shared set. Different identities on
an occasional row are normal staggered geographic borders, not a requirement
that every pair of edge pixels be equal.

The original EVXP instead has **6,255 / 1,937** equal/different rows and
**38** shared identities, with long generated land and sea contacts exactly
on the cut. The production land cache explicitly requested
`split_at_seam=True`. The splitting helper dates to `69de7b6`; `237fa7f`
retained it in cached generation, and it survived the later mainland-wrap
change. In a synthetic 160×400 canvas, that call makes **171** identities
where the continuous generation has **157**: fourteen invented locations.
The production-versus-continuous label equality assertion fails before the fix.

## Change by construction

[V-EXEC C376] **0.13.5 / epoch 42** removes the split implementation and its
generation options. The land model is built in its continuous logical canvas;
`Canvas.put` projects the same identities onto either side of the game's raster.
No seam is passed into cell construction or its cache key. Cache schema and
epoch prevent reuse of the older cut-cell cache. Relief, coast generation and
the terrain padding introduced for the visual crack are unchanged.

Regression coverage checks land and water cells across three projection cuts,
their graph, colour identity and cylindrical connectivity. The same identities
would appear fragmented to a planar-only check, which is why their production
representation must not be forced into separate planar locations.

The former reference's reduced cell count also exposed two missing coastal
area keys, `labrador_sea_area` and `brazil_sea_zones_area`. Its first export
correctly failed because the old setup pruning retired GRL solely for an
obsolete discovery-area reference; after that was investigated, residual
script references also failed validation. No validator was weakened.
Wholly removed areas now bind to the generated area receiving the most of
their location replacements, with name order breaking ties. The same planned
bindings reach vanilla setup source **before** pruning and reach script scopes,
values and lists through the existing remapper. Discovery is retained in the
replacement area; country ownership/capital dependencies still retire truly
removed countries. A missing compatible replacement fails loudly.

This is initial source binding, not a campaign hook or repair of emitted data.
Synthetic checks cover a retained country, removed capital and dependent,
fixed-point retirement, navigable destination, deduplicated area lists and
missing-destination failure. The former reference then exports successfully,
retaining GRL and passing the complete script-reference checks. It lacks a
maritime-league opportunity under the new identities, so EVXP, which offers
every story family, becomes this epoch's reference.

## Independent written-file evidence

[V-EXEC C377] Rebuilt the owner's exact seed and settings. The new written map
has **8,103 / 89** equal/different seam rows and **74** shared identities,
including generated land and water. Across the full raster, **zero physical
class pixels change** from original EVXP. All **30,434,666** retained nonsea
Old World RGB pixels equal vanilla. Rivers are byte-identical. Of **558**
terrain2 files, only **16 material files/metadata** change; height sources,
their placements and the remaining terrain files stay exact.

The Towa route's former `rnw_loc_01329` / `rnw_loc_05117` anchor positions now
both identify **rnw_loc_01329**. Its artificial adjacency no longer exists.
For the earlier 1346 pair, the two natural neighbouring locations remain
distinct, **rnw_loc_01100 / rnw_loc_01128**; each now continues over the raster
edge. Their written unit anchors are close together on the same side of the
raster, rather than separated by nearly a map width. The initial audit's
assumption that this second pair must merge into one identity was false and
was corrected, not presented as a passing result.

All **6,312** generated unit-stack anchors occupy their own written identity;
all **865** canonical bundle entries match their size and SHA-256. Private
before/after border rendering was inspected. It is an offline identity view,
not a screenshot or proof of post-fix movement in game.

## Verification and delivery

[V-EXEC C378] Complete project check: **2,005 Python tests pass, 14 skip**;
**23 Rust tests pass**, formatting/lint/types clean. Four synthetic geometry
cases, including drawn land, and one area-binding/setup case agree between
Linux and the final Windows package, digest **b57e6fa0…18a02**. Its isolated
offscreen window/native-kernel self-test passes.

The epoch-42 reference uses the corrected EVXP code in `tests/golden_world.json`:
**837 nonmetadata files**, digest **76c17c96…f4d5b0**. A fresh, hash-seed-7
installed-game/reference test run passes **13 tests**, with only the separate
layer-export experiment skipped, in **213.41 seconds**. It independently
regenerates the reference with the final source, compares the digest, and
checks every story family. This also establishes that the added area binding,
unused by EVXP's retained areas, did not change its candidate bytes.

Prepared a separate **RNW: Supercontinent EVXP fixed**, folder
`rnw_exp_evxp_identities`, library id **uj3emczw5t**, with **6,874** atlas
locations and a **29-file** recovery receipt. Independent receipt adoption
restores its full preview and record. Installation is verified in
[INSTALLED](../INSTALLED.md) (C379): **848** world files, **3,266** hub files,
and the 29-file entry in both native and Windows libraries. The generator-only
hub moves **0.13.3 → 0.13.5**, with verified external and retired backups.
All **820** original EVXP file hashes, **4,225** other-mod size/time records,
**nine** profile-root hashes, **111** save-file size/time records, **eleven**
prior library records and **two** preference files are preserved. No retired
directory sweep occurs. Live host inspection finds EU5 absent; the forced-close
session's log still reads `played`, so that stale flag is not represented as
a live-game result.

[UNKNOWN C378] Post-fix troop raising, movement and campaign stability have
not been observed in EU5. No further owner sitting is requested in this phase.
Changed location identities require a new campaign; no existing world or save
is migrated or overwritten. No engine binary, shader/define workaround,
impassable stripe, seam channel, companion mod or runtime repair is added.

## Private artifacts and removal

Raw game data, audits, packages, source comparisons and images remain ignored
under `local_data/seam-identities/` and `generated/`. No proprietary asset is
committed. Existing binary adapters are recorded in interoperability R-001/R-004;
the correction to the hang interpretation is recorded in R-006.

Remove only the new candidate with the generator's Remove action or
`uv run rnw uninstall-mod rnw_exp_evxp_identities --user-dir USER_DIR` while
the game is closed. The original EVXP is a separate world.
