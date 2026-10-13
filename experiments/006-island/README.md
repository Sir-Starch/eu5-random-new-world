# 006 — playable generated island

- **Hypothesis:** A handful of new land locations in one area/region and an adjacent sea zone can load, be explored and colonized/conquered, and permit ships to route around the island.
- **Method:** After experiment 005, generate a tiny coherent graph and its raster, hierarchy, terrain, rivers, ports, setup and sea routes. Validate all IDs and connections offline. In game, inspect exploration, colony/conquest, trade, ship routes, 1337 start, save/reload and Old World regression; compare logs and startup time with a same-build baseline.
- **Files/tools:** full geography/start-state test mod emitted locally, offline graph/raster validator, `rnw logdiff`, game UI.
- **Game version:** Target 1.4.1 open beta, build 25905365 [V-LOCAL C01].
- **Result/evidence:** No mod generated or game run [UNKNOWN C13].
- **Remaining uncertainty:** Every T3 contract; performance and patch stability.
- **Architecture implication:** Successful completion would justify production T3 design. Until then, it is a research objective.
- **Status:** **NOT-RUN**; prerequisite experiments incomplete and no further game launches this session.
