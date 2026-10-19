# Terrain and biome synthesis (required, planned)

**Status:** planned, not implemented. The current material layer is an interim patch transfer (C46) and must be replaced.

## Problem

The owner reviewed the generated New World in EU5 1.4.1 on 2026-10-19 [V-GAME owner observation]. Coasts and water were fixed, but up close the land looks pixelated: forests and other biomes show many small squares, borders are rough, biomes do not fill coherent areas, and transitions are not smooth. Generation must use a deliberate algorithm, not noise plus random patches.

Measured cause [V-EXEC C47]: per-pixel fragmentation of the material index map is about the same as vanilla (boundary density 0.25 vs 0.29, median patch 5 vs 4 pixels). The difference is structure. The interim method copies Voronoi patches from vanilla land anywhere at a similar latitude, so neighbouring patches come from unrelated landscapes. Their borders are hard cuts, and nothing ties materials to climate, relief or the location templates [INFERRED].

## Requirements

1. Biomes form coherent regions with plausible shapes. Their size and shape statistics should be comparable to vanilla's.
2. Transitions between biomes are gradual ecotones, not hard edges or patch seams.
3. Biomes follow a physical model: latitude, elevation, distance to sea, prevailing winds, rain shadow and rivers.
4. Visual layers (heights, materials) and gameplay data (location templates: climate, vegetation, topography, raw materials) come from the same model, so a forest location looks like forest.
5. The output is deterministic and seam-free across decals. The Old World stays untouched.

## Algorithm plan

| Stage | Method | Output |
|---|---|---|
| 1. Relief | Plate or ridge skeleton for mountain ranges, so they form chains rather than blobs. Hypsometric shaping, then light hydraulic erosion. Rivers from flow accumulation carve valleys and feed `rivers.png` | Height field, river network |
| 2. Climate | Temperature from latitude, elevation lapse rate and ocean moderation. Moisture advected along latitude-band winds, with orographic rain and rain shadow behind ranges | Temperature and moisture fields |
| 3. Biome classification | Whittaker-style lookup calibrated on vanilla. Learn the joint distribution of vanilla templates' climate and vegetation against latitude, elevation and coast distance, then classify | Biome per pixel and per location |
| 4. Coherence | Classify at a coarse scale, apply a majority filter, enforce a minimum region area, warp boundaries with noise, define ecotone width per biome pair | Smooth biome map with ecotone weights |
| 5. Material synthesis | An exemplar library of vanilla material maps per biome, taken from vanilla locations of that biome. Image quilting on the categorical map: overlapping patches with minimum-error boundary cuts (Efros and Freeman, 2001). Ecotones blend the two biomes' syntheses by noise-dithered thresholds | Material layer without seams |
| 6. Gameplay consistency | Location templates take the majority biome, climate and topography of their pixels. Raw materials are drawn per biome from vanilla frequencies | `location_templates.txt` |

## Acceptance criteria

- **Biome coherence:** at least vanilla's on comparable areas. Measure the share of pixels equal to their 9×9 majority, and the distribution of region areas.
- **No visible patch structure:** gradient energy of the material map along synthesis-patch boundaries must not exceed interior levels by more than 10%.
- **Ecotones:** transitions between biomes have a measurable width of at least 8 location pixels, with no straight or grid-aligned edges.
- **Per-biome slot statistics:** within a set tolerance of the vanilla exemplars (for example, total variation ≤ 0.15).
- **Template agreement:** each location's vegetation matches its rendered biome for at least 95% of locations.
- **Owner review in game:** screenshots at continental, regional and close zoom.

## Place in the roadmap

Phase V1 in [roadmap](roadmap.md); it supersedes the visual part of R5. It can proceed in parallel with native civilizations (R6), because both read the same biome and template data.
