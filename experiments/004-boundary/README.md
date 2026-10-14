# 004 — move a boundary between two existing cells

- **Hypothesis:** Recoloring a small connected pixel patch between neighboring existing IDs moves their actual in-game boundary while preserving references.
- **Method:** After experiment 003, choose two cells away from Old World and sea edges. Change only a small synthetic patch in a locally generated full raster, keep colors/IDs stable, validate topology and unchanged pixels outside the target. Measure map appearance, selection, movement and logs. Generate from the player's own installed raster locally; never commit or redistribute it.
- **Files/tools:** `locations.png`, named color map, optional terrain and cache layers, geography validator, `rnw logdiff`.
- **Game version:** Target 1.4.1 open beta, build 25905365 [V-LOCAL C01].
- **Result/evidence:** An offline land–sea variant is prepared but not run in game. `uv run rnw generate --game-dir "$EU5_GAME_DIR" --seed 42 --preset continents --output generated/rnw_exp_d0_coast_s42` stages a mod with only `locations.png` and `rivers.png`. It moves 16,205 pixels between existing American land and sea IDs and keeps all cell contacts and all pixels outside the window [V-EXEC C28]. No game run [UNKNOWN C13].
- **Remaining uncertainty:** Override contract, derived centers/ports/nodes, cache invalidation and pathfinding.
- **Architecture implication:** Gates T2 ID-preserving reshape.
- **When authorized:** After 002–003, install only `generated/rnw_exp_d0_coast_s42/rnw_exp_d0_coast_s42` into the isolated profile with `rnw install-mod`, record it in [INSTALLED](../INSTALLED.md), and check against a same-build baseline: error log, location borders/selection in the window, unit movement onto moved coast, naval movement, ports near frozen coasts, save/reload. Expect a drawn-terrain mismatch (C25).
- **Installation:** 2026-10-14, normal profile `mod/rnw_exp_d0_coast_s42`, byte-identical to the manifest; see [INSTALLED](../INSTALLED.md). Baseline logs without the mod are in gitignored `local_data/baseline/2026-10-14-normal-no-rnw/`.
- **Status:** **NOT-RUN** in game (installed, not yet launched with it); candidate **PREPARED OFFLINE**, NOT GAME VALIDATED.
