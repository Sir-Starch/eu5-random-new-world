# 004 — move a boundary between two existing cells

- **Hypothesis:** Recoloring a small connected pixel patch between neighboring existing IDs moves their actual in-game boundary while preserving references.
- **Method:** After experiment 003, choose two cells away from Old World and sea edges. Change only a small synthetic patch in a locally generated full raster, keep colors/IDs stable, validate topology and unchanged pixels outside the target. Measure map appearance, selection, movement and logs. Generate from the player's own installed raster locally; never commit or redistribute it.
- **Files/tools:** `locations.png`, named color map, optional terrain and cache layers, geography validator, `rnw logdiff`.
- **Game version:** Target 1.4.1 open beta, build 25905365 [V-LOCAL C01].
- **Result/evidence:** No raster generated or game run [UNKNOWN C13].
- **Remaining uncertainty:** Override contract, derived centers/ports/nodes, cache invalidation and pathfinding.
- **Architecture implication:** Gates T2 ID-preserving reshape.
- **Status:** **NOT-RUN**; blocked by earlier experiment and no further game launches this session.
