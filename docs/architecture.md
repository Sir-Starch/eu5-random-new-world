# Architecture options and decision gates

The production architecture is conditional on [experiments 002–006](../experiments/) and [feasibility](feasibility.md). [ADR 0001](adr/0001-python-research-tooling.md) decides only the research kit stack. The D0 offline generator and an ID-preserving EU5 exporter now exist ([ADR 0002](adr/0002-d0-generator-stack.md)); neither is game validated.

| Option | Benefits | Costs and evidence gate |
|---|---|---|
| A. In-game dynamic generation | Direct campaign flow, no prelaunch install | No EU5 1.4.1 topology mutation API verified [UNKNOWN C13]; requires engine/`script_docs` probe plus live test |
| B. External preprocessing of a versioned template | Good seed and preview workflow; can compute large rasters outside game | Needs reliable mod override and clear rights to any template; test 002–006 [INFERRED C03–C14] |
| C. Standalone generator emitting a complete mod | Clear validation boundary and reproducible artifact; Linux/Windows friendly | Full file coupling, loader behavior and local-only vanilla derivation must be solved; test 002–006 [INFERRED C03–C15] |
| D. Curated pre-generated worlds | Predictable QA per world, simpler player install | Limited variety, storage and asset rights; still needs T2/T3 mod acceptance [INFERRED] |
| E. External geography plus in-game political roll | Could reduce number of packaged seeds | Requires both static geography acceptance and a proven script hook for politics; untested [UNKNOWN C13] |

**Conditional recommendation:** C, with B as a local generation technique. Keep game-specific adapters behind a build fingerprint and validate before installing. **Runner-up:** an ID-preserving T2 exporter if new IDs fail while pixel boundary edits work. A switch to T0 alone would not meet the product goal. [INFERRED C03–C14]

## Minimal conceptual pipeline, subject to validation

`settings + seed + game build fingerprint → abstract geography and society model → validators → EU5-specific serializers → complete mod package → manual launcher enablement → in-game regression evidence` [INFERRED]. The world model must distinguish IDs, color raster cells, geographic parents, land/sea class, graph edges and start-state entities. Implemented so far [V-EXEC C28–C31]:

| Stage | Module | State |
|---|---|---|
| Settings, seed, RNG | `settings.py`, `rng.py`, `noise.py` | Schema 1, two presets, SplitMix64 v1, integer noise |
| World model | `model.py`, `topology.py` | Label raster, cells, classes, parents, anchors, edges; new IDs supported |
| Generators | `synth.py` (T3-style, synthetic), `coast.py` (T2 boundary moves) | Deterministic, offline |
| Validators | `validate.py` | Typed errors, generic and boundary-move checks |
| EU5 adapter and serializer | `eu5_map.py`, `eu5_export.py`, `png.py`, `artifacts.py` | Build 25905365 only; emits `locations.png` + `rivers.png` |
| T3 New World | `newworld.py`, `eu5_canvas.py`, `eu5_newworld.py`, `eu5_rewrite.py`, `eu5_remap.py`, `eu5_nw_export.py`, `pdx.py`, `names.py` | New IDs, empty 1337 start; plays in game [V-GAME C45] |
| Relief and climate (V1) | `fields.py`, `relief.py`, `climate.py` | Game-independent integer fields: warped rotated noise, mountain belts, Euclidean distance, zonal-wind rainfall |
| Rivers (V1b) | `rivers.py` | Game-independent priority-flood drainage, rain-weighted catchments, one-pixel river networks drawn head-down, valley carving; EU5 codes in `eu5_nw_export.py` |
| Biomes and terrain (V1) | `eu5_biomes.py`, `eu5_slots.py`, `eu5_terrain.py`, `eu5_objects.py`, `eu5_water.py`, `terrain_tiles.py`, `lzav.py`, `dds.py` | Templates from a calibrated climate model; decal heights and material slots by vanilla rules; vegetation instances; water textures; NOT GAME VALIDATED ([terrain-biomes](terrain-biomes.md)) |

Native start-state entities (R6) are not generated yet; the New World starts empty.

The exporter should read any vanilla-derived data from the user's local game installation and write generated assets only to gitignored/local mod directories [INFERRED C15]. It must preserve Old World pixel regions, identifiers and references by explicit tests. A package manifest should record seed, settings schema, generator version, target game build and hashes without embedding proprietary input files.

## Open design decisions

1. **T3 versus T2/T1.5:** requires a new-ID, moved-boundary and cell-class experiment with visible movement/naval checks (experiments 003–006) [UNKNOWN C13].
2. **Map representation:** full raster, polygon/graph, or hybrid; needs real override semantics, pixel/heightmap requirements and a benchmark on 134M pixels [V-LOCAL C03,C07; UNKNOWN].
3. **Serialization:** parser/round-trip fidelity for BOM, comments and order; needs minimal-file override test and synthetic fixtures before broad rewriting [V-LOCAL C04,C08; UNKNOWN].
4. **Performance core:** Python array libraries versus a Rust core, benchmark after first accepted raster edit; ADR 0001 does not decide this [UNKNOWN].
5. **UI/install:** CLI first versus cross-platform GUI, after the output contract and security of user-path detection are proven [UNKNOWN].

Patch policy: discover the installed version and branch each run, compare a known contract fingerprint, and refuse unsupported builds until an explicit regression pass. The `1.4.*` metadata match is not a promise that all future 1.4 patches accept the same map files [V-GAME C11; INFERRED C18].
