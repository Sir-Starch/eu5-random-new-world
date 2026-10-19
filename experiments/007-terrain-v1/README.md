# 007 — V1a terrain and biomes in game

- **Hypothesis:** Generated templates, slot-coded material decals, continuous relief and regenerated vegetation instances make the New World look coherent, like vanilla terrain: biomes fill whole zones, transitions follow location borders as soft bands, mountains form ranges, and forests have trees.
- **Method:** The owner installs the V1a build of `rnw_exp_new_world` (C53) in place and starts a 1337 campaign. Screenshots at continental, regional and close zoom over forest, grassland, desert, jungle, mountains and coasts. Compare with a vanilla Old World area at the same zoom. Check map modes for climate, vegetation and topography, startup time, and error.log for messages about map objects, biomes or decals.
- **Files/tools:** `generated/rnw_exp_new_world/` (report: `biomes`, `terrain.objects`), `rnw logdiff` against the same-build baseline.
- **Game version:** 1.4.1 open beta, build 25905365 [V-LOCAL C01].
- **Result/evidence:** Installed by the owner on 2026-10-19 (commit 10e931f; 712 files verified byte-identical with the manifest). The owner's run loaded a 1337 start with the generated terrain (C55). Defects: a crack along the map wrap, square city models with a corner in water, brown pixel patches in white desert, and green city ground in sand. Causes and the V1a.1 fixes (generator 0.5.0) are in [terrain-biomes](../../docs/terrain-biomes.md) and C56.
- **Remaining uncertainty:** whether the engine accepts the whole-file instance overrides (8.5 million new instances) and their memory and startup cost; whether every generated template combination resolves to a sensible biome; how the 1.4 GB mod affects loading.
- **Architecture implication:** If it passes, terrain is generated from one model and only rivers (V1b) and natives (R6) remain for the New World's look and life.
- **Status:** V1a **PARTIAL** (loads; four visual defects). V1a.1 **PENDING-HUMAN-VALIDATION**.
