# 008 — V1b rivers on a fresh random seed in game

- **Hypothesis:** Generated rivers that follow every vanilla `rivers.png` convention (C59) load in EU5 1.4.1, render as rivers with banks and valleys, and give locations river modifiers. A seed never tested before produces a different, valid New World.
- **Method:** The owner installs `rnw_exp_new_world` built from seed 3903742112 (continents, generator 0.6.0, C62) in place and starts a 1337 campaign. Check rivers at regional and close zoom (mouths, confluences, sources, width, valleys), the rivers map mode, a location tooltip for a river modifier, startup, and error.log for river or map messages. Compare a vanilla Old World river area at the same zoom.
- **Files/tools:** `generated/rnw_exp_new_world/` (report: `terrain.rivers`), `rnw logdiff` against the same-build baseline.
- **Game version:** 1.4.1 open beta, build 25905365 [V-LOCAL C01].
- **Result/evidence:** Installed by the owner on 2026-10-19 (commit 7c86a24; 712 files verified byte-identical). In-game run pending.
- **Remaining uncertainty:** whether the engine builds river meshes and modifiers from generated rasters without errors; whether rivers ending in lakes are handled; whether the 13-step width scale (only four steps used, as in vanilla) looks right.
- **Architecture implication:** If it passes, the New World's physical geography is complete for V1 and work moves to natives (R6).
- **Status:** **PENDING-HUMAN-VALIDATION**.
