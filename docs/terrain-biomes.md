# Terrain and biome synthesis (phase V1)

The terrain/biome pipeline ships in 1.0.0. The dated implementation and vanilla surveys below explain its construction; they are not a new validation queue. Current world-wrap policy is in [AGENTS](../AGENTS.md) and the [wrap dossier](research/map-wrap-dossier.md).

**Status:** V1a implemented on 2026-10-19 and reviewed by the owner in game (C55): it loads and renders; four defects led to V1a.1 (generator 0.5.0, below), which the owner accepted in game (C58). V1b rivers implemented on 2026-10-19 (generator 0.6.0, C59–C60) and accepted by the owner in game (C64); the same review led to V1b.1 (generator 0.7.0, below), accepted in game (C66).

## Problem

The owner reviewed the generated New World in EU5 1.4.1 on 2026-10-19 [V-GAME owner observation]. Coasts and water were fixed, but up close the land looked pixelated: forests and other biomes showed many small squares, borders were rough, biomes did not fill coherent areas, and transitions were not smooth. Generation must use a deliberate algorithm, not noise plus random patches.

## How EU5 draws land

Investigation of the 1.4.1 files changed the plan [V-LOCAL C50; V-EXEC C51, C52]:

- **Biome per location.** The shader samples a per-location biome texture through the location colour map (`main_menu/gfx/FX/cw/terrain2_biomes.fxh`). The biome is chosen from the location template's climate, vegetation and topography in `gfx/map/biome_definitions/biomes.txt`. A coherent look therefore needs coherent templates.
- **The material layer stores slots, not textures.** Every biome in `gfx/terrain2/materials.txt` lists 16 materials (a few list 17). The decal layer selects one of them per pixel by role:

  | Slots | Role | Vanilla rule |
  |---|---|---|
  | 0–4 | Coast, chosen by the location's topography (flatland, hills, plateau, mountains, wetlands) | 1–4 px inland; 2–6 px offshore |
  | 5 | Coast transition | 4–10 px inland |
  | 6 | Rivers, lake and sea edges | 0–3 px around river pixels; 5–10 px offshore |
  | 7 | Topography border | Band of about ±4 px around location borders where topography changes |
  | 8 | Vegetation border | Same band where vegetation changes |
  | 9 | Climate border | Same band where climate changes |
  | 10–15 | Two families of three variations | Family blobs about 25 px; level blobs about 8 px |

  Where several attributes change at once, topography wins, then vegetation, then climate. Some changes get no band: flatland ↔ flatland wasteland, arid ↔ hot semi-arid, cold arid ↔ cold semi-arid, arctic ↔ subpolar. Level shares depend on vegetation and topography; forest uses level 1 only. Pixels are decal pixels, two per location pixel.
- **Short material lists.** Only 33 of 191 biome lists have 16 entries; 93 have 13 (no second variation family), others 12, 14 or 15, and `arid_plateau_desert_biome` has one. The shader clamps the slot to 15 and reads a fixed table whose unlisted entries most likely point at material 0, `fallback_material` (dead grass) [V-LOCAL C54; INFERRED]. Vanilla writes the missing slots anyway; generated land does not (stage 5).
- **Trees and ground clutter are pre-placed instances.** They live in `gfx/map/map_objects/*_generator_*.bin` (40-byte records: x, y, z, quaternion, scale) and in three inline `jungle_dense` text files. 27–44% of the forest, pine, jungle, woods and grass instances stood on the removed Americas.

The interim patch transfer copied river and border bands from unrelated places and took templates from random donors. That produced the squares and the mosaic (C47).

## Algorithm (implemented)

| Stage | Module | Method |
|---|---|---|
| 0. Land and sea | `newworld.py` | Fractal noise above a threshold that keeps the land budget, with one seed-drawn lattice origin for the whole crop so high-variance nodes do not favour fixed map positions (0.12.1, C286). Near a guard (protected-domain or longitudinal canvas edge, axes opening enclosed seas) elevation falls over a ramp of four coast margins whose start moves inland by 0–2 ramps of warped noise; canvas slivers thinner than two ramps stay sea. A sea cut off around a protected islet gets its shortest path to open water added to the guard, and the coasts are redrawn (C64). |
| 1. Relief | `relief.py` | One continuous height field in decal units. Mountain chains follow the zero lines of two families of low-frequency noise at the width of a real range (the noise divided by its slope), rise to massifs of varied height and carry ridged-multifractal crests; plus foothills, hill country, plateaus, a broad tilt and an inland rise. All noise uses rotated lattices and domain warping, so nothing aligns with the raster. Ramps use a Euclidean distance to the sea. Up to epoch 63 the highest cells become wastelands; from epoch 64 they are planned ([Natural wastelands](#natural-wastelands-130--epoch-64)). From epoch 64 the active coasts of each landmass also raise a cordillera, and the land falls away from them ([Drainage before cells](#drainage-before-cells-130--epoch-64)). See [Mountains and hills](#mountains-and-hills-110--epoch-60). |
| 2. Climate | `climate.py`, `eu5_biomes.py` | Absolute latitude comes from city-locator anchors (C49). Rainfall comes from zonal winds: easterlies below 30°, westerlies from 30° to 60°, polar easterlies above, blended across the band edges. The sea recharges moisture (an ocean fully, a strait little). Land loses a fixed share per pixel plus an orographic share on smoothed terrain, which gives rain shadow behind ranges. The same model runs on the vanilla map and on the generated map. From epoch 64 (`OPEN_CLIMATE`) it runs once for a summer and once for a winter (`climate.seasonal_rainfall`): the belts move 7° poleward in summer and back in winter, colder air holds less water, the equatorial trough and the storm tracks rain readily and the subtropical highs hardly, summer air also flows in from the seas on the equator side (the monsoon), and the sea off a subtropical west coast is cold and gives little water; the vote reads the fourth roots of both seasons' rain. The yearly zonal rain had told vanilla's dry climates from the others no better than chance within a latitude band, and the vanilla river density did not rise with it; the seasonal rain finds the dry climates of a continent the vote did not learn from about twice as often (Africa 21 % against 13 %, Oceania 32 % against 10 %), vanilla's river density rises with it (0.86 to 1.24 of the mean from the driest land with rivers to the wettest), and on generated worlds the wettest tenth of the land is 77–80 % tropical where it had been 36–52 % [V-EXEC 2026-11-14]. |
| 3. Classification | `eu5_biomes.py` | Integer k-nearest-neighbour vote (k = 32) on latitude, rainfall, height and distance to the sea. It predicts climate first, then vegetation among the pairs of the chosen climate. Up to epoch 63 it learns from Old World location centres and treats farmland as grassland. From epoch 64 it uses a 48-pixel grid over all vanilla land except farmland, keeps a donor for each pair the grid misses, and calibrates pair weights on those readings. Sea and lake climates come from vanilla sea zones by latitude and distance to land. |
| 4. Coherence | `eu5_biomes.py` | Up to epoch 63 the joint (climate, vegetation) votes are smoothed over the location adjacency graph: 3 rounds choose the climate; 1 round, limited to that climate's own pairs and widened when it has no vote, chooses the vegetation (issue #4). From epoch 64 neither is smoothed: the k-NN vote on smooth fields already gives climate regions near the Americas' size (10–11 cells against 11.1; the Old World 13.3). Topography comes from relief ranks in vanilla proportions (mountains, plateaus, hills, wetlands, flatland), using height, height spread, rainfall and distance to the coast; from epoch 64 hills are ranked by how much their height bends over eight pixels, not by the slope every coastal cell has, and mountains and plateaus by the spread of the ground a cell lies on (64-pixel blocks), not by its own, which grows with the cell. Desert cells never become wetlands, because no biome covers that combination (C54). |
| 5. Material slots | `eu5_slots.py` | The vanilla rules above, applied to the generated labels and templates. Band edges, variation families and levels come from uniformised integer noise in absolute decal coordinates, so adjacent decals agree. Each label's biome is resolved through `biomes.txt` (most specific rule); a slot its material list lacks becomes the same variation level of the first family, else the highest listed level, else slot 0. On mountains the installed stamps' own slots are laid over the variations (below). |
| 6. Gameplay consistency | `eu5_nw_export.py` | Each location template gets the model's climate, vegetation and topography. Raw materials are drawn from vanilla frequencies for the same climate, vegetation, topography and coastal flag; from epoch 64 each class is pooled with its broader ones by how many vanilla locations stand behind it ([economy](economy.md#raw-materials-0914-c119)). |
| 7. Vegetation instances | `eu5_objects.py` | Vanilla instances inside the canvas are dropped. New instances are sampled per material pixel at the Old World density for the pixel's (vegetation, climate, topography, slot) class. Rotation and scale are copied from vanilla records of the same file. The engine caps the mesh map objects of a game at 2^24 (16,777,216) and drops those loaded last, so the new instances may not outnumber the removed ones (all densities scale down together by a recorded factor; 1% of the budget stays unused, `ObjectBudgetError` otherwise). Vanilla holds 15.9 million, the 0.9.8 world 19.5 million (C95). |
| 7b. Rivers (V1b) | `rivers.py`, `eu5_nw_export.py` | On a 4-pixel grid, a priority flood from all water gives every land cell a downstream neighbour, so depressions are crossed; routing adds fractal valley noise so flow converges. The square root of rainfall accumulates downstream; the catchment threshold gives 16 river pixels per 1000 land pixels (vanilla 15.7). Streams split at confluences (larger branch continues); rivers to the sea need 12 cells. Each stream is drawn from its head down a smoothed, slightly meandering line until it reaches water (up to 3 px into it; the head becomes the source) or meets a river drawn before (a join pixel beside one river pixel). Widths 4/5/11/15 follow catchment in vanilla shares; valleys of 350–1,150 units are carved within 6 px; slot 6 runs along rivers. The export refuses any violation of the vanilla raster rules (C59). |
| 8. Location shapes | `newworld.py` | Cell borders are bent by a smooth displacement field, then cut-off pieces are re-attached, so borders and the bands along them are organic rather than polygonal. A cell that would vanish or split keeps its original shape; before generator 0.9.1 such a cell undid the bending everywhere (C71). The map wrap does not constrain land: one continuous crop is generated before it is placed across the two map edges (0.12.2, C289–C290). Administrative cells that cross the display seam are split without changing the land mask. A strait is cut wherever generated land would enclose the sea around a protected Old World islet (C61). City points maximise `min(2 × distance to the cell border, distance to water)`, so coastal cities stand inland. |

## Climate/vegetation consistency (issue #4; fixed in 1.1.0 / epoch 60)

[V-EXEC C443] RNW 1.0.0 conditioned vegetation votes on the selected climate, but its
empty-vote fallback restored the votes of every climate, and the one smoothing round then
added neighbours' votes that were conditioned on the *neighbour's* climate. A synthetic
13-cell call to `assign_biomes` gave a zero-rainfall-index centre `arid` climate and
`forest` vegetation, although the calibration held only arid/desert and tropical/forest
pairs ([issue #4](https://github.com/Sir-Starch/eu5-random-new-world/issues/4) has the
game-independent reproduction). It is no ban on forests in dry or continental climates:
the rule is that a cell's pair comes from votes its own climate holds.

[V-EXEC C452] **Prevalence** in four full exports of the installed 1.4.6 map (continents
1001, archipelago 7, small continents 21, the supercontinent reference world): 3 to 14 of
4,973 to 7,798 land cells (at most 0.19 %) carried a pair absent from the Old World
calibration, every one `desert` in a `subtropical` or `mediterranean` climate. The leak
ran both ways, not only forest into dry climates, and the climate itself was never wrong.

**Construction.** `eu5_biomes.regularize_votes` smooths the *joint* (climate, vegetation)
votes instead of two marginals. The climate is the largest climate sum of the votes
smoothed for `CLIMATE_ROUNDS` (unchanged: no climate differs in any of the four worlds).
The vegetation comes from the same votes smoothed for `VEGETATION_ROUNDS` and limited to
the climate the receiving cell took, so a neighbour's vote counts only as evidence for a
pair that the calibration holds in that climate. When the selected climate has no vote
in the cell's neighbourhood (its own nearest neighbours were all of another climate), the
neighbourhood widens by one smoothing round at a time, up to the climate's own rounds, in
which the climate was chosen and so is guaranteed a vote; the vegetation of another
climate is never borrowed. A cell without any vote raises `ValueError` rather than getting
an arbitrary pair. There is no repair pass and no rainfall threshold.

**Effect** on the same four worlds, against 1.0.0's rule:

| | Archipelago 7 | Continents 1001 | Small cont. 21 | Supercontinent |
|---|---:|---:|---:|---:|
| Pairs outside the calibration | 3 → 0 | 13 → 0 | 4 → 0 | 14 → 0 |
| Cells whose vegetation changes | 224 (4.5 %) | 248 (3.3 %) | 261 (3.3 %) | 257 (3.4 %) |
| …of those at a climate border | 220 | 242 | 257 | 249 |
| Cells whose own climate-limited votes were empty | 14 | 13 | 12 | 36 |
| Pair (climate, vegetation) edges alike, ‰ | 723 → 733 | 760 → 762 | 761 → 767 | 745 → 755 |
| Pair singleton regions, ‰ | 420 → 388 | 362 → 254 | 332 → 272 | 358 → 288 |
| Vegetation edges alike, ‰ | 787 → 768 | 811 → 793 | 814 → 799 | 797 → 787 |
| Vegetation differing from the cell's own vote, ‰ | 165 → 154 | 139 → 125 | 152 → 138 | 146 → 136 |
| Mean rainfall index under forest | 249 → 260 | 61 → 64 | 149 → 156 | 70 → 74 |

Almost every change lies on a climate border, where 1.0.0 mixed the votes of two climates.
The new rule follows the cell's own moisture evidence more closely (fewer overrides, forest
slightly wetter) and makes the climate/vegetation pairs more contiguous, at the price of
10–19‰ fewer alike *vegetation-only* edges, because the vegetation now changes with the
climate where the calibration says it does. The widening never fired on these maps: every
cell whose climate lacked an own vote found one among its neighbours within one round, so
it is tested synthetically (`tests/test_biome_consistency.py`, which also covers the
dry-centre graph, a wet cell in a dry climate, 12 random mixed maps that 1.0.0 fails on 7,
a coast-to-interior gradient, a rain shadow behind a range and calibrated cold-climate
forest at a rainfall index where another climate has desert). Engine rendering of the changed
borders is unobserved; the owner has not been asked to look.

## Acceptance results (seed 42, continents) [V-EXEC C51–C53]

- **Slot-rule fidelity:** rebuilding a 1600×2400 vanilla Mediterranean crop from vanilla templates gives 85.6% agreement on structural classes. Coast slot choice is right on 96% of coast pixels. The optional local test requires at least 80%.
- **Biome coherence:** the share of adjacent location pairs with the same climate is 919‰ (vanilla Old World 806‰); for vegetation it is 854‰ (vanilla 631‰). Mean region size is 86 and 38 locations (vanilla 13 and 7). Zones are deliberately more coherent than vanilla's location-level mosaic.
- **Climate bands:** tropical at 0–20°; subtropical and arid at 20–35°; Mediterranean and cold arid at 35–45°; continental at 45–55°; subpolar at 55–65°; arctic above 65°.
- **Vegetation instances:** density per 1000 location pixels, generated versus Old World:

  | Instances | Generated | Old World |
  |---|---|---|
  | Forest trees in forest | 75 | 90 |
  | Pine in forest | 344 | 283 |
  | Jungle trees in jungle | 387 | 299 |
  | Woods trees in woods | 97 | 75 |
  | Grass in grassland | 107 | 99 |

  None are placed on desert, sparse land or water.
- **Owner review in game (C55):** loads and renders. Defects and fixes (C56; V1a.1 build C57):

  | Defect | Cause | V1a.1 fix |
  |---|---|---|
  | Wide crack along the map wrap in the north-west | At the time attributed to an engine limitation [INFERRED]; 1,390 rows of generated land crossed it (vanilla: one islet). That attribution is not established: the generator also clamped terrain sampling at the seam and restarted detail noise (C289) | Historical workaround in 0.5.0: a 24 px exclusion band and coast ramp. Removed in 0.12.2; wrapped sampling and continuous noise now supply terrain across the seam (C290), with engine appearance still [UNKNOWN] |
  | Square city models with a corner in water | Large models next to the crack or a near shore; cities were already 8+ px from water | City points pushed inland: coastal cities now 11 px from water at the 1st percentile, 28 px at the median (were 8 and 21) |
  | Brown pixel-staircase patches in white desert | Slots 13–15 in 13-entry biomes such as `arid_hills_desert_biome` render `fallback_material` | Only listed slots are written on generated land; desert cells no longer become wetlands, which have no biome |
  | Green city ground in sand | Vanilla `city_materials` gives every non-Mediterranean biome the green peasant decal; models come from donor cultures | Not changed: an override would also change Old World deserts; native cultures are R6 |

## V1-era limits and later refinements

This list records the original V1 scope and measurements. Later terrain changes
are described below; future hydrology and relief work belongs in [roadmap](roadmap.md).

- **V1b rivers:** accepted in game (C64). Lakes ended rivers (no outflows) until the 1.1.0 (see
  [below](#coast-shape-water-bodies-and-drainage-110--epoch-60)); splits and deltas are not generated.
- **V1b.1 coastline outline (C64–C65):** the owner saw the same north-west on a new seed. The edge ramp had grown with `feature_px` to 533 px and left only the canvas core for the land budget, so every seed filled the same outline (land overlap between seeds IoU 0.53–0.67). Now 0.31–0.45; seam coasts and straits use the same ragged coast model. Accepted in game (C66).
- Mountain stamps on generated ranges (vanilla covers about 57% of mountain interiors with them): placed along the ranges since 1.1.0, with their materials ([below](#mountains-and-hills-110--epoch-60)).
- Erosion for more natural valleys.
- The V1 measurement was about 1.3 GB per built world, because instance files are whole-file overrides; this is not the size of the generator hub.

## Continuous map wrap (0.12.2)

[V-EXEC C289–C290] The wrap is an interior column of one rolled generation crop, not a second domain. Land masks, elevation, climate and drainage are generated before display coordinates are restored. Neither generated nor drawn land gets a special exclusion band there. The split of location identities keeps compact bounding boxes and interior points; it does not separate landmasses.

Height and material decal windows read their horizontal halo modulo the map width. Detail and material noise use the rolled coordinates of that same crop, so the noise cut is outside its replaceable domain. A synthetic continent rendered whole and then rolled produces exactly the same decoded height and material pixels, including both world edges and arbitrary row bands. Water distance and blur also wrap horizontally, with periodic detail noise. Road contacts include both map edges and their curves use the shorter cylindrical displacement; read-back validation checks their steps and preserves every retained vanilla polyline. The engine rendering of the new wrap contacts has not been observed.

## Boundary placement and coast precision (0.12.3)

[V-GAME owner C293] 0.12.2 still shows a physical crack and regular straight teeth
in large-continent coasts. [V-EXEC C294] Interpolation had only 256 fractional
positions across a 3,600-pixel octave: long flat stretches then large jumps.
The shared integer kernel now uses 65,536 fractions; derivative-bound tests reject
the old jumps without smoothing or repairing a finished coast.

[V-LOCAL/V-EXEC C295] A pixel-continuous field also needs periodic **placements**.
The terrain compute shader accepts a decal's lower boundary and excludes its
upper boundary. The first/last column assets are now placed once more beyond each
horizontal world edge, reusing their textures; both cache and instance records
agree. These outside placements supply boundary/halo samples while interior
coverage stays identical. [UNKNOWN] The candidate's actual engine rendering;
synthetic source-coverage checks do not prove CPU admission or mesh extent.

## Impassable units and mountain detail (0.12.8)

[V-LOCAL / V-EXEC C321–C323] [Experiment 058](../experiments/058-impassable-highlands/README.md)
separates physical sampling from impassable location identities. Connected samples
with identical climate, vegetation, topography and resource attributes are one
indivisible node for administrative partitioning, then one location; their
continuous relief and drainage are retained. TR46's 668 impassable samples yield
88 compatible locations. This is not one global wasteland or a claim to reproduce
Paradox's exact authoring algorithm.

The initial primary height sources also sample fine eroded detail from the three
installed ordinary mountain height layers. Integer, band-independent sampling
follows elevated land, fades near river lines and low terrain, and continues into
periodic edge padding. This supplies the missing fine-detail role noted under
the V1-era limits above; it does not add separate mesh objects. The exact blend, resource
bounds, local numeric/visual comparison and remaining engine uncertainty are in
058. Neither biome grouping alone nor a height-source plot proves final game
appearance. No engine files are patched and no derived game resources are shipped
with the generator.

## Natural wastelands (1.3.0 / epoch 64)

Until epoch 63 the wastelands were the highest cells of the relief (the share set by **Wasteland
share**), so every one was a mountain. [V-LOCAL EU5 1.4.7, build 26377361, 2026-11-13] The game's own
map has 1,821 impassable locations among 22,718 land ones (8.0 % of the locations, 38.4 % of the
land area, because a few are enormous: the largest is 1.14 million pixels, the median 632 and the
5 % largest hold two thirds of the area). By area they are 30.7 % flat wastelands (tundra, taiga
and jungle hearts), 24.5 % mountains, 14.3 % plateaus and mesas, 10.7 % hills and 10.0 % dunes, under
36 % sparse, 26 % forest, 23 % desert, 9 % jungle and 5 % woods. Mountains are less than a quarter.

`barrens.py` (called from `eu5_biomes.assign_biomes` once climate and vegetation are drawn, from
epoch 64, for every land, the Wall's side continents included) plans the wastelands in five steps;
the construction is [INFERRED] from those measurements, not a copy of Paradox's authoring.

1. **Calibration from the installed game, by area.** For each patch (a climate group of
   `biomes.txt` and a vegetation) and kind (mountain, hills, plateau, flat, dune) it reads the part
   of the patch's land that vanilla wastelands cover, and the size of every vanilla wasteland by
   kind. A patch below 150,000 pixels gives no rate (a few dozen locations are noise, not a share).
   It also reads, per kind, how much likelier the area of the game's wastelands is to touch the sea
   than the land of their own patches (`Calibration.shore`; [V-LOCAL 1.4.7] flat wilds 1.48, plateaus
   1.07, mountains 0.99, dunes 0.94, hills 0.33): 21 % of the game's wastelands (23.5 % of the
   Old World's locations, 27.7 % of its wasteland area) touch the sea, as a fifth of its land does,
   but the kinds differ.
2. **Quotas.** The world's budget (land cells × the wasteland share, as before) is divided between
   the (climate, vegetation, kind) classes in proportion to rate × the patch's area in the world, by
   exact capped water-filling (`fractions.Fraction`, a class never takes more than 80 % of what it
   can hold in the first round) and rounded by systematic sampling, so the sum is exact. A class
   exists only where `biomes.txt` draws the triple by a biome of its own with materials, never by
   `default_biome`.
3. **Suitability.** A cell can only be a kind its ground allows: the ground that the game's
   locations most like it vote for it (`vote_grounds`, over all the land before the plan; mountains,
   hills and plateaus allow their kind, flatland and wetlands a flat wild or dunes). The plan first
   read fixed heights (14,000 and 11,000) and the cell's own height spread, which grows with the
   cell; with the vote `gady3byywf` has 215 mountain, 294 flat, 61 hills, 16 plateau and 80 dune
   wastelands where it had 237, 284, 56, 10 and 79, and 125 of its 666 at the sea where it had 104
   (vanilla: a fifth), while under the fixed heights a relief with higher smooth interiors, tried
   below, had cost 94 flat wilds and added 68 mountains [V-EXEC 2026-11-13]. Within that a cell
   ranks by what the kind is: dry smooth ground for dunes, wet lowland for jungle, cold ground for
   tundra, the highest roughest ground for mountains, each blended 70/30 with a smoothed
   regional noise, so that districts favour a kind. Smooth and rough are the ruggedness of the
   ground a cell lies on (`cell_ruggedness`), read the same whatever the cell's size: its own height
   spread grows with the cell, and on mountain, hills and plateau ground the larger cells had more
   of it (Spearman 0.18–0.34 on `gady3byywf`); with the ruggedness the hills wastelands follow their
   patches at every cell size [V-EXEC 2026-11-14]. Coastal cells are candidates like any other, and
   the seeds of a class are drawn from two strata, the cells at the sea and the others, so that the
   class's cells at the sea keep the share its candidates have there times the kind's `shore`
   factor, whatever the units grow into (a deficit rule, `_Planner._next_seed`).
4. **Units.** Vanilla wastelands are mostly single locations with a heavy tail of huge ones, and
   touching wastelands of identical attributes are one location (`wastelands.location_units`). A
   unit draws its size from the vanilla sizes weighted by area (a random vanilla wasteland *pixel*
   picks the location, so the area, not the count, sets the shape), converted to generated cells,
   and grows from the best cell over cells of one class. No unit touches another of the same
   attributes, so the sizes drawn are the sizes written.
5. **Reachability.** A cell becomes wasteland only if every passable cell still reaches a coast
   without it (a breadth-first test per cell; cells that are the last way are never taken).

Two kinds of cell are fixed beforehand: land at a polar edge of the map, which is always
impassable and comes on top of the budget, and the cells the Wall's core runs through
(`NewWorld.barrier`, one chain from pole to pole, recorded by `newworld._wall_cells`, kept by the
land cache and renumbered by `ports.relabel`), which are wastelands of the topography their height gives and count in the budget.
The land on either side of the Wall is planned like any other. Both carry the topography their
height gives (`legacy_topography`), as do the passable pockets that the fixed cells enclose (they
reach no coast and are sealed, `unreachable_forced`). The plan fails with `WastelandPlanError` if a
passable cell would reach no coast.

**Order of the stages.** The ports, docks and strait crossings of the coast stage are made for the
passable land beside the sea (`ports.coast_links`, `crossings.sections`), so from epoch 64 the
plan comes first: the stage `land character` (`eu5_nw_export._land_character`) draws the climate,
vegetation, wastelands, topography and raw materials of the *land* cells, and `settle_coast` and
`shape_water` then run on a world that already has its final classes. This works because the
generator numbers land cells first and the coast stages only fold sea cells together (`relabel`
keeps the land cells' numbers; `_land_count` checks it); the climate of the waters that remain is
drawn later by the stage `biomes and rivers` (`water_climates`). Epoch 63 and older keep the old
order (the highest cells become wasteland at the land stage and the biome model runs after the
coasts). The cost is a stage on the critical path (about 6 s) and that the coast stages no longer
overlap the wait for the vanilla climate: about 15 s of a 4-minute export [V-EXEC].

The topography written is the kind's: `mountain_wasteland`, `hills_wasteland`, `plateau_wasteland`,
`flatland_wasteland` or `dune_wasteland` (biome `desert_rock_wasteland`). Wastelands are named for
their terrain, in every language (`wording.HIGHLANDS`, `WILDS`, `DESERT`; a mountain, hills or
plateau is a *Highlands*, a flat one *Wilds*, a dune a *Desert*), and both windows draw each with
its own relief and colour (`lenses.json`).

[V-EXEC 2026-11-13] The reference world (supercontinent, seed 20261102, 9 % wastelands): budget 583,
no shortfall; 116 dune, 14 plateau, 298 flat, 48 hills and 107 mountain cells, in 122 units (the
largest 50 cells), every written location a valid biome (`default_biome_locations` 0). 65 planned
cells (11 %, 13 % of the planned area) touch the sea, against 14 % of the land's cells and 24 to 28 %
of the game's wastelands: the generated coast is a rough ramp (65 % of its cells have the ground of
hills, against 29 % of the inland ones), so few cells at the sea can be flat or dune wastelands and
the share follows what the ground allows. The same plan at 30 ‰ puts 19 % of its cells at the sea,
at 200 ‰ 12 % and at 500 ‰ 14 %. The composition follows the vanilla rates patch by patch but is
shaped by the generated relief, which has few smooth high cells, so plateaus are rarer than in the
game.

**Limits.** At the highest **Wasteland** the world holds a few per cent fewer wastelands than
asked (bench, same inputs: 200 ‰ 11 of 1,297 cells short; 500 ‰ 106 of 3,243), because every passable
location must still reach a coast; the stats record `shortfall`. A mountain range painted in a land
image is high ground, which the plan favours for mountain wastelands, but it is not made impassable
throughout.

## Drainage before cells (1.3.0 / epoch 64)

An audit of the epoch-64 world `gady3byywf` (continents, seed 20261115) against the vanilla Old
World and the vanilla Americas in the same map columns [V-EXEC 2026-11-13, EU5 1.4.7, build 26377361]
traced several shortfalls to the order of the stages: the land cells were grown from a uniform
scatter of seeds beside the relief, before any river, climate or drainage existed.

| Measure | Old World | Americas | Epoch 64 before this section | After it: `gady3byywf`; seed 42 |
|---|---|---|---|---|
| Location size p90/p10 (CV) | 9.9 (1.12) | 8.7 (0.80) | 2.35 (0.37) | 7.6 (0.98); 6.6 (0.87) |
| River pixels on a location border (all land pixels) | 302 ‰ (100) | 218 ‰ (79) | 73 ‰ (69) | 304 ‰ (69); 300 ‰ (68) |
| Largest river network, share of all river pixels | 63 ‰ | 199 ‰ | 49 ‰ (second world 44 ‰) | 75 ‰; 84 ‰ |
| Climate regions: mean cells, same-climate contacts | 14.3, 808 ‰ | 9.0, 750 ‰ | 59.4, 916 ‰ | 8.3, 678 ‰; 8.0, 683 ‰ |
| Semi-arid and cold arid land (this audit's count; for the count of the passable locations used below, vanilla holds 116 ‰ in both) | 93 ‰ | 86 ‰ | ≤ 17 ‰ | 63 ‰; 48 ‰ |
| Mountain locations at the sea; coastal flatland / hills / wetlands | 137 ‰; 497 / 254 / 106 ‰ | 153 ‰; 425 / 221 / 160 ‰ | 66 ‰; 255 / 384 ‰ | 78 ‰; 461 / 186 / 196 ‰; seed 42: 94 ‰; 485 / 211 / 124 ‰ |

Seed 42 is the code of `gady3byywf` with that seed (`RNW1-040G0-00000-00001-A041G-0013C-NR0`); the
vanilla climate regions are read over the columns of `gady3byywf`.

The median size of a class's locations over the median of its region, in the same worlds and in
two more epoch-64 worlds, a Wall world (`vnnvge53ci`) and a drawn land (`62g4bmw4xx`):

| Class | Old World | Americas | `gady3byywf` | Seed 42 | Wall | Drawn |
|---|---|---|---|---|---|---|
| Desert vegetation | 1.52 | 1.45 | 1.29 | 1.60 | 1.50 | 1.52 |
| Arid climate | 1.55 | 1.03 | 1.30 | 1.62 | 1.43 | 1.54 |
| Subpolar climate | 3.12 | 1.48 | 1.82 | 1.64 | 1.64 | |
| Oceanic climate | 0.54 | 0.69 | 0.69 | 0.69 | 0.67 | 0.84 |
| Mountains | 0.86 | 0.61 | 0.87 | 1.00 | 0.87 | 0.71 |
| Plateau | 1.58 | 1.48 | 1.32 | 1.16 | 1.14 | 1.27 |
| Hills | 0.83 | 0.91 | 1.12 | 1.12 | 1.08 | 1.21 |
| Wetlands | 1.14 | 1.07 | 0.76 | 0.85 | 0.72 | 0.78 |
| Coast (0–40 px) / far inland (300+ px) | 0.70 / 1.80 | 0.59 / 2.06 | 0.74 / 2.05 | 0.75 / 1.20 | | |

From epoch 64 each is changed at its cause, each behind its own switch of `rnw.epoch`:

* **Cordilleras** (`CORDILLERAS`, `relief.py`). The coasts of each landmass that face the way of
  its plate (a direction a per-seed vector and two slow noises give, broken up by a local noise)
  are active margins. A cordillera stands 100–260 pixels inland of them; the land falls away from
  them by up to 1,800 units over 2,400 pixels, and the inner chains of that foreland keep a fifth of
  their strength. The distance is measured on a 16-pixel grid within the landmass, and a grid cell
  of mostly water takes the value of the nearest land cell: blended towards the cap over the sea, it
  had raised a false ridge and a step of the tilt along every shore near an active coast, so the
  coastal locations were two and a half times as rough as the inland ones (median 867 against 349)
  and 458 ‰ of them hills. An axis 50–150 pixels inland with a 10-pixel ramp to the sea put half of
  all mountain locations within one step of the coast (vanilla 26–35 %). The share
  of land above 16,000 units stays near 136 ‰.
* **Rivers first** (`RIVERS_FIRST`, `watersheds.py`, `newworld.py`). The relief is made first; the
  domain's own rain (the seasonal model on the domain, all but its land and lakes being sea)
  drains it in the export's watershed domains; the cells are seeded with a spacing the land sets
  and grown up to the 300 ‰ largest rivers by flow, whose pixels then join the cell beside them, and
  the border wobble leaves the pixels within 24 pixels of those rivers alone. The export draws the
  same rivers again from the same inputs, so they are the borders.
  The spacing is read from the installed game (`eu5_biomes.size_model`, built by the export from
  the vanilla map and part of the land cache key). Each passable vanilla land location of the Old
  World and the Americas, farmland left out as in the vote, carries its size as exact 64ths of an
  octave over the lower median of its region, and the pixel-weighted mean of the features of the
  64-pixel blocks it covers: latitude, rain, mean height and the share of coast. Every 64-pixel block
  of generated land reads the same features the same way (`block_features`), takes the (climate,
  vegetation) pair the climate vote would choose there with vanilla's weights (the same k-NN) and the mean
  size of the 32 vanilla locations of that pair nearest to it (`class_sizes`): a desert is as large
  as vanilla's deserts where vanilla's land is like it, a wet coast as small as vanilla's. The pairs'
  votes are weighed by `calibrated_weights` (below), not matched to the world as the vote's own are.
  Since 2026-11-15 the nearest locations are sought in latitude and the summer's and winter's rain
  only (`SIZE_COLUMNS`), the ground and the coast moving the size instead (below), and only the
  locations of landmasses of 100 locations or more size a class (`MAINLAND`): those of smaller
  islands lie 0.5 to 1.7 octaves below their pair, as large as their islands allow. The figures of
  this paragraph and the next are of the model before that. Left
  out one location at a time, the model gives vanilla deserts 1.41 of the median (they are 1.48),
  arid land 1.47 (1.51), subpolar 2.45 (2.38) and tropical land 0.98 (1.02), and chooses desert for
  1,197 locations where 1,194 are; R² 0.48 [V-EXEC 2026-11-13]. A block's ground moves its size
  too: voted as the cells' is (`vote_grounds`, below; the block reads its height, the spread and
  the bend of its height, `block_relief`, its rain and its distance to the sea), it takes the mean
  amount by which vanilla's locations of that ground, each read without itself, lie off the size of
  their class
  (`SizeModel.offsets`): mountains 0.90 of it, plateaus 1.05, wetlands 1.07, hills and flatland
  1.00. Class, height and distance to the sea already carry most of vanilla's difference between
  grounds. Adding the ranks of the spread and the bend to the size neighbours themselves fitted
  vanilla a little better (R² 0.50) but made the generated plateaus smaller (`gady3byywf` 1.32 to
  1.11) and the sizes less varied (p90/p10 7.6 to 7.0), so it is not used [V-EXEC].
  A least-squares fit of size on the same four features (R² 0.34) had left this world's deserts at
  0.96 of the median: the zonal rain barely tells a vanilla desert (the share of desert and sparse
  locations falls only from 0.30 to 0.13 from the driest to the wettest of seven rain bins), so a
  size read from the features alone loses the class, while choosing the class first does not.
  Features read at a location's centre had made coastal locations read as coast and the large ones
  as inland, so the training and the query both read blocks.
  **Sized by what each location becomes** (2026-11-15). Sized block by block, a location's class
  was another than the block's for 43 % of the cells, and its ground for 58 % of the wetlands:
  generated deserts and cold dry land came out near the median and wetlands small. The land is now
  cut twice (`watersheds.cell_spacing`): first cells, grown on the block sizes, are voted as
  the export will vote the final ones, each on its own centre and pixels (`eu5_biomes.cell_sizes`:
  the pair with matched weights, the ground with `vote_grounds`), and each sizes the land it lies on
  by the mean of the 32 vanilla locations of that pair nearest in latitude and rain, moved by the
  mean amount vanilla's mainland locations of its ground lie off that, inland or on the coast
  (`SizeModel.offsets`, two rows: inland mountains −0.16 of an octave, plateaus +0.07, hills
  +0.05, wetlands +0.08, flatland +0.04; on the coast +0.11, −0.02, −0.10, −0.13, −0.09); the
  final cells are then seeded on that field. On `4aomqqsg6b`'s land 927 ‰ of the final locations
  get the ground their size was read for, and the export's coastal locations are the cells' own
  (997 ‰). The second cut costs the export of that world 334 to 384 seconds with four threads (the
  land cells 35 to 60); the memory floor (seed 42, one thread, `RNW_MEMORY=1500`) is 6.74 GiB.
  **Neighbours change size gradually** (2026-11-15). Vanilla's neighbouring passable land locations
  differ by more than an octave in 99 and 107 ‰ of their pairs (Old World, Americas), by more than
  two in 4.5 and 3.9 ‰ and by more than three in 0.1 ‰, and 0.6 and 1.0 ‰ of them are under a quarter
  of their neighbours' median (whole locations, those with most of their pixels on the side, sizes
  and borders read on the full map; cut at the New World's columns, the cut ones had looked small
  and doubled the share over two octaves). Sized block by block, with seeds on a jittered grid that
  could put two within 0.15 of the spacing, the generated ones (`4aomqqsg6b`) did in 299, 64.5 and
  13.7 ‰, and 21 ‰ were under a quarter of their neighbours. The spacing is now graded (`grade_spacing`: a block's
  spacing exceeds a neighbour's by at most 0.3 pixel per pixel for the first cells,
  `FIRST_GRADATION`, and since 2026-11-16 0.5 for the final ones, `GRADATION`), taken in exact 64ths of
  an octave (`spacing_permille`, integer powers of two), and the seeds are thrown as blue noise
  (`spaced_sites`: candidates in a hashed order, each kept only beyond 0.758 of the mean of its and
  its neighbours' spacings); the border wobble shrinks with the spacing. A smooth settlement noise
  (`DENSITY_PERIOD` 800 pixels, `DENSITY_SPREAD`) then gives each world its denser and sparser
  regions, as vanilla's locations lie 0.74–0.87 of an octave off the size of their class, shared
  by neighbours (correlation 0.51–0.58). The spacing is scaled as a whole to keep the number of
  cells, and the polar bands keep three times the spacing; the land before them widens toward
  them at half that rate (`APPROACH_SLOWER`, since 2026-11-16) from half their area, and the
  settlement noise never narrows it, for their passable cells had bordered ordinary ones
  (51 of a world's 59 pairs more than three octaves apart lay there), and they stay the larger, as
  those at the map's edge become its wastelands. A seed grows at a speed in proportion to
  its spacing (`synth.grow_weighted`); grown at one speed, the cells of the largest spacings had come
  out at three quarters of their area, cut off by their denser neighbours.
  What remains: `gady3byywf`'s deserts are scattered patches, and part of their cells lie in blocks
  the vote reads as another class, so they stay at 1.29. Its tropical land is 1.56 of the median
  because 543 of its 1,536 tropical locations lie over 300 pixels from the sea; band by band (0.62,
  1.09, 1.60, 2.98 from the coast inwards) it follows the Old World's (0.84, 1.24, 1.90, 2.43).
  Seed 42's far inland is 1.20, not 1.8–2.1, because 701 of its 1,327 locations there are
  subtropical, at 0.92 (the Old World's far subtropical land: 0.89). The plateaus (1.14–1.32 against
  1.48–1.58) and wetlands (0.72–0.85 against 1.07–1.14) of this step were too small, from its
  relief, not the vote; with the worn relief and the matched votes (below) they are 1.42 and 1.16
  on `gady3byywf` and seed 42, and 0.83 and 0.76.
  With the cells sized by what they become and graded (whole locations of `qjkrrkxfot` and of the
  reference world): neighbours more than an octave apart 120 and 127 ‰ of the pairs, more than two
  7.0 and 7.9 ‰, more than three 0.7 and 0.3 ‰ (vanilla 99–107, 3.9–4.5 and 0.1), locations under a
  quarter of their neighbours' median 3.0 and 2.6 ‰ (vanilla 0.6–1.0), small ones mostly bordered
  by one four times larger 15.2 and 17.3 ‰ (vanilla 19.8–40.9); η² of log size by pair 0.213
  and 0.223, by pair and ground 0.365 and 0.372 (vanilla 0.189–0.314 and 0.380–0.384), its spread
  1.10 and 1.22 octaves (vanilla 1.23–1.24). Plateaus 1.30 and 1.34 of the median, hills 1.14 and
  1.07, wetlands 0.70 and 0.77, mountains 0.75 and 0.90 [V-EXEC 2026-11-15]. The pairs still over
  two octaves apart are grown, not planned: on `gady3byywf`'s grown cells their sizes differ by
  0.25 of an octave in the field and 2.0 in growth, the smaller cell 1.4 octaves under what its
  spacing gives (spread over all cells 0.88) [V-EXEC].
  Vanilla's ground does not make a location larger or smaller than its neighbours: against the
  adjacent flatland locations of the same pair and coast, its wetland, hill and plateau locations
  differ by −0.06 to +0.10 of an octave in both regions, its mountains by +0.04 to −0.09; its
  wetlands are larger overall because they lie where the land's locations are large. The generated
  coast did not behave so: `qjkrrkxfot`'s coastal wetlands were 0.32 of an octave smaller than the
  flatland beside them and its coastal hills 0.36 larger, and on four worlds' grown cells the
  coastal hills 0.30 larger (standard error 0.04). Both causes lay in a cell's own extent
  (C537, [V-EXEC 2026-11-15]):
  - The ground was voted on a cell's own readings, and the distance to the sea at its centre grows
    with the cell (rank correlation +0.58 among vanilla's coastal locations of one ground). The
    ground is now voted block by block (16 pixels) by vanilla's blocks, and a cell sums the votes
    of its land (`ground_field`). Read on vanilla, each block voted by the blocks of the other
    locations, coastal wetlands and hills come out 0.08 smaller and 0.03 larger than vanilla's in
    their pair, against 0.27 and 0.14 voted by location.
  - A thrown seed by the sea grew a cell the sea cut: a coastal cell's size followed its seed's
    distance from the sea (rank correlation 0.77; seeds within 0.15 of their spacing of it grew
    0.88 of an octave under their plan), and as the land rises from the shore the cells reaching
    inland took the hills' ground, those on the strand the wetlands'. A vote over a disk of the
    planned area around each seed changed nothing (coastal wetlands −0.23, hills +0.32 on the same
    cells), and neither did keeping the seeds back from the sea (coastal cells outgrew the inland
    ones and the land lost 7–9 % of its cells) or re-estimating the ground offsets. Now the seed of
    each cell beside water moves once to the centre of the cell it grew (Lloyd's relaxation of the
    shore, `watersheds.RELAX_STEPS`), and twice the speed of each such cell is corrected toward its
    planned share of the land it and its neighbours grew (`SHORE_FEEDBACK_STEPS`, `_shore_gains`:
    by the root of that share over its own area). The first version of this (C537) moved the seeds
    twice and sped every seed by the root of the land's share of its planned square; it evened the
    coastal hills (+0.05) partly by inflating every coastal cell, its coastal flatland 0.05 of an
    octave larger than the inland flatland beside it where vanilla's is 0.17 and 0.10 smaller
    (relaxed without the faster shore −0.06, not relaxed at all −0.24). Corrected toward the share
    of all the land, the coastal cells grew into the next row (+0.43); every cell corrected, the
    sizes evened out (neighbours more than an octave apart in 38 ‰ of the grown pairs, not 70–80);
    moved again after the last correction, +0.10. Moving every seed evened the coast no better and
    laid the land out in a lattice of diamonds, the shape the four-neighbour growth gives regular
    seeds.
  - The ground offsets of the size model (C538) were each ground's mean off its class over the
    whole map, and so mixed in its regions: a mountain region's locations are all small inland and
    all large on the coast, and the plan made inland mountain cells 0.21 of an octave smaller than
    the plain beside them and coastal ones 0.20 larger. They are now read against the land beside
    each location (`_local_offsets`: least squares over the contacts of two locations of one pair,
    one of them flatland), which puts vanilla's mountains 0.07 under the flatland beside them
    inland and on the coast, its hills 0.06 and 0.03 over it, its wetlands level with it and its
    coastal flatland 0.11 under the inland's. A coastal cell that grew large still reaches the high
    land behind the shore: among the coastal cells the share of mountain rises from 27 ‰ in the
    fifth smallest for their plan to 67 ‰ in the largest, and the corrected shore narrows that
    spread.

  Pooled over the four worlds' grown cells with all three and the smoothed climate (below): coastal
  flatland 0.015 of an octave smaller than the inland flatland beside it (its plan 0.007; vanilla
  0.17 and 0.10); against the flatland of their pair and coast, coastal hills +0.08 (standard
  error 0.02), wetlands −0.02 (0.03) and mountains +0.09 (0.04), inland hills +0.02, wetlands
  −0.06, plateaus −0.03 and mountains −0.09 (0.03), where before coastal mountains were +0.16 and
  inland ones −0.16; neighbours more than an octave apart in 70 ‰ of the grown pairs and more than
  two in 3.4 ‰ (80 and 4.1 before) [V-EXEC 2026-11-15].
  On whole locations of `uc6q6tihfq` (the land of `kkgvhey7ry`, its peoples rolled again):
  coastal flatland 0.05 of an octave smaller than the inland flatland beside it (vanilla's Old
  World 0.17, the Americas 0.10; `kkgvhey7ry` 0.06 larger); inland mountains −0.09 against the
  flatland beside them (vanilla −0.09 and −0.02; before −0.29), hills −0.00 (+0.01, −0.00),
  wetlands −0.06 (−0.05, −0.06), plateaus +0.04 (−0.05, +0.04); coastal hills +0.12 (+0.03,
  +0.09) and wetlands −0.09 (−0.03, +0.10); neighbours more than an octave apart in 88 ‰ of the
  pairs, more than two in 4.2 ‰, more than three in 0.3 ‰ (vanilla 99–108, 4.1–4.4 and 0.1;
  before 96, 4.2 and 0.3), locations under a quarter of their neighbours' median 0.7 ‰ (0.7–0.9)
  [V-EXEC 2026-11-15]. What remains: a single world holds too few coastal mountains to read (four
  here); pooled, they are 0.09 of an octave larger than the flatland beside them (standard error
  0.04; vanilla +0.04 and −0.05). The plan wants the coastal flatland 0.10 smaller than the inland,
  but the first cells, the blocks and the grading dilute the offset to 0.01 before the cells grow.
  This world's coastal hills (+0.12, `kkgvhey7ry` +0.03) lie at the top of vanilla's range; pooled
  they are +0.08. Neighbouring sizes now contrast less than vanilla's (88 ‰ of the pairs more than
  an octave apart, vanilla 99–108; the spread of the log sizes 1.08, vanilla 1.21–1.25). On the
  four worlds' grown cells the corrected shore takes 9 ‰ of that contrast (79 ‰ without it, with
  coastal hills +0.22 and mountains +0.31 and the spread of the coastal growth 0.45 instead of
  0.36) and the smoothed climate 4 ‰ (74 ‰ unsmoothed) [V-EXEC 2026-11-15]. The planned variety
  was not short, as this paragraph first said: the cells' own targets differ by more than an
  octave in 103–107 ‰ of the pairs, as vanilla's do, and the gradation held the plan to 21 ‰
  (C539, below).

  **Coastal mountains and contrast** (2026-11-16, C539). Over eight worlds' grown cells (seeds
  20261115, 42, 7, 1234, 99, 2026, 31337 and 555) the cells of C538 left the coastal mountains 0.09
  of an octave larger than the coastal flatland of their pair beside them (standard error of the
  worlds' means 0.025) and neighbours more than an octave apart in 69 ‰ of the pairs, the polar
  bands left out. Four causes, each changed where it arises:
  - A shore cell was corrected toward its share of its own neighbourhood, and that share depends
    on whom it borders: a coastal mountain cell borders more inland cells, which the sea does not
    cut, and was given 0.055 of an octave more land for it. The final cells beside the sea are now
    corrected toward their planned square at the density of the inland cells whose seeds lie
    within four blocks of theirs, moved by vanilla's offset of their ground on the coast against
    its inland flatland (`watersheds._density_gains`, `eu5_biomes.coastal_offsets`, read on the
    cells as they grow; a lake shore takes no offset). The first cells keep their share.
  - A coastal cell planned large reaches the high land behind the shore and is voted mountain, so
    the steeper the first cells' sizes change, the larger the blocks the coastal mountains are
    planned on: +0.005 of an octave against the coastal flatland of their pair at 0.3 pixel per
    pixel, +0.04 at 0.4, +0.09 at 0.5, and the final cells follow their plan. The first cells keep
    0.3 (`FIRST_GRADATION`); the final cells, which no vote reads before they are drawn, are graded
    at 0.5 (`GRADATION`), so that more of the cells' own variety reaches the plan (pairs over an
    octave 21 → 46 ‰).
  - A slow seed among fast ones was hemmed in: the smaller cells of the inland pairs over two
    octaves had a neighbour planned 0.73 of an octave larger (0.34 for all inland cells), their
    seeds as far from the others as any, and grew 1.1 octaves under their plan while the larger
    grew 0.6 over. An inland final cell grown more than three quarters of an octave off its plan
    at the density round it is now corrected back to that band (`SIZE_BAND`); corrected all the
    way, every cell had evened the land (38 ‰ over an octave).
  - The land before the polar bands widened at the full rate, and the settlement noise, applied
    after, narrowed it further: the spacing doubled within three blocks where the cells are small,
    and 28 ‰ of the pairs of cells by the bands were more than two octaves apart, ten times as many
    as elsewhere. It now widens at half the rate and the noise no longer narrows it: 5 ‰.

  Pooled over the eight worlds' grown cells: coastal mountains +0.03 against the coastal flatland
  of their pair (standard error 0.03; vanilla +0.04 and −0.05), inland mountains −0.05 (−0.09,
  −0.02), coastal hills +0.04 (+0.03, +0.09), inland hills −0.00, coastal and inland wetlands −0.03
  and −0.04, inland plateaus −0.03; coastal flatland 0.02 smaller than the inland beside it (0.00
  before); neighbours more than one, two and three octaves apart in 87, 3.0 and 0.11 ‰ of the pairs
  (69, 2.9 and 0.16 before), under a quarter of their neighbours' median 0.13 ‰ (0.68). Tried and
  worse are listed at `watersheds.RELAX_STEPS` [V-EXEC 2026-11-16].
  On whole locations of `d7w4gsxhse` (the land of `uc6q6tihfq`, its peoples rolled again):
  neighbours more than an octave apart in 94 ‰ of the pairs, more than two in 3.9 ‰, more than
  three in 0.1 ‰ (vanilla 99–107, 3.9–4.4 and 0.1; `uc6q6tihfq` 88, 4.2 and 0.3), under a quarter
  of their neighbours' median 0.1 ‰ (vanilla 0.6–1.0; before 0.7); its grown cells contrast the
  least of the eight worlds' (80 ‰ over an octave; the others 81–96); seed 1234's world
  (`py4hwjlbok`, whose grown cells contrast as the eight worlds' do on average, 87 ‰) has 97, 3.7
  and 0.0 ‰ (86, 3.8 and 0.1 before). Coastal hills +0.09 and +0.05 against the flatland beside
  them (before +0.12 and +0.14), coastal wetlands −0.01 and −0.05; inland hills −0.01 and +0.01,
  wetlands −0.01 and −0.16, plateaus −0.01 and +0.01; coastal flatland 0.03 and 0.01 smaller than
  the inland; the climate of `d7w4gsxhse` as before (177 ‰ of neighbours differ, 14 ‰ alone).
  Inland mountains beside flatland of their pair are −0.18 and −0.24 there (62 and 66 locations;
  before −0.09 and −0.03), while all inland mountains keep their median size (0.77 and 0.97 of the
  passable median, as before) and the eight worlds' grown cells put them at −0.05 (−0.07 before).
  Over six worlds' whole locations (these two and seeds 42, 7, 99 and 2026) they are −0.10 (385
  contacts; the worlds' means from −0.24 to +0.20, standard error 0.07; vanilla −0.09 and −0.02):
  these two lie in the low tail. The six worlds' neighbours differ by more than an octave in 94 to
  104 ‰ of the pairs (mean 99), by more than two in 3.7 to 4.4 ‰, by more than three in 0.0 to
  0.1 ‰, as vanilla's do; coastal hills +0.07, coastal mountains −0.03 (64 contacts), inland
  wetlands −0.08 and plateaus −0.06 against the flatland beside them; the coastal flatland 0.03
  smaller than the inland [V-EXEC 2026-11-16].
  The band leaves fewer locations under a quarter of their neighbours' median than vanilla's (0.0
  to 0.6 ‰ on the six worlds, vanilla 0.6–1.0; a handful of locations per world). What remains:
  the coastal flatland is planned 0.10 of an octave smaller than the inland, but the first cells
  and the blocks dilute that to 0.02–0.03 (vanilla 0.10–0.17).
* **Open climate** (`OPEN_CLIMATE`, `eu5_biomes.py`). The vote learns from the vanilla Americas as
  well, leaves farmland out instead of reading it as grassland, and is smoothed over the location
  graph once, its weights matched through that smoothing (below). A plurality of 32 neighbours
  seldom names a class that is rare among them: each vanilla location read without itself, the
  vote gave 72 ‰ of them a semi-arid or cold arid climate where 91 ‰ have one, and too many a
  Mediterranean one. The pairs' votes are therefore weighed so that
  the vote, each location read by its 32 nearest others, chooses every pair about as often as vanilla
  holds it (`calibrated_weights`: ten rounds from the cube root of the inverse of the pair's share,
  each multiplying a weight by the square root of its locations over the locations it was chosen
  for). Calibrated on the Old World alone, it gives the Americas 89 ‰ of those climates, which hold
  87 ‰ (the cube root alone: 82 ‰) [V-EXEC 2026-11-13]. The neighbour search runs on eight threads
  and in integers (|a|² + |b|² − 2 a·b, the same distances in a third of the time); the two
  calibrations, of the vote and of the size model, take about a second each.
  Matched to each world (below), the vote gives a world the climates the neighbours of its
  locations hold: cold semi-arid and cold arid on 117 ‰ of seed 42's passable locations and 80 ‰ of
  `gady3byywf`'s, where vanilla's Old World and Americas hold 116 ‰ each, counted the same way. How
  much of a world is cold and dry is its geography: only 5 % of `gady3byywf`'s land between 30° and
  55° lies over 400 pixels from the sea (the Americas 13 %, the Old World 19 %) and its high land
  lies near the equator (a median 10°, where the Americas' dry highlands lie at 15–21°), wet all
  year as the equatorial Andes are [V-EXEC 2026-11-14].
  Unsmoothed, the vote speckled the land: on `kkgvhey7ry` 51 passable locations in a thousand had a
  climate none of their neighbours shared (vanilla's Old World 13, the Americas 30), 133 one that
  fewer than a third of them shared (42, 83), and a climate region held 9.3 locations (26.3, 13.0);
  the dry and Mediterranean climates were the scattered ones (100–200 ‰ of their locations alone).
  Three rounds had eaten those climates (C534) because a plurality of smoothed votes again favours
  the class most of the neighbours hold. Now the votes are smoothed once (`OPEN_CLIMATE_ROUNDS`,
  `OPEN_VEGETATION_ROUNDS`) and the weights are matched to the world through that smoothing
  (`smoothed_pairs`), so the smoothed vote keeps each pair's share: over four worlds' cells 13 ‰
  stand alone, a region holds 20 cells, and the semi-arid, cold arid and Mediterranean land is
  203 ‰ where the neighbours hold 196 ‰ (unsmoothed 199 ‰); two rounds left 7 ‰ and 27 cells but
  drifted twice as far from the shares (24 ‰ against 16 ‰) [V-EXEC 2026-11-15]. On the whole
  locations of `uc6q6tihfq` 14 ‰ stand alone, 42 ‰ share their climate with fewer than a third of
  their neighbours, a region holds 19.1 locations and 176 ‰ of the neighbours differ in climate
  (vanilla 148 and 215; `kkgvhey7ry` 277) [V-EXEC 2026-11-15]. The first cells are voted the same
  way over their own contacts (`cell_pairs`), so they are still sized by the class they will have.
  The original calibration counted each vanilla location once. That underrepresented large
  arid areas, especially the desert wastelands of North Africa. The current calibration takes
  readings of seasonal rain, local height, latitude and coast distance every 48 raster pixels
  and uses the climate and vegetation at each point. A pair that falls entirely between grid
  points keeps one reading at its largest donor location. The same calibration supplies the
  first cell-size vote and the final biome vote. The output depends on the generated land
  and its seasonal circulation, with no target desert area per continent.
  [V-EXEC C550] On the owner's combined world with the required connection to Asia, desert
  cover across Africa's 20–32° N belt rose from 21.47% to 42.19% of land pixels, and arid or
  semi-arid climates from 53.45% to 74.54%. Vanilla Africa has 83.88% desert and 99.71% dry
  climate in this belt. South of the equator at 20–32° S, generated Africa's desert cover rose
  from 27.26% to 43.84%. In Africa's 0–10° N band it went from 0.10% to 0.00%. In the same
  world, desert cover at 20–32° N went from 20.44% to 29.43% in generated America. The
  percentages compare compiled location templates over the full raster, including wastelands.
* **The ground voted** (`ROUGH_HILLS`, `eu5_biomes.vote_grounds`). The ground of the passable land
  is voted, as its climate is, by the 32 vanilla Old World locations nearest in four readings of the
  height the decals show (the worn relief, below), taken as they are and scaled by vanilla's spread:
  mean height, ruggedness and roughness (both below) and distance to the sea; each ground's votes
  weigh what makes vanilla read as it is, matched to the world's own land (below), and a desert is
  never wetland. The 64-pixel blocks of the size model are voted the same way, with vanilla's weights.
  Read on vanilla itself, each location without itself, the hand-made ranks that came before
  (height plus twice the spread for mountains, rain against height and the sea for wetlands) named
  the ground of 635 Old World locations in a thousand and 597 in the Americas and 19 % of the
  wetlands rightly; the vote names 926 and 660 and 79 % of the wetlands, and rainfall as a fifth
  reading adds nothing (Americas 640) [V-EXEC 2026-11-13, 2026-11-14]. On the generated worlds the
  coastal wetlands fell from 187–222 ‰ of the coastal locations to 81–196 ‰ (vanilla 106 and 160)
  and `gady3byywf` has 70 wetlands over 120 pixels from the sea where it had none.
  The relief of this step put the generated land's lowest ground at the coast: vanilla's wetlands
  are its lowest land (median height rank 0.08–0.11) and a fifth of them lie in the farthest
  quarter from the sea, its plateaus are high (0.78–0.84) and far from the sea, and that quarter is
  high (0.59–0.65), while the generated one had a rank of 0.47, being the cordilleras' foreland,
  where the great rivers also gather. Raising that foreland directly (narrowed to 900 pixels, a rise
  with the distance from the sea, tablelands on noise of 700–2,000 pixels or kept off the trunk
  corridors of a first drainage, a cordillera nearer the coast) split the largest river networks
  (81–84 ‰ of the river pixels down to 45–68 ‰) or put a third of seed 42's mountains at the sea
  [V-EXEC 2026-11-13]. The worn relief (below) reverses the order instead.
* **Rough hills** (`ROUGH_HILLS`, `relief.cell_roughness`). Hills are ranked by how much a cell's
  height bends: the mean of |h(p + d) + h(p − d) − 2 h(p)| over `HILL_STEP` = 8 pixels along the
  rows and the columns whose two ends are land. A slope bends not at all, so the ramp up from every
  coast no longer reads as hill country, and the measure does not grow with the cell. The spread
  about a cell's best-fitting plane, used first, grew with the cell and made hills the largest
  locations (1.32 of the median, coastal hills 327 ‰); the bend gives 1.02 and 278 ‰ on the same
  world. For the same reason mountains (height plus twice the spread) and plateaus (height less
  three times the spread) were then ranked, and the vote now reads, the spread of the ground a cell
  lies on, the mean over its pixels of the spread of the height in their 64-pixel block
  (`cell_ruggedness`), not the cell's own: the variance of a fractal relief grows with the area
  read, so the largest cells had become mountains and the smallest plateaus (mountains 1.00–1.08 of
  the median and plateaus 0.96–0.99, vanilla 0.61–0.86 and 1.48–1.58).
* **Worn relief** (`BASINS`, `TABLELANDS`, `basins.py`, `relief.py`). The relief that the
  cordilleras and the noise give is the structure; its drainage is planned on it first and the land
  is then worn down along that drainage, as real continents are: a graded bed rises from the mouths,
  200 units below the sea, up the drainage tree by the landmass's gradient over the square root of
  each cell's catchment, and the base of the land is lowered to it (less on high ground, not on the
  old shields a slow noise places), so the great rivers spread broad low plains far inland, the
  plains nearest the sea and the deltas lie at its level, and the land between the basins stays
  high. The hills' spread is added after the plan, outside the valley floors of the rivers of 40
  cells or more and within the height band of hill country, so it cannot split the basins and the
  larger rivers climb no more often than on the relief they were planned on. Plateaus are broad
  tablelands (their noise raised over 4,000–9,000 instead of 9,800–14,700), which the worn relief
  keeps: the five largest networks hold 301 and 253 ‰ of the river pixels of `gady3byywf` and seed
  42 against 292 and 237 ‰ without them. The ground is voted on the height the decals will show
  (`eu5_terrain.land_surface`: the relief, its detail and its coastal cap through the writer's own
  kernel, without the stamps), as vanilla's is read from its primary heightmap; read on the raw
  relief, hill country had looked like flatland (82 ‰ hills). By full export with the matched votes
  (below) [V-EXEC 2026-11-14, vanilla in `gady3byywf`'s columns]:

  | Measure | Old World | Americas | `gady3byywf` | Seed 42 |
  |---|---|---|---|---|
  | Mountains / plateau / hills / flatland / wetlands, ‰ of land locations | 104 / 117 / 202 / 449 / 57 | 114 / 129 / 209 / 366 / 75 | 98 / 111 / 188 / 497 / 55 | 118 / 154 / 229 / 395 / 37 |
  | Median size over the region's: plateau / hills / wetlands / mountains | 1.58 / 0.83 / 1.14 / 0.86 | 1.48 / 0.91 / 1.07 / 0.61 | 1.42 / 1.08 / 0.83 / 0.82 | 1.16 / 1.10 / 0.76 / 0.94 |
  | Wetlands among coastal locations; mountains touching the sea | 106 ‰; 137 ‰ | 160 ‰; 153 ‰ | 115 ‰; 46 ‰ | 88 ‰; 82 ‰ |
  | Largest / five largest river networks, of river pixels | 63 / 264 ‰ | 199 / 423 ‰ | 137 / 300 ‰ | 94 / 250 ‰ |
  | Size spread p90/p10; river pixels on a location border | 9.9; 302 ‰ | 8.7; 218 ‰ | 7.6; 306 ‰ | 7.2; 293 ‰ |

  Seed 42 is the higher continent (half its land above 9,200 units against 7,900; 206 ‰ of it below
  6,600 against 271 ‰), so it has fewer of the low coasts and plains where wetlands lie. Mountains at
  the sea are fewer than vanilla's because the cordillera stands a location inland of an active
  coast; a random continent need not have coastal ranges at all.
* **Matched votes** (`OPEN_CLIMATE`, `ROUGH_HILLS`, `eu5_biomes.matched_weights`). Weights
  calibrated on vanilla make the vote read vanilla's own locations as they are, but a world's land
  lies otherwise over the readings, and there a plurality again gives a class that its neighbours
  hold in part fewer rows than they hold of it. Each world's climate and ground votes are therefore
  matched to its own locations: the rounds of the calibration, towards the rows that the neighbours
  of its locations hold of each class (their rank-weighted votes per location, summed), so that a
  world has as much of a class as land like its own holds, not vanilla's shares. On vanilla itself
  the plurality, the neighbours and the truth agree (wetlands 60, 59 and 61 ‰ of the Old World's
  passable locations); on seed 42 the plurality gave 31 ‰ of wetlands, 213 ‰ of hills and 151 ‰ of
  mountains where the neighbours hold 39, 235 and 134, and 91 ‰ of subtropical climate for 122
  [V-EXEC 2026-11-14]. Held out where the truth is known, the Old World voting the Americas, the
  matching takes the error of the shares (half the summed differences) from 189 to 165 ‰ for the
  climates and from 88 to 65 ‰ for the grounds (mountains 189 to 166 ‰ where 128 are, hills 174 to
  203 ‰ where 228 are, subtropical 87 to 106 ‰ where 142 are), and leaves the share of locations
  named rightly as it was (climate 398 and 395 ‰, ground 660 and 660 ‰) [V-EXEC 2026-11-14]. The
  ground is voted once over all the land, for the wasteland plan and the topography alike. By full
  export, `gady3byywf`'s mountains went from 118 to 98 ‰ of its land
  locations, its hills from 168 to 188 ‰ and its cold dry climates from 72 to 80 ‰; seed 42's
  wetlands from 29 to 37 ‰ (88 ‰ of its coastal locations, from 77), its hills from 205 to 229 ‰
  and its mountains from 139 to 118 ‰.

* **Locations the game can draw** (`BOUNDED_CELLS`, `watersheds.MAX_LAND_PX`, C555). EU5 lays a
  town or a city out on a grid of primitives (`SPrimitiveData`, 264 bytes each) whose scratch array
  it keeps on the stack of a worker thread of 4 MiB. Sara, the largest city of a generated world
  (28,154 pixels), asked for 16,719 of them (4.4 MB) and the game died on opening its details, twice,
  at the same instruction with the same count [V-EXEC 2026-11-23, minidump registers]. The count
  against the area is read at that one location (0.594 a pixel, a limit near 26,000 pixels
  [INFERRED]); a count growing with the area to any power above an eighth stays under the stack at
  15,000 pixels, above a fifth at 20,000. A location becomes a town or a city by its people alone
  (`common/location_ranks`: 5 and 30, no area), so a rank refused at the start would not bind a city
  founded in play, and the bound has to hold for every passable location, whoever lives there.
  Vanilla's passable lands are mostly small and the few large ones are empty: of its 21,114, 20 are
  above 15,000 pixels and 12 above 26,000 (arctic and desert, with nobody in them); its largest town
  or city has 4,882 pixels, and the largest location with the people of a city (30) 16,931, which
  the game may or may not draw as one [V-LOCAL 1.4.9, 1337 start]. The generator's worlds are about
  three times the size of vanilla's in every class (the median tropical flatland has 2,414 pixels,
  vanilla 826) and had 9 ‰ of their land locations above 15,000 pixels, vanilla 0.9: of four worlds'
  8,100 to 8,300 each, 50 to 92 above 15,000 and 4 to 20 above 26,000, up to 56,436 pixels, and
  cities and towns on up to 43,696 [V-EXEC 2026-11-23, `vh3m2efqeq`, `x5aphoaqwu`, `jyfr3ww7yo`,
  `2prnfya2fq`]. They are born in the plan and in the growth alike: of the grown cells above 15,000
  pixels (VH3M's three continents: 22, 36, 0) the plan was already above it in half, and between
  7,500 and 15,000 in the rest, grown by 1.1 to 2.4 over it, never below 7,500, so a cap on the plan
  could not hold them. A last growth therefore gives every cell above the bound
  (`river_cells(limit=)`) a second seed and grows the cells again, at most eight times
  (`_divided_seeds`): the cell's two ends (the pixel farthest from its centre and the one farthest
  from that) are found, and the cell's own pixels nearest to a quarter and to three quarters of the
  way between them are the two seeds. Each grows at 707 ‰ of the cell's speed (`SPLIT_GAIN`, the
  square root of a half: each is planned half the area). At the cell's own speed the new seed, near
  the cell's far end, took the land of the small cells beside it: the neighbours of X5AP's cells
  differed by more than two octaves in 6.4 ‰ of the pairs and by more than three in 0.4, against
  5.0 and 0.0 without the bound. No border is cut across finished cells. The cells touching a polar
  map edge, which become impassable wastelands, stay as large as they grew. The export checks the
  finished locations (`verify_sizes`): a passable location above 20,000 pixels (`LAND_PX_CEILING`,
  the bound less a fifth, for the border rivers' pixels, merged slivers and the one reading it
  rests on) stops the export. By full export [V-EXEC 2026-11-23, final code; the three worlds with
  an export of the code before it beside them]:

  | World | Passable cells | Median px | Largest px | Above 15,000 / 20,000 | Pairs over 1 / 2 / 3 octaves, ‰ | Largest city or town px |
  |---|---|---|---|---|---|---|
  | VH3M before | 8,285 | 2,076 | 28,583 | 50 / 16 | 104.2 / 4.3 / 0.1 | 28,154 |
  | VH3M | 8,346 | 2,098 | 15,360 | 2 / 0 | 103.1 / 4.2 / 0.1 | 13,991 |
  | X5AP before | 8,107 | 2,365 | 44,375 | 92 / 41 | 114.4 / 5.0 / 0.0 | 43,696 |
  | X5AP | 8,252 | 2,426 | 15,294 | 4 / 0 | 108.6 / 4.6 / 0.0 | 15,294 |
  | PRNF before | 8,287 | 2,347 | 43,715 | 80 / 19 | 105.6 / 3.3 / 0.0 | 19,614 |
  | PRNF | 8,389 | 2,384 | 16,246 | 6 / 0 | 102.6 / 3.0 / 0.0 | 14,521 |

  The other four worlds (JYFR, a `wall`, an `archipelago` and a `continents` world) export with the
  largest passable location 15,761, 14,985, 13,285 and 15,163 pixels; none stopped the validator.
  The bound alone does not touch how many people stand in a cell: their cities and towns still lay
  at the 0.81 to 0.88 percentile of populated locations by area (vanilla America's 0.15, Africa's
  0.33) because the people went as the pixels. That is the next section.

### People follow the plan (1.3.0 / epoch 64, `SETTLED_PEOPLE`)

A location's people were `pixels × density of its climate`, so within a class (climate and
topography) population grew with the area of the cell: slope of log2 population on log2 area
+0.7 to +1.2 in six exported worlds, r +0.5 to +0.8 [V-EXEC 2026-11-23]. Vanilla 1.4.9 holds
alike or fewer people in the larger location [V-LOCAL, 1337 start, passable land with people]:

| Vanilla continent | Locations | Slope within class | r | sd of log2 pop within class | Cities/towns at area percentile |
|---|---|---|---|---|---|
| America | 4,434 | −0.39 | −0.21 | 1.97 | 0.15 |
| Africa | 2,432 | +0.18 | +0.10 | 1.71 | 0.33 |
| Oceania | 713 | −0.05 | −0.03 | 1.63 | (no city) |
| Asia / Europe | 7,934 / 5,259 | −0.25 / −0.25 | −0.13 / −0.15 | 1.83 / 1.21 | 0.40 / 0.34 |

(−0.55, the slope of all of vanilla pooled by class alone, is an artefact: the Old World's small
dense locations meet the Americas' large sparse ones. Within every continent the slope is mild.)

From epoch 64 the planner records, for every cell, the area it asked of it (`NewWorld.planned`:
the mean over its pixels of the squared spacing of their block, `watersheds.cell_plans`, 0 for
water; carried through the land cache, `turned_to_sea`, `ports.relabel` and
`continent_world.compose_regions`), and `eu5_natives.land_graph` counts the people of a location on

`planned = class median × (own plan / class median) ^ e`

instead of on its pixels (`settled_land`; a class of fewer than 30 cells takes the median of its
climate, then of all). The exponent `e` is per generated continent, after the vanilla one it stands
for: America −0.6, Africa −0.1, Oceania −0.2 (`SETTLEMENT_EXPONENT`; another continent takes
America's). The plan is 0.7 to 0.8 of the within-class variance of a finished cell's log area, the
growth of the cells the rest, so the people follow the plan and not the luck of the growth; the
societies' complexity gain and noise still run on top. The export stops without it
(`verify_settlement`: no `planned`, or a passable cell without a planned area). The total
population is the fixed target as before. The exponents were chosen offline on the captured inputs
of two worlds [INFERRED] and checked on six exported worlds [V-EXEC 2026-11-23, against exports of the code before]:

| World, continent | Slope before → after | r after | City/town area percentile before → after | People in cells above 10,000 px before → after | Median area of locations with 30+ people before → after |
|---|---|---|---|---|---|
| VH3M America | +1.18 → −0.28 | −0.22 | 0.88 → 0.58 | 10.7 % → 3.1 % | 6,026 → 4,471 |
| X5AP America | +1.20 → −0.28 | −0.22 | 0.91 → 0.56 | 16.7 % → 5.2 % | 6,490 → 4,424 |
| PRNF America | +1.24 → −0.24 | −0.22 | 0.92 → 0.62 | 14.5 % → 4.2 % | 5,847 → 2,924 |
| `continents` | +1.05 → −0.43 | −0.35 | 0.76 → 0.41 | 3.3 % → 0.4 % | 4,383 → 2,165 |
| `archipelago` | +0.98 → −0.43 | −0.31 | 0.73 → 0.49 | 1.6 % → 0.1 % | 3,052 → 912 |
| `wall` | +0.97 → −0.23 | −0.25 | 0.74 → 0.28 | 5.2 % → 0.6 % | 3,300 → 1,962 |
| VH3M Africa | +1.20 → +0.16 | +0.13 | 0.68 → 0.54 | 13.4 % → 5.3 % | 4,347 → 3,608 |
| X5AP Africa | +1.13 → +0.08 | +0.07 | 0.80 → 0.55 | 20.8 % → 8.3 % | 5,788 → 3,930 |
| PRNF Africa | +0.72 → −0.27 | −0.21 | 0.67 → 0.50 | 18.6 % → 8.5 % | 6,216 → 3,722 |
| VH3M Oceania | +1.09 → −0.01 | −0.01 | 0.30 → 0.31 | 0 % → 0 % | 4,171 → 1,526 |
| X5AP Oceania | +0.97 → −0.18 | −0.17 | 0.82 → 0.55 | 15.2 % → 3.7 % | 4,300 → 2,113 |
| PRNF Oceania | +0.89 → −0.24 | −0.20 | 0.48 → 0.29 | 0.1 % → 0 % | 2,508 → 1,273 |
| Vanilla America / Africa / Oceania | −0.39 / +0.18 / −0.05 | −0.21 / +0.10 / −0.03 | 0.15 / 0.33 / – | 0 / 0.5 / 0 % | 675 / 1,558 / 693 |

The slope now falls in the bands set before the exports (America −0.39 ± 0.15, Africa +0.18 ± 0.15,
Oceania −0.05 ± 0.2) in five of the six America worlds (`wall` −0.23 misses by 0.01), two of the
three Africa worlds (PRNF −0.27 does not; the world differed before, +0.72 against +1.13 and
+1.20) and all three Oceania worlds; the mean is −0.32, −0.01 and −0.14. The population, the
uninhabited share of Oceania (0.15 to 0.30, unchanged: another matter) and the number of cities
and towns stay as they were (74 → 72, 121 → 120, 104 → 109 in the three composed worlds; the
total population within 1 %).

What is not met, and is not meant to be: the people of a world are less spread within a class
(sd of log2 population 0.9 to 1.2 against 1.1 to 1.5 before; vanilla's 1.2 to 2.0), the cities
and towns of the Americas still lie above vanilla's percentile (0.28 to 0.62 against 0.15; the
rest is between classes, not within them [INFERRED]), up to 8.5 % of the people still live in cells
above 10,000 px (vanilla 0 to 0.5 %) and the largest city is as large as before (13,991 px in
VH3M; the safety margin is the bound above, not this). The African megalopolis stands in a cell of
1,559 to 6,766 px (vanilla's: 202 to 421). A world made before epoch 64 keeps what it has, as does
the existing VH3M world, with its 28,154 px "City of Sara".

## Coast shape, water bodies and drainage (1.1.0 / epoch 60)

The roadmap's hydrology and continental-variety directions are taken up together: coasts,
lakes, inland seas, narrow land connections and drainage are all constructed in the land
stage (`newworld._natural_land`) or the river stage, with no repair after generation. No new
setting is added; the sizes follow the existing feature size, and `new_world.max_lake_px`
(Largest lake) now defaults to 25,000 pixels with a control range up to 60,000. Its help text
in all eleven languages describes the drawn lake size. Since pending epoch 61, natural enclosed
basins can remain lakes above that size or become substantial inland seas; see
[the basin classification policy](sea-geography.md). Water connected to the open sea stays sea.

**Distance from kept shores (1.1.0 as Distance from the Old World; `new_world.centre_permille`, 0 by default).** The
land lies where the density field puts it, and on the wide expanded canvas that is often against
the Old World's shores. The control adds to the land density a lift that rises smoothly (a
smoothstep of the Euclidean distance from the edge of the domain, on blocks of four pixels, up to
the deepest interior or 2,400 pixels) by at most one noise unit, so the land moves toward the middle
of the canvas while the threshold, which counts pixels, keeps the land share. The mean distance of
the land from the canvas edge, on the installed canvas (seeds 4242 and 7, continents and small
continents): 1,540–1,920 px at 0, 1,840–2,100 at 250 ‰, 2,070–2,230 at 500 ‰, 2,260–2,360 at 750 ‰ and
2,340–2,390 at 1,000 ‰, with the share unchanged to within 0.3 percentage points
[V-EXEC 2026-10-31]. A doubled lift had saturated by 500 ‰. The Wall and drawn land ignore the control. The
default leaves every world as it was; world codes carry the value as a changed field.

**Water at the join with the game's map (1.1.0; no setting).** No land lies within
`newworld.EDGE_WATER_PERMILLE` (30 ‰ of the canvas's width, 302 px, about two and a half sea cells) of the
canvas's boundary with the game's own map: the Old World, the waters of the game kept whole and the
left and right edges of the crop. The band is added to the guard of the coast ramp, so the ramp, the
inland shift and the optional distance control above all start at its inner edge; the polar map edges
get none, and The Wall passes the real boundary rather than its own cleared course. The land share is
kept by raising the land share of the narrower interior (`_widen_boundary`). On the owner's world
`aszzsukifw` the land's least distance from the boundary rose from 150 to 476 px with 33.0 % and 33.1 %
land [V-EXEC 2026-11-01]; [sea geography](sea-geography.md) says why the water is wanted there.

**Vanilla calibration.** [V-LOCAL 2026-10-30, EU5 1.4.6 / 26300913, `Eu5Map` location sizes]
The installed map has 918 lake locations (median 90 pixels, 99th percentile 6,131, largest
22,692). Those of at least 80 pixels (the generator's `min_lake_px`) number 482: 11.2 per
million land pixels (land, wasteland and non-ownable together, 43.1 million), 0.78 % of that
land, with quartiles 127 / 214 / 503 and 1,096 at the 90th percentile; a Pareto tail with
exponent about 0.88 describes them. The 1.0.0 generator drew 0.9 per million (0.09 % of land),
none above 4,000 pixels, from accidental holes in the thresholded noise; larger enclosed water
was filled with land, so no sea could lie inland.

| Stage | Module | Construction |
|---|---|---|
| Bent coast field | `newworld._field`, `_warped_rows` | The land density is sampled at coordinates displaced by two smooth noises of 0.45 times the feature size and the same period, on a 2-pixel lattice interpolated bilinearly, so any strip height gives the same pixels. Plain thresholded noise gives rounded blobs; the bend gives capes, hooks and gulfs with narrow mouths. 0.8 drew thin marbled slivers, so it was refused. The land budget is unchanged (the threshold counts pixels). |
| Isthmuses | `isthmuses.py` | Landmasses of at least 0.8 % of the squared scale length that a narrow strait separates (`straits.narrow_gaps`, up to 0.2 of the scale, at least the 36-pixel `pinch` reach) are joined, each pair with a chance of 0.45, by a land corridor: the pixels whose distances to the two landmasses sum to little more than the distance between them, held within three half-widths of the crossing, widening towards both ends. Refused if it touches a third landmass, the protected edge or the coast margin, would leave a new piece of water closed off, or does not join the two. |
| Inland seas, gulfs and lagoons | `gulfs.py` | A basin with an outline as ragged as an ocean coast is cut into land that keeps a rim of at least 1 % of the scale length around it, and a strait is cut to the nearest ocean as the same distance-sum corridor (narrowest in the middle, flaring at both ends; half-width 0.3–1.1 % of the scale, never more than a quarter of the basin's short radius). A thin rim leaves a spit and a lagoon or gulf with one narrow entrance (the Gulf of Gdańsk behind the Hel spit, the Sea of Azov behind the Arabat spit); a thick one, an inland sea behind a Bosporus-like strait. Each sea is refused unless every basin pixel reaches the open sea after the cut, so none is cut off; corridor pixels the strait does not reach stay land. The scale length is the feature size bounded to 1,000–1,600 pixels, so island presets do not shrink the seas and a sea needs a landmass that can hold it. |
| Lakes | `lakes.py` | Sites are drawn per 256-pixel square by land area; each has an area from the vanilla tail (quarter-octave steps, 859 permille passing each), an elongation (up to 2.4, and for about an eighth, fingers of 3–6), one of sixteen orientations, a bend and a complexity. The area is exact; the shape is not an ellipse with a rough edge, which read as a crater in the first build (every lake a smooth oval). A lake is the part of a bent ellipse where a six-octave fractal noise, weighed against a bowl-shaped envelope, rises above the level that leaves exactly that area: lobes, bays, headlands, sinuous arms, satellite ponds and sometimes islands, more tangled where the noise outweighs the bowl, and narrow and sinuous for fingers. It is kept only if no pixel of it lies within 14 pixels of water, so it stays a lake and not a bay. Lakes are cut before islands are counted. |
| Rivers through lakes | `rivers.generate_rivers(lakes=...)`, `streams` | Lake cells are land in the priority flood with the lowest height, so the lake fills to its lowest rim and every lake has one outflow; rain accumulates through it. A stream going upstream ends at the first lake cell, which is where the outflow river begins (its source is on the shore); each river that enters the lake starts a stream of its own and ends in the water as any river reaching water. The inflows of a lake are kept even when the river leaving it is too short to be drawn. Lake cells do not count towards the river density target. The raster rules and the outlet check are unchanged. |
| Crossings over the seam | `eu5_seas.straddles_seam` | A strait that runs through the display seam has two points a map width apart in `adjacencies.csv`; the game's own 184 rows are all 1–9 pixels apart and none crosses an edge, so such a crossing is not written and not expected [V-LOCAL 2026-10-30]. A new pattern of straits exposed it on an island world. |

**Measured** [V-EXEC 2026-10-30; `land_stage` on the installed expanded canvas, 8192 × 10075,
eight seeds per preset: 42, 7, 1000, 1–5; mean per preset, before → after]:

| Preset | Lakes ≥ 80 px per million land px | Lake area share | Largest lake | Coast length per √area | Narrow gulfs (closing 12 / 24 px, share of land) | Necks (erosion 6 px) |
|---|---|---|---|---|---|---|
| continents | 0.9 → 11.5 | 0.09 % → 0.82 % | 3,263 → 17,373 | 14.0 → 20.3 | 0.010 / 0.029 → 0.020 / 0.046 | 1.5 → 3.3 |
| small continents | 2.7 → 11.6 | 0.18 % → 0.96 % | 3,440 → 17,963 | 21.1 → 26.4 | 0.021 / 0.053 → 0.032 / 0.072 | 2.5 → 2.6 |
| supercontinent | 0.3 → 12.0 | 0.03 % → 0.70 % | 2,087 → 17,388 | 8.9 → 14.3 | 0.003 / 0.010 → 0.010 / 0.019 | 1.3 → 1.1 |
| archipelago | 16.8 → 21.5 | 0.74 % → 1.8 % | 3,607 → 18,142 | 58.1 → 62.6 | 0.118 / 0.265 → 0.137 / 0.284 | 12 → 14 |
| islands | 25.7 → 27.4 | 1.08 % → 1.81 % | 3,678 → 17,617 | 80.5 → 86.7 | 0.204 / 0.454 → 0.226 / 0.493 | 18 → 27 |

Continent lakes now match the vanilla density, size quartiles (112 / 184 / 436 against 127 / 214 /
503; 1,270 at the 90th percentile against 1,096) and tail. Island presets already held many noise-hole lakes, so their
count barely moves while larger lakes appear. Inland seas number 0–4 on continents (mean about
2.4), 3–5 on small continents and 1–4 on a supercontinent; isthmuses 0–2 on continents, so some
seeds have them and others do not. Rivers: continents seed 1000 keeps 16 drawn river pixels per
1,000 land pixels (326,000 against 347,000 before, on 6 % less land) with 492 mouths against
365 (the outflows and inflows of lakes) and 231 lakes against 28. An earlier build dropped every
lake inflow whose outflow was too short and fell to 14; a regression test now covers a lake in a
valley. Full exports on EU5 1.4.6 / 26300913 pass every invariant for continents (seed 1000),
wall (9), archipelago (42), islands (7), small continents (42) and supercontinent (42): no split
cell, unreachable sea zone, unported land cell or river-rule violation.

**Physical map of the generator.** The viewers synthesize their relief from each location's
topography, not from the heightmap (`desktop/src/lib/relief.ts`, `gui/mapstyle.py`, the same
arithmetic). They treated a lake as a shore: height fell to zero over six field pixels all
round it, so each of the new lakes read as a crater with a lit rim and a dark wall (owner
report, 2026-10-30). A lake is now a level surface in the land (the mean height of the land
its location touches, flatland's if none), only the sea is a shore, and a lake in mountains
shades like the mountains around it: mean deviation from level 0.69–0.70 before against about
0.25 after, in the same synthetic test in both languages. The owner saw the generated world
in game and found the lake depth acceptable though not ideal; the game's own heightmap, where
a lake is a coast-height depression, is unchanged.

*Lit as a chart, not as a model* (2026-11-22, owner report: coasts almost black beside others so
burned that the biome vanished). The cause was the light, not the colours: the height was dragged
to nothing at every shore, so each coast was a cliff, and one lamp lit that cliff hard on one side
and not at all on the other. The relief is now built in one place for both windows
(`lenses.json`, `relief`; every number of the light is there):

* The height is smoothed over the land alone (a normalised blur, so a coastal pixel averages the
  land around it and not the sea), warped ridge noise rides on it, and a Sobel slope is lit from
  four azimuths at once (the north-west most), squeezed by `tanh` into −1…1. A slope is never
  wholly black or wholly white and level ground reads 0.
* `lit()` grades a colour by that shade within bounds: in shadow it loses at most 42 / 38 / 30 %
  per channel (the blue least, so shadows are cool), in light it moves a fifth of the way to a warm
  lamp colour and never past it. The hue of the biome stays readable at both ends.
* High ground turns to rock between two heights and to snow above the snow line of its climate
  (0.30 arctic to 0.95 arid, blurred across locations like the colours), so a hot range is not
  white and a polar one is.
* Water darkens from the shore as an exponential shelf (three e-folds of the coast depth), and its
  depth is an exact Euclidean distance (Felzenszwalb, stored in quarter field pixels), where the
  chamfer distance had drawn octagonal blocks.

Measured on the real atlas of one three-continent world, the shade at the coast (61 406 pixels)
has percentiles 1 / 5 / 50 / 95 / 99 of −0.97 / −0.87 / −0.04 / 0.54 / 0.63 and inland (163 101
pixels) −0.98 / −0.87 / −0.03 / 0.50 / 0.63 in the TypeScript port, with the Python one within a
hundredth [V-EXEC 2026-11-22]: the coast is lit as the inland is. The relief of a full-size
synthetic atlas (4 096 × 1 880, 600 locations) takes 1.2 s in the Tauri window where it took
0.86 s [V-EXEC 2026-11-22]. The game's own heightmap is not in the atlas; reading it would change
the atlas format and is not part of this.

[UNKNOWN] How the engine draws a generated lake of tens of thousands of pixels: vanilla lists
mesh transforms for its own lakes and the exporter drops those in the canvas, so generated lakes
(as in 1.0.0) are the water colour map under the sea plane; only small ones have been seen. The
play value of inland sea zones, and the appearance of the new coasts under the engine, are also
unobserved offline results; they do not reopen 1.0.0 acceptance. Not modelled yet: deltas and river
splits, valley carving driven by drainage (relief is still generated first), lakes that follow
depressions or climate (endorheic basins in arid land), and sea straits that the armies' crossing
rows treat specially.

## Mountains and hills (1.1.0 / epoch 60)

The owner reported on 2026-10-30 [V-GAME owner observation] that generated mountains and hills
were still unrealistic and monotonous beside vanilla's: from far away the ranges looked like
artifacts rather than chains, they were one height over wide areas, and close up nothing said why
the land was impassable, since it looked rather flat. Raising the ridges was suggested. After the
first rebuild the owner asked for the fine grain of the ground and for the cones round lakes to be
fixed too (both below), and then, on 2026-10-31, sent in-game screenshots of the result beside vanilla's
Alps and Caucasus [V-GAME owner observation, EU5 1.4.6, playset "RNW" = the generator hub and the generated
world, as `debug.log` and `playsets.json` show]: the range shapes seen from far away were much better, but
zoomed in the generated mountains, an impassable highland among them, had no visible relief at all,
where vanilla's stand out as peaks. I had said that their height was in order.

**Corrected diagnosis.** [V-EXEC 2026-10-31] The files of the loaded world held high ground (the
Wawamk Highlands, a mountain wasteland: median 19,846), but its local relief over 20-pixel windows had
a median of 5,457 where the Alps have 14,913, the Caucasus 11,110 and the Zagros 7,970, and its slope
(units per pixel; median / 90th percentile) was 403 / 759 against 1,310 / 2,792 in the Alps and 744 /
1,847 in the Caucasus. Over the generated locations with *mountains* topography the 16-pixel relief
had quartiles of 4,281 / 5,284 / 6,586 and slope 397 / 750; vanilla's primary heightmaps give 4,352 /
6,238 / 9,538 and 610 / 1,996. The first benchmark of this section, the share of land above each height
and the local relief of the highest ground, compared our pipeline with vanilla's **primary** heightmaps,
and the tallest samples were all it asked for. But what the game draws in vanilla is the primary
heightmap plus **3,706 additive mountain stamps** (`heightblendmode: add`; strength 0.23 at the
median, 0.35 at the 90th percentile and up to 0.8). They cover 75 % of the pixels of mountain
locations, with 1.06 stamps on average (at most 6), 11 % of hills and 38 % of mountain wastelands.
Reconstructing that sum from the installed instances (the rotation's direction does not matter to
these statistics), the 16-pixel relief of *mountains* has quartiles of 10,484 / 13,670 / 18,128 and a 90th
percentile of 22,333, slope 1,040 / 2,521 and a median height of 21,899 (the primary
heightmap: 6,238 and 16,700). Our mountains had the relief and slope of vanilla's **hills** (3,498 and
327 / 908), from stamps at a strength of 0.04–0.15, five or six to a pixel and joined by the maximum.
The rest of the causes of the first rebuild stand: a belt threshold that swells into broad blobs
wherever the noise is flat; one crest height along a chain; a presence noise that cut chains into
isolated segments; smooth hills; stamps at random in eight directions.

| Stage | Module | Construction |
|---|---|---|
| Chains | `relief._chain` | The axis of a chain is the zero line of a low-frequency noise (periods 900 and 600 pixels, the second family narrower and weaker), displaced by a finer noise. The distance to it is the noise divided by its smoothed slope, so a chain keeps its width where the noise is flat and forks where lines cross; a noise that crosses zero too gently (closed rings round a faint extreme) fades out. A crest zone of 130 pixels and a whole chain of 390 pixels (83 and 260 for the second family; half-widths, each wandering between half and three halves) rise through a smoothstep, the crest zone squared so it is sharper. |
| Massifs | `relief._strength` | A massif noise (period 520) sets each stretch's height between 0.38 and 1 of the peak, so ranges climb to peaks and fall to passes; a presence noise only thins them to 0.38, it no longer cuts chains apart. |
| Ridges | `relief._ridged` | Ridged multifractal of five octaves, 128 to 8 pixels: each octave's crest (one at the zero line, squared) lets a share through to the next, so fine ridges grow on high crests and the low ground between stays smooth, as erosion leaves it. A quarter of a chain's height holds without ridges; the peak is 38,000 units. |
| Hills | `relief` | Foothills (a 48-pixel blur of the chains' strength) and hill country carry a 72-pixel and a 20-pixel noise up to 5,500 units. Plateaus are unchanged. The inland rise is 2 units per pixel (it was 6) and follows the distance to the sea, with lakes counted as land (below). |
| Fine grain | `eu5_terrain.decal_heights`, `native/src/terrain.rs` | The terrain's detail noise, added to the relief at decal resolution, is a fractal from 64 down to 4 decal pixels whose octaves fall by a quarter each (it was three octaves halving), with an amplitude of 600 units plus 0.6 of the height above the coast, up to 7,500. The installed heightmaps' mean height difference grows with distance to a power of about 0.4–0.6, and this reproduces that exponent. Octaves, persistence and the amplitude's reach are parameters of the native kernel, equal to `tests/reference/terrain.py`. |
| Lakes | `relief.generate_relief(lakes=...)` | The inland rise and the broad tilt follow the distance to the sea, so a lake no longer stands in a cone. Mountains still fade out over 40 pixels at any shore, so no range ends in a cliff into a lake; hills and plateaus rise from a lake's shore over 16 pixels (40 from the sea), not out of a bowl of flat ground. |
| Stamps | `eu5_mountains.mountain_relief` | A candidate stamp every 48 pixels (jittered), where the smoothed relief reaches 9,000. Its chance rises with the square of the height above that, from 0.1 to 1 over 14,000 units: foothills seldom carry one, the high ranges nearly always, so the overlap there is about vanilla's. Its crest is turned onto the range's axis: the axis is the direction of least slope energy of the smoothed relief (an integer structure tensor over 8-pixel cells, 32 directions) and each source's own crest axis is found from the spread of its top pixels. Where there is no clear axis the turn is random. Size follows vanilla's percentiles (26 pixels across at the 10th, about 51 at the median, 102 at the 90th, stretched 0.7–1.5 along), strength is 0.2 + 0.4 u² of the source for a draw u (a median of 0.3, rising 0.85–1.15 with the height there). **Heights add**, as the engine's blend does, they show above 9,000 units (in full at 14,000) and nothing rises past 62,000 (the layer holds 65,535). |
| Stamp materials | `eu5_terrain._lay_stamp_slots` | Each installed stamp also has a material layer (slots 10, 11, 12 in the pattern of its valleys; 255 where it lays none) that vanilla blends with the lower slot winning (`materialblendmode: min` in its decal parameters). Generated land now carries it: coasts, rivers and borders (slots 0–9) stay, the variations take the stamp's slot on the mountains, and a biome whose list lacks the slot takes the slot its list holds (one with no variation at all keeps its own). Where stamps overlap the highest one decides, not the lowest slot: vanilla overlaps far less, and the minimum turned every dense massif into slot 10. |

**Measured** [V-EXEC 2026-10-31; installed expanded canvas; ground classed by its 48-pixel mean height, so no
location rule is involved; vanilla is the primary heightmaps with all stamps summed, outside the Tibetan
block]. 16-pixel relief at the 25th / 50th / 75th / 90th percentile, slope (units per pixel) at the 50th / 90th,
and the class's share of land, vanilla → a world with 24 % land:

| Class | Share of land | 16-pixel relief | Slope |
|---|---|---|---|
| 9,000–12,000 | 22.1 → 28.5 % | 1,023 / 1,778 / 2,994 / 4,559 → 1,962 / 2,513 / 3,294 / 4,415 | 144 / 374 → 198 / 305 |
| 12,000–16,000 | 18.4 → 23.3 % | 1,538 / 2,684 / 5,148 / 9,504 → 3,188 / 4,122 / 5,739 / 9,445 | 204 / 706 → 315 / 612 |
| 16,000–22,000 | 12.1 → 13.0 % | 2,456 / 6,244 / 11,844 / 16,791 → 4,647 / 6,486 / 10,795 / 16,300 | 449 / 1,232 → 446 / 1,062 |
| 22,000–30,000 | 5.4 → 5.3 % | 8,644 / 13,080 / 17,814 / 22,409 → 7,393 / 10,858 / 16,490 / 22,904 | 946 / 1,677 → 710 / 1,522 |
| 30,000 and over | 2.0 → 2.2 % | 13,922 / 17,788 / 22,408 / 27,386 → 12,247 / 16,506 / 22,256 / 27,996 | 1,324 / 2,052 → 1,086 / 1,887 |

Share of land above 14,000 / 22,000 / 30,000 / 40,000: vanilla with its stamps 22.9 / 6.5 / about 2.3 / 0.7 %; the
world 23.6 / 6.6 / 2.3 / 0.6 %. The same classes of three more worlds (11 %, 19 % and 34 % land) have
relief and slope within the same 20 % of vanilla's from 16,000 up; the share above 14,000 is 9.4, 21.0 and
28.6 %. The ground below 16,000 is rougher than vanilla's at its lower quartile (flatter stretches are missing
from the hills and foothills) and the classes of 9,000–16,000 hold more land than vanilla's. By location topography on the same
world, as the export would assign it (ranks of each cell's mean height and spread; a proxy for the
export's own rule): hills 16-pixel relief 2,378 / 3,211 / 4,299 / 6,047 against vanilla's 2,659 / 3,626 / 5,483 /
8,299; mountain wasteland 6,386 / 10,281 / 16,346 / 23,189; *mountains*, whose cells are the next ranks
down and so lower on the height scale than vanilla's, 4,137 / 5,485 / 8,314 / 14,261 against 10,484 / 13,670 /
18,128 / 22,333; flatland and plateau are about 1.5 and 1.9 times vanilla's median (1,382 against 861 and 3,384
against 1,759).

For the record, the first rebuild measured against the primary heightmaps alone: share of land above 14,000
5.7 % (1.0.0) → 17.3 %, above 22,000 2.6 → 3.3 % (vanilla's primary: 19.2 and 2.8 %), and the median local relief
of crest zones from 59 % to 98 % of vanilla's primary, which is what the owner's screenshots refuted.

Mean absolute height difference at decal resolution, by distance in decal pixels (1/4/16/64), for
ground whose 96-pixel mean is in the class; vanilla's primary heightmaps / before the grain / now (the grain, 2026-10-30):

| Class | Vanilla | Before the grain | Now |
|---|---|---|---|
| 6,000–8,000 | 47 / 118 / 262 / 500 | 9 / 32 / 107 / 332 | 32 / 108 / 248 / 586 |
| 8,000–11,000 | 62 / 188 / 477 / 1,009 | 21 / 81 / 272 / 828 | 62 / 215 / 521 / 1,222 |
| 11,000–15,000 | 119 / 392 / 996 / 2,066 | 52 / 191 / 612 / 1,621 | 112 / 387 / 947 / 2,038 |

**Lakes.** [V-EXEC] The relief took the distance to the sea from a mask in which a lake was water, so
every lake raised the ground round it in a pyramid up to 320 pixels across (its facets were the
medial axis of that distance). A world has about 230 lakes, so the pyramids overlapped and lowered the
interior ground nearly everywhere: counting lakes as land lifts the median relief of the land in the
first 2,304 rows of one world from 9,645 to 10,346. The inland rise was reduced (to 2 units per pixel, with the
stronger chains) to bring the shares of the classes back to vanilla's.

Relief on the full canvas takes 17–20 s (it took 6 s before the mountains); the stamps' planning 0.3 s;
the terrain and stamps of the canvas 10–20 s. A full export of continents seed 1001 takes about 195 s on
the development machine (a local timing, not a benchmark). Strips of any height give the same relief with and
without lakes (`tests/reference/relief.py`), bands and columns the same stamps and slots, and the
band-to-band, seam and roll tests hold with the stamps' materials. Full exports of six presets
(continents 1001, wall 9, archipelago 42, supercontinent 42, islands 7, small continents 42) pass
every cell, port, route, river and contact invariant; the rivers, the topography of each cell and the
biomes follow the new relief, so every world differs from the one before.

[UNKNOWN] How the engine renders the result, and the scale of its stamp blend: the heights, slots and the
reconstruction of vanilla's sum are computed from the files and the instances' parameters, on the reading that
an `add` stamp raises the terrain by its source times its strength; the engine's actual factor is not
observed, and an error in it moves vanilla's reconstructed relief and ours the same way only if the
reading is right. The maps in both windows draw their relief from location topography, not from these heights.
The stamps' material blending is likewise inferred from the decal parameters. The bank of a lake in the
terrain stage is the coastal cap, a rise of 300 units per decal pixel from the lake's own height, so a lake
in a range has a steep bank.

## Omerika

**Design (1.2.0 development, pending epoch 61).** [V-EXEC, EU5 1.4.7 / build 26377361] `rnw/omerika.py`
adds one term to the continents' density field: the installed game's Americas (land and lakes of the
`america` continent, `Canvas.template`, read when the canvas is selected and kept in the land cache,
never shipped). The template is worked on a 4-pixel grid: its coverage is read through a smooth
seed-drawn displacement (amplitude 300 px at a loose likeness, 80 px at the closest, period 1,500 px;
the Jacobian stays above 0.35) and turned into a signed distance from the coast. Two profiles of it
are mixed by the likeness squared: a *soft* one, cut off at 600 px and squared, flat at the coast and
steep far from it, and a *sharp* one, linear and cut off at 140 px. The sum is added to the fractal
noise with weight `template_permille` of three noise ranges (500 by default). The soft profile lets
the noise draw the coast; the sharp one holds the outline at a close likeness. The land share is the
Americas' own (215‰ of the interior against 205‰ of the canvas). Climate, relief, rivers and everything
after the land are the ordinary layers.

**Thin parts.** A signed distance is a few dozen pixels deep in a neck or a cape, and the noise would
take them (the first version lost Central America, Yucatan and Baja at likeness 1000 and left the
corridor as a ribbon over the sea, owner's screenshot 2026-11-09). Where no land within 110 px of the
sea lies near, the centre line of the land (the ridge of its depth, at least 16 px from the sea) is
raised by three noise ranges and widened by three cells each side, in proportion to a likeness that
rises from 250 to 650.

**The join.** The two greatest cores of the template (land at least 300 px from the sea) are joined
by the cheapest 8-connected route on a 16-px grid that prefers depth (cost 1 + (120 px / depth)²),
widened and raised by four noise ranges, so it is land by construction. It is made only from a
likeness of 300 (below it the land is a loose echo and keeps no promise to join: a corridor between
places that the land no longer puts there is a ribbon). `check_joined` runs after the land stage and
after the pinch and classification and fails explicitly unless the places of the *neck* (the stretch of
the route less than 300 px deep; the route's stretch inside a continent may lie in an inland sea) are
land (90%) and one landmass; there is no repair.

**Measured** (real canvas of the installed game, 8,192 × 10,078 px; `land_stage` takes 8.5-9.5 s, the
template 0.6 s): all seeds joined at likeness 300 (8), 500 (14) and 1000 (12); overlap with the
template (IoU) 0.48-0.55 at 300, 0.65-0.74 at 500 and 0.81-0.84 at 1000 (a random continent of the same
share overlaps about 0.1; land 201-207‰). At every likeness from 300 the share of land within 150 px of
a place of the route is at least 0.4: no ribbon. The non-expanded canvas still works. A full export of
seed 42 at 500 and at 1000 passes every export validator.

## The Wall

The 1.1.0 / epoch 60 cycle adds `--preset wall` (The Wall; Russian: Стена).
The owner requested a straight thin continent spanning every row on 2026-10-30,
using their EU4 screenshots as visual references. Online player descriptions call
this EU4 fantasy scenario [The Wall](https://www.reddit.com/r/eu4/comments/1ivh48m/),
while [The Line](https://www.reddit.com/r/eu4/comments/x7z8ui/) also occurs. These are
community names, not verified official localization identifiers [SOURCE, accessed
2026-10-30]. No EU4 assets or tile data are included.

`wall.py` plans the barrier's route in the installed game's expanded canvas, keeping all
protected pixels intact, and places the continental envelope along it. The position control
spans the longest band of columns in which at least 90% of the rows are open (columns 2,173–7,350
of 10,075 on build 26300913 [V-EXEC 2026-11-01]), west to east. The route is a straight line at that position wherever the
envelope with its coast margin fits. Where an island, a group of islands or their guard water
is in the way it detours by the shortest smooth way: the backward pass of `wall._plan` finds the
cells from which the south edge can still be reached, so the detour starts early and the route
returns to its position beyond the obstacle; it moves at most half a pixel sideways per row
(the grid is 16 × 32 pixels), and a moving average over 512 rows rounds it off while the planner
keeps 80 pixels of extra water for that. Islands closer together than the envelope count as one
obstacle, so the wall passes a group on one side and never threads between. The exact route is
checked against the protected pixels row by row, and a canvas with no route is rejected. The
secondary land keeps the same clear gap on both sides of the route. [V-EXEC, 2026-10-31] On the
installed canvas the planning takes 0.15 s and the full export of the owner's world at position
0 (width 140‰, gaps off) passes every check (no split cell, unreachable sea or lost Old World
contact); the wall follows the west of the canvas and goes around the Polynesian protrusion and the isolated islet.
One seeded, multi-octave land-density field defines the coast within that envelope.
Land amount shifts its sea level, feature size and octaves set its scale, and coastal
irregularity sets its strength. The same field can produce continuous land, coastal
islands, an island chain or an intermediate shape. Density saddles may form narrow
navigable straits. No scenario is selected and no count or probability of passages
is prescribed. **Allow gaps in the wall** is enabled by default; disabling it imposes
a continuous land core on the same field. The polar endpoints remain land.

The core (`wall.core`) is not a straight strip: its centre drifts by up to 0.3 of the
envelope's half-width and its half-width swells between 0.3 and 0.5 of it, both along
the whole length, and its edge takes the ragged shore of the coastal noise (up to an
eighth of the half-width). Coastal noise fades over the outer quarter of the envelope, so
no coast is cut off along the envelope's straight edge, and the wall keeps the land it is
sized for (a base of 250‰; a larger land share adds to it).
[V-EXEC, 2026-10-31] Owner report: a world with land share 187, coastal irregularity 904,
maximum width and gaps off (seed 12471306029767500627) was a thin, ruler-straight strip
through much of its length beside large continents. The straight strip was the old forced
core (a fixed quarter-width column in every row) exposed wherever the density field
left the wall's own land empty; no location budget was involved (6,643 of 32,000 locations).
The same land stage at one eighth scale now gives a bent core of varying width; the
connectivity checks and a per-row centreline check at cell construction remain.

The land share is one budget for the whole world. `newworld._wall_land` builds the barrier
first and counts its pixels; the continents beside it get `land_permille` of the canvas's
interior less those pixels (`_natural_land(budget_px=…)`), never less than
`WALL_SIDE_MIN_PERMILLE` (1%) of the water beside the wall. So a wider wall leaves fewer
continents, and a wall that needs the whole share takes nearly all the land. A wall wider than
the share allows keeps its land and the world has more land than the share asked for;
`controls.estimated_locations` counts that (`wall_share`). Before this the continents took the
share of the canvas without the wall's band and the wall came on top, so the widest wall
(14%) still sat beside huge continents. [V-EXEC 2026-11-01, real canvas of build 26300913,
seed 1000, land share 212‰, 61.65 million interior pixels] The wall's land is 0.65–0.77 of the
width in permille of the canvas's land area (54 settings: irregularity 0–1000, gaps allowed or
not; the worst case of each land amount), rising to 1.15 at a land share of 600‰. Land stage:
width 140‰ gives a wall of 100‰ beside 114‰ of continents (total 214‰); width 300‰ a wall of 207‰
and 6.5‰ beside it; width 440‰ a wall of 312‰ (more than the share) and 10.4‰ beside it. The
route search finds a way for widths up to 464‰ at every position (the longest open band is
51% of the canvas), so the control stops at 440‰. The full export at 440‰ (seed 1000) has
29,257 locations (the window estimates 30,800 and refuses above 31,200) and every sea invariant
holds (no split cell, unreachable sea, lost Old World contact or land cell without port access).

Secondary land outside an ocean gap on either side uses a continuous density field
with a broad continental component (four times the feature scale, two-thirds of
the density) and the ordinary local coast component (one-third). One sea level
sets its land budget across both sides. This lets a seed leave whole broad regions
as ocean rather than distributing local land through every large canvas pocket.
The protected-domain boundaries still constrain where land can occur. There are
no continent positions, counts or scenario templates in this field.
The regular relief, climate, rivers, locations, societies and content pipeline runs
on the result; a longitudinal mountain spine adds the scenario's defining relief.
Locations touching the polar endpoints become wasteland. Construction rejects a
canvas too narrow for the requested envelope or a drawn-mask combination. With gaps
disabled, it verifies that the final cell raster retains its continuous land column.

Both windows expose the gap checkbox plus maximum width (4–44% of canvas width, 14% by default),
west-to-east position across the canvas (the wall goes around protected islands), coastal irregularity and
ridge height under Advanced → The Wall. Land share, feature scale and noise settings
shape both the Wall and the side land. The preset requires the expanded canvas. Its
world codes preserve every control.

At the owner's request, ordinary and image-based generation also permit land to
reach the north and south map edges. Ordinary continents now have one narrow
approach to each polar edge, selected from the strongest inland part of the coast
field; the rest of each edge has the same ocean guard as a canvas boundary.
Land locations near either edge use a coarser seed grid, and every location that
touches an edge is impassable. Image-based land keeps its authored coast, but its
edge locations use the same larger grid and impassability rule. The Wall keeps its
continuous polar endpoints. Protected pixels and longitudinal margins remain
guarded. Polar water connects to ocean
only through actual ocean outlets; isolated polar basins follow the same lake
classification as other enclosed water. Ordinary worlds do not guarantee polar land.

[V-EXEC, 2026-10-31, C454] The installed EU5 1.4.6 / build 26300913 export of
the epoch-60 reference passed the world validators (871 nonmetadata files,
SHA-256 `03d0877d…194aa`). An independent continents candidate with seed 20261031
has one generated land location on a polar edge: 249 edge pixels out of 150,849
generated-land coast contacts (0.17 %). That location has 60,190 pixels and is
listed as an impassable mountain. For scale, the installed vanilla map's six
edge-touching land locations have median area 350,799 pixels; its polar and
middle-latitude land locations have medians 2,502 and 709 pixels respectively.
These are file measurements, not a new in-game visual observation. The local
comparison is in `local_data/polar-edge-20261031/edge-metrics.json`.

The full Wall export also exposed a route-scale defect: folding closed ocean zones
changed the median cell size and could invalidate an already constructed narrow
route opening. Water planning now retains the physical scale used to build routes;
validators still reject closed or incomplete routes.

[V-EXEC, 2026-10-30] On EU5 1.4.6 / build 26300913, the default Wall seed 9
exports 864 nonmetadata files (`0cd08894…79e8c7f`). The full export reports zero
split generated cells, unreachable sea zones, land cells without port access or
lost Old World contacts. The density field naturally leaves a narrow cross-wall
water opening in this seed. Synthetic checks cover continuous-core enforcement,
polar endpoints, seed variation, strip equality, increased land density, emergent
gaps and isolated polar basins. Both windows expose the translated controls;
all eleven installed-game language catalogues are current. Full checks pass
(2,244 Python tests, 15 optional skips; 23 native Rust tests), as do desktop checks
(14 interface tests, five Rust shell tests), native/Windows package self-tests and
the installed-game suite (14 tests, one opt-in skip), including independent reference
reproduction. The epoch-60 reference now has 867 files / `94fcf2d4…77a4bcc`;
the frozen epoch-59 reference is untouched. See [installation record](../experiments/INSTALLED.md)
for the new world and backed-up hub. Evidence stays under ignored `local_data/the-wall/`.
These are offline results; no EU5 launch or new engine observation is claimed.

### Secondary-continent placement follow-up

[V-LOCAL/V-EXEC, 2026-10-30] The owner reported repeated compositions in three
Wall worlds. Recovery records show that UED2 and OJB5 share seed
12140331280324730264, while 7FQK uses 15379157863967449931. Six full-resolution
land-stage runs confirmed changing outlines, but local-scale noise repeatedly
populated the canvas's broad northern and southern pockets. The additional
continental component above changes that broader occupancy too. A synthetic
regression requires each of two large side regions to be entirely ocean on some
seeds and substantially land on others; the former field fails it. Strip parity,
protected pixels and the Wall's existing continuity checks remain covered.
Evidence and before/after six-seed sheets stay in ignored `local_data/wall-variety/`.

The full default-settings seed-1000 export has 865 nonmetadata files
(`e0bd5068…f1ca9ec7`) and zero split generated cells, unreachable sea zones,
unported land cells or lost Old World contacts. Full checks pass (2,246 Python
tests, 15 optional skips; 23 native Rust tests). Native and Windows package
self-tests pass, and four synthetic seeds produce identical coast digests and
regional land counts in Linux and the packaged Windows generator under Wine.
The installed-game suite passes 14 tests (one opt-in skip), including independent
reproduction of the unchanged 867-file ordinary reference (`94fcf2d4…77a4bcc`).
The corrected geometry invalidates the development land cache; the release
target remains 1.1.0 / epoch 60. Existing worlds are preserved.
