# Architecture options and decision gates

> [!NOTE]
> **Historical record.** The options below were written before the experiments decided between them. Option C was chosen: a standalone generator writes one complete mod per world on the player's machine and is delivered in a Workshop item ([ADR 0009](adr/0009-hub-mod-with-generator.md), [ADR 0010](adr/0010-layered-worlds-and-a-generator-of-its-own.md)).

The following options and their original conditions are historical; the current implementation is summarized in the pipeline below. [ADR 0001](adr/0001-python-research-tooling.md) decides only the research kit stack. The D0 offline generator and an ID-preserving EU5 exporter now exist ([ADR 0002](adr/0002-d0-generator-stack.md)); neither is game validated.

| Option | Benefits | Costs and evidence gate |
|---|---|---|
| A. In-game dynamic generation | Direct campaign flow, no prelaunch install | Not possible with vanilla mechanisms: the 1.4.1 executable has no random-map generator, mods cannot run code, and no script effect changes land, sea, relief or climate [V-LOCAL/INFERRED C83] |
| B. External preprocessing of a versioned template | Good seed and preview workflow; can compute large rasters outside game | Needs reliable mod override and clear rights to any template; test 002–006 [INFERRED C03–C14] |
| C. Standalone generator emitting a complete mod | Clear validation boundary and reproducible artifact; Linux/Windows friendly | Full file coupling, loader behavior and local-only vanilla derivation must be solved; test 002–006 [INFERRED C03–C15] |
| D. Curated pre-generated worlds | Predictable QA per world, simpler player install | Limited variety, storage and asset rights; still needs T2/T3 mod acceptance [INFERRED] |
| E. External geography plus in-game political roll | Could reduce number of packaged seeds | Requires both static geography acceptance and a proven script hook for politics; untested [UNKNOWN C13] |

**Original conditional recommendation:** C, with B as a local generation technique. Keep game-specific adapters behind a build fingerprint and validate before installing. **Runner-up:** an ID-preserving T2 exporter if new IDs fail while pixel boundary edits work. A switch to T0 alone would not meet the product goal. [INFERRED C03–C14]

**Delivery decision (2026-10-21, [ADR 0009](adr/0009-hub-mod-with-generator.md), replacing ADR 0004 and ADR 0008):** one Workshop item carries the data mod and the generator, which the player starts from the game's Open in folder; the world is a second, local mod. Earlier, ADR 0004 chose option C as a local application with a window. It generates from the player's installation, installs the world in place, and earlier experiments observed mod reload behavior (C85, C88); later evidence supports restarting before switching maps ([known limitations](known-limitations.md)).

## Current pipeline

`settings + seed + game build fingerprint → abstract geography and society model → validators → EU5-specific serializers → complete mod package → in-place installation → new game from the main menu → in-game regression evidence` [INFERRED]. The world model must distinguish IDs, color raster cells, geographic parents, land/sea class, graph edges and start-state entities. The D0 components and the later New World pipeline are summarized below [V-EXEC C28–C31, C410]:

| Stage | Module | State |
|---|---|---|
| Settings, seed, RNG | `settings.py`, `rng.py`, `noise.py` | Schema 1, two presets, SplitMix64 v1, integer noise |
| World model | `model.py`, `topology.py` | Label raster, cells, classes, parents, anchors, edges; new IDs supported |
| Generators | `synth.py` (T3-style, synthetic), `coast.py` (T2 boundary moves) | Deterministic, offline |
| Validators | `validate.py` | Typed errors, generic and boundary-move checks |
| EU5 adapter and serializer | `eu5_map.py`, `eu5_export.py`, `png.py`, `artifacts.py` | Original D0 adapter, initially tested against build 25905365; the current New World exporter is listed below |
| T3 New World | `newworld.py`, `hierarchy.py`, `eu5_canvas.py`, `eu5_newworld.py`, `eu5_rewrite.py`, `eu5_remap.py`, `eu5_events.py`, `eu5_nw_export.py`, `pdx.py`, `names.py` | New IDs; plays in game [V-GAME C45] (first with an empty 1337 start) |
| Relief and climate (V1) | `fields.py`, `relief.py`, `climate.py` | Game-independent integer fields: warped rotated noise, mountain belts, Euclidean distance, zonal-wind rainfall |
| Rivers (V1b) | `rivers.py` | Game-independent priority-flood drainage, rain-weighted catchments, one-pixel river networks drawn head-down, valley carving; EU5 codes in `eu5_nw_export.py` |
| Biomes and terrain (V1) | `eu5_biomes.py`, `eu5_slots.py`, `eu5_terrain.py`, `eu5_objects.py`, `eu5_water.py`, `terrain_tiles.py`, `lzav.py`, `dds.py` | Templates from a calibrated climate model; decal heights and material slots by vanilla rules; vegetation instances; water textures; accepted in game (C58, C66) ([terrain-biomes](terrain-biomes.md)) |
| Native societies (R6) | `societies.py`, `eu5_natives.py` | Game-independent hearths, complexity, population, nested religion/culture zones, states and tribes on the location graph; EU5 calibration on the vanilla 1337 Americas, vanilla culture/religion matching by homeland, new tags, pops, countries, towns, markets, holy sites; plays in game (C69) ([natives](natives.md)) |
| Economy & development (R7a) | `eu5_development.py` | Starting development keyed by society complexity, river terms, vanilla-calibrated harbour capacities, and market villages ([economy](economy.md)) |
| Technology & empires (R7b, R7c) | `eu5_technology.py`, `eu5_empires.py`, `splnet.py`, `eu5_splines.py` | Complexity-derived tech levels, great empires, royal roads with valid spline strips ([R7 design](r7-technology-and-empires.md)) |
| Extraordinary societies (R7d) | `archetypes.py`, `eu5_archetypes.py` | Sea leagues, highland confederations, fractured realms, sacred centres with vanilla-compatible structures and trade-offs |
| Sea geography & currents (S1, S2) | `seas.py`, `seanames.py`, `ports.py`, `lanes.py`, `straits.py`, `currents.py`, `sea_corridors.py`, `sea_policy.py`, `eu5_oceans.py`, `eu5_seas.py` | Ports for coastal zones, shape-aware names, deep shipping lanes, replaced-band currents, continuous crossing corridors, and army straits ([sea geography](sea-geography.md)) |
| Dynamic content & stories (N0–N5) | `content_inventory.py`, `content_decisions.py`, `content_check.py`, `eu5_content.py`, `content.py`, `storymodel.py`, `stories.py`, `stories_n4.py`, `stories_colonial.py`, `colonial_names.py`, `formations.py`, `eu5_story.py`, `eu5_formation.py`, `eu5_places.py` | Cleanly gated/rebound vanilla American content, formable nations, procedural stories, rare resource sites, and region-key mapping ([content plan](content-plan.md)) |
| Localization (L1) | `languages.py`, `translations.py`, `game_texts.py`, `wording.py`, `translit.py` | Complete translation across all 11 official EU5 languages, with script-native transliteration and grammar rules ([localization](localization.md)) |
| Application & native core | `native/` (Rust), `rnw/app/`, `rnw/gui/` | High-performance SIMD/parallel kernels, headless generator controller, and current Qt desktop interface; Tauri migration is planned, not implemented ([roadmap](roadmap.md)) |

The 1337 start now has generated native societies instead of an empty New World.

The exporter should read any vanilla-derived data from the user's local game installation and write generated assets only to gitignored/local mod directories [INFERRED C15]. It must preserve Old World pixel regions, identifiers and references by explicit tests. A package manifest should record seed, settings schema, generator version, target game build and hashes without embedding proprietary input files.

## Historical design questions

These questions describe the early research stage, not current unresolved choices: T3 generation, the Rust core and the Qt application have since been implemented. Current future work, including the planned Tauri transition, is in the [roadmap](roadmap.md).

1. **T3 versus T2/T1.5:** requires a new-ID, moved-boundary and cell-class experiment with visible movement/naval checks (experiments 003–006) [UNKNOWN C13].
2. **Map representation:** full raster, polygon/graph, or hybrid; needs real override semantics, pixel/heightmap requirements and a benchmark on 134M pixels [V-LOCAL C03,C07; UNKNOWN].
3. **Serialization:** parser/round-trip fidelity for BOM, comments and order; needs minimal-file override test and synthetic fixtures before broad rewriting [V-LOCAL C04,C08; UNKNOWN].
4. **Performance core:** Python array libraries versus a Rust core, benchmark after first accepted raster edit; ADR 0001 does not decide this [UNKNOWN].
5. **UI/install:** CLI first versus cross-platform GUI, after the output contract and security of user-path detection are proven [UNKNOWN].

Patch policy: discover the installed version and branch each run, compare a known contract fingerprint, and refuse unsupported builds until an explicit regression pass. The `1.4.*` metadata match is not a promise that all future 1.4 patches accept the same map files [V-GAME C11; INFERRED C18].
