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

- **V1b rivers:** accepted in game (C64). Lakes ended rivers (no outflows) until the pending 1.1.0 (see
  [below](#coast-shape-water-bodies-and-drainage-pending-110--epoch-60)); splits and deltas are not generated.
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

## Coast shape, water bodies and drainage (pending 1.1.0 / epoch 60)

The roadmap's hydrology and continental-variety directions are taken up together: coasts,
lakes, inland seas, narrow land connections and drainage are all constructed in the land
stage (`newworld._natural_land`) or the river stage, with no repair after generation. No new
setting is added; the sizes follow the existing feature size, and `new_world.max_lake_px`
(Largest lake) now defaults to 25,000 pixels with a control range up to 60,000. Its help text
in all eleven languages now says what the code does: lakes are drawn up to about that size and
larger *enclosed* water fills with land (water that reaches the open sea, with or without a
strait, stays sea).

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
| Lakes | `lakes.py` | Sites are drawn per 256-pixel square by land area; each has an area from the vanilla tail (quarter-octave steps, 859 permille passing each), an elongation up to 2.4 and one of sixteen orientations, and an outline of noisy ellipse. A site is kept only if its distance to the shore leaves the lake a rim of land (1.45 times its long radius plus 14 pixels), so it stays a lake and not a bay. Lakes are cut before islands are counted. |
| Rivers through lakes | `rivers.generate_rivers(lakes=...)`, `streams` | Lake cells are land in the priority flood with the lowest height, so the lake fills to its lowest rim and every lake has one outflow; rain accumulates through it. A stream going upstream ends at the first lake cell, which is where the outflow river begins (its source is on the shore); each river that enters the lake starts a stream of its own and ends in the water as any river reaching water. The inflows of a lake are kept even when the river leaving it is too short to be drawn. Lake cells do not count towards the river density target. The raster rules and the outlet check are unchanged. |
| Crossings over the seam | `eu5_seas.straddles_seam` | A strait that runs through the display seam has two points a map width apart in `adjacencies.csv`; the game's own 184 rows are all 1–9 pixels apart and none crosses an edge, so such a crossing is not written and not expected [V-LOCAL 2026-10-30]. A new pattern of straits exposed it on an island world. |

**Measured** [V-EXEC 2026-10-30; `land_stage` on the installed expanded canvas, 8192 × 10075,
eight seeds per preset: 42, 7, 1000, 1–5; mean per preset, before → after]:

| Preset | Lakes ≥ 80 px per million land px | Lake area share | Largest lake | Coast length per √area | Narrow gulfs (closing 12 / 24 px, share of land) | Necks (erosion 6 px) |
|---|---|---|---|---|---|---|
| continents | 0.9 → 11.3 | 0.09 % → 0.93 % | 3,263 → 19,533 | 14.0 → 19.7 | 0.010 / 0.029 → 0.021 / 0.048 | 1.5 → 3.1 |
| small continents | 2.7 → 11.3 | 0.18 % → 1.01 % | 3,440 → 18,842 | 21.1 → 25.9 | 0.021 / 0.053 → 0.032 / 0.073 | 2.5 → 2.6 |
| supercontinent | 0.3 → 11.9 | 0.03 % → 0.82 % | 2,087 → 19,331 | 8.9 → 13.5 | 0.003 / 0.010 → 0.011 / 0.021 | 1.3 → 1.1 |
| archipelago | 16.8 → 21.2 | 0.74 % → 1.8 % | 3,607 → 18,142 | 58.1 → 62.4 | 0.118 / 0.265 → 0.137 / 0.284 | 12 → 14 |
| islands | 25.7 → 27.3 | 1.08 % → 1.81 % | 3,678 → 17,617 | 80.5 → 86.6 | 0.204 / 0.454 → 0.226 / 0.493 | 18 → 26 |

Continent lakes now match the vanilla density, size quartiles (117 / 185 / 383 against 127 / 214 /
503 in a rectangular test) and tail. Island presets already held many noise-hole lakes, so their
count barely moves while larger lakes appear. Inland seas number 0–4 on continents (mean about
2.4), 3–5 on small continents and 1–4 on a supercontinent; isthmuses 0–2 on continents, so some
seeds have them and others do not. Rivers: continents seed 1000 keeps 16 drawn river pixels per
1,000 land pixels (326,000 against 347,000 before, on 6 % less land) with 492 mouths against
365 (the outflows and inflows of lakes) and 231 lakes against 28. An earlier build dropped every
lake inflow whose outflow was too short and fell to 14; a regression test now covers a lake in a
valley. Full exports on EU5 1.4.6 / 26300913 pass every invariant for continents (seed 1000),
wall (9), archipelago (42), islands (7), small continents (42) and supercontinent (42): no split
cell, unreachable sea zone, unported land cell or river-rule violation.

[UNKNOWN] How the engine draws a generated lake of tens of thousands of pixels: vanilla lists
mesh transforms for its own lakes and the exporter drops those in the canvas, so generated lakes
(as in 1.0.0) are the water colour map under the sea plane; only small ones have been seen. The
play value of inland sea zones, and the appearance of the new coasts under the engine, are also
unobserved offline results; they do not reopen 1.0.0 acceptance. Not modelled yet: deltas and river
splits, valley carving driven by drainage (relief is still generated first), lakes that follow
depressions or climate (endorheic basins in arid land), and sea straits that the armies' crossing
rows treat specially.

## The Wall

The pending 1.1.0 / epoch 60 cycle adds `--preset wall` (The Wall; Russian: Стена).
The owner requested a straight thin continent spanning every row on 2026-10-30,
using their EU4 screenshots as visual references. Online player descriptions call
this EU4 fantasy scenario [The Wall](https://www.reddit.com/r/eu4/comments/1ivh48m/),
while [The Line](https://www.reddit.com/r/eu4/comments/x7z8ui/) also occurs. These are
community names, not verified official localization identifiers [SOURCE, accessed
2026-10-30]. No EU4 assets or tile data are included.

`wall.py` finds a full-height corridor in the installed game's expanded canvas,
keeping all protected pixels intact, and places a straight continental envelope there.
One seeded, multi-octave land-density field defines the coast within that envelope.
Land amount shifts its sea level, feature size and octaves set its scale, and coastal
irregularity sets its strength. The same field can produce continuous land, coastal
islands, an island chain or an intermediate shape. Density saddles may form narrow
navigable straits. No scenario is selected and no count or probability of passages
is prescribed. **Allow gaps in the wall** is enabled by default; disabling it imposes
a continuous straight land core on the same field. The polar endpoints remain land.

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

Both windows expose the gap checkbox plus maximum width (4–14% of canvas width),
west-to-east position within the available polar corridor, coastal irregularity and
ridge height under Advanced → The Wall. Land share, feature scale and noise settings
shape both the Wall and the side land. The preset requires the expanded canvas. Its
world codes preserve every control.

At the owner's request, ordinary and image-based generation also permit land to
reach the north and south map edges. Those edges no longer impose an ocean guard;
protected pixels and longitudinal margins still do. Polar water connects to ocean
only through actual ocean outlets; isolated polar basins follow the same lake
classification as other enclosed water. Ordinary worlds do not guarantee polar land.

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
reproduction. The pending epoch-60 reference now has 867 files / `94fcf2d4…77a4bcc`;
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
target remains 1.1.0 / pending epoch 60. Existing worlds are preserved.
