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
| 0. Land and sea | `newworld.py` | Fractal noise above a threshold that keeps the land budget, with one seed-drawn lattice origin for the whole crop so high-variance nodes do not favour fixed map positions (0.12.1, C286). Near a guard (canvas edge, axes opening enclosed seas) elevation falls over a ramp of four coast margins whose start moves inland by 0–2 ramps of warped noise; canvas slivers thinner than two ramps stay sea. A sea cut off around a protected islet gets its shortest path to open water added to the guard, and the coasts are redrawn (C64). |
| 1. Relief | `relief.py` | One continuous height field in decal units. Mountain chains follow noise zero lines (belts) whose width and edges vary, cut into segments by a presence noise, with ridged crests; plus foothills, hill country, plateaus, a broad tilt and an inland rise. All noise uses rotated lattices and domain warping, so nothing aligns with the raster. Ramps use a Euclidean distance to the sea. The highest cells become wastelands. |
| 2. Climate | `climate.py`, `eu5_biomes.py` | Absolute latitude comes from city-locator anchors (C49). Rainfall comes from zonal winds: easterlies below 30°, westerlies from 30° to 60°, polar easterlies above, blended across the band edges. The sea recharges moisture (an ocean fully, a strait little). Land loses a fixed share per pixel plus an orographic share on smoothed terrain, which gives rain shadow behind ranges. The same model runs on the vanilla map and on the generated map. |
| 3. Classification | `eu5_biomes.py` | Integer k-nearest-neighbour vote (k = 32) over about 18,000 Old World land locations, on latitude, rainfall, mean height and distance to the sea. It predicts climate first, then vegetation within the chosen climate. Farmland is learned as grassland, because the New World starts empty. Sea and lake climates come from vanilla sea zones by latitude and distance to land. |
| 4. Coherence | `eu5_biomes.py` | Class scores are smoothed over the location adjacency graph: 3 rounds for climate, 1 for vegetation. Topography comes from relief ranks in vanilla proportions (mountains, plateaus, hills, wetlands, flatland), using height, height spread, rainfall and distance to the coast. Desert cells never become wetlands, because no biome covers that combination (C54). |
| 5. Material slots | `eu5_slots.py` | The vanilla rules above, applied to the generated labels and templates. Band edges, variation families and levels come from uniformised integer noise in absolute decal coordinates, so adjacent decals agree. Each label's biome is resolved through `biomes.txt` (most specific rule); a slot its material list lacks becomes the same variation level of the first family, else the highest listed level, else slot 0. |
| 6. Gameplay consistency | `eu5_nw_export.py` | Each location template gets the model's climate, vegetation and topography. Raw materials are drawn from vanilla frequencies for the same climate, vegetation, topography and coastal flag. |
| 7. Vegetation instances | `eu5_objects.py` | Vanilla instances inside the canvas are dropped. New instances are sampled per material pixel at the Old World density for the pixel's (vegetation, climate, topography, slot) class. Rotation and scale are copied from vanilla records of the same file. The engine caps the mesh map objects of a game at 2^24 (16,777,216) and drops those loaded last, so the new instances may not outnumber the removed ones (all densities scale down together by a recorded factor; 1% of the budget stays unused, `ObjectBudgetError` otherwise). Vanilla holds 15.9 million, the 0.9.8 world 19.5 million (C95). |
| 7b. Rivers (V1b) | `rivers.py`, `eu5_nw_export.py` | On a 4-pixel grid, a priority flood from all water gives every land cell a downstream neighbour, so depressions are crossed; routing adds fractal valley noise so flow converges. The square root of rainfall accumulates downstream; the catchment threshold gives 16 river pixels per 1000 land pixels (vanilla 15.7). Streams split at confluences (larger branch continues); rivers to the sea need 12 cells. Each stream is drawn from its head down a smoothed, slightly meandering line until it reaches water (up to 3 px into it; the head becomes the source) or meets a river drawn before (a join pixel beside one river pixel). Widths 4/5/11/15 follow catchment in vanilla shares; valleys of 350–1,150 units are carved within 6 px; slot 6 runs along rivers. The export refuses any violation of the vanilla raster rules (C59). |
| 8. Location shapes | `newworld.py` | Cell borders are bent by a smooth displacement field, then cut-off pieces are re-attached, so borders and the bands along them are organic rather than polygonal. A cell that would vanish or split keeps its original shape; before generator 0.9.1 such a cell undid the bending everywhere (C71). The map wrap does not constrain land: one continuous crop is generated before it is placed across the two map edges (0.12.2, C289–C290). Administrative cells that cross the display seam are split without changing the land mask. A strait is cut wherever generated land would enclose the sea around a protected Old World islet (C61). City points maximise `min(2 × distance to the cell border, distance to water)`, so coastal cities stand inland. |

## Climate/vegetation consistency follow-up (2026-10-29)

[V-EXEC C443] RNW 1.0.0's classifier initially conditions vegetation votes on the
selected climate, but its empty-vote fallback and subsequent neighbour smoothing
can discard that constraint. A synthetic 13-cell call to `assign_biomes` gives a
zero-rainfall-index centre `arid` climate and `forest` vegetation, although the
calibration fixture contains only arid/desert and tropical/forest pairs. Disabling
only vegetation smoothing changes that centre to desert. This establishes a
classifier consistency defect; its prevalence in generated worlds is unmeasured,
and it does not establish a general ban on forests in dry or continental climates.
[Issue #4](https://github.com/Sir-Starch/eu5-random-new-world/issues/4) contains the
game-independent reproduction and tracks a construction-time correction.

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

- **V1b rivers:** accepted in game (C64). Lakes end rivers (no outflows yet); splits and deltas are not generated.
- **V1b.1 coastline outline (C64–C65):** the owner saw the same north-west on a new seed. The edge ramp had grown with `feature_px` to 533 px and left only the canvas core for the land budget, so every seed filled the same outline (land overlap between seeds IoU 0.53–0.67). Now 0.31–0.45; seam coasts and straits use the same ragged coast model. Accepted in game (C66).
- Mountain mesh decals on generated ranges (vanilla covers about 57% of mountain interiors with them).
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
