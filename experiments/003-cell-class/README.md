# 003 — existing-cell geography and class

- **Hypothesis:** An existing coastal location ID can change a terrain/climate attribute, then potentially switch land/sea/lake class with aligned map layers.
- **Method:** First make one visible attribute change, retaining geometry and ID. If it loads, test class change in a separate mod with `default.map` lists, templates, setup, coastline visuals and connectivity updated consistently; inspect land/naval movement and log delta. Do not conflate attribute and class success.
- **Files/tools:** `location_templates.txt`, `default.map`, `locations.png`, `rivers.png`, `gfx/terrain2/`, `rnw logdiff`.
- **Game version:** Target 1.4.1 open beta, build 25905365 [V-LOCAL C01].
- **Result/evidence:** No mod prepared or game run [UNKNOWN C13].
- **Remaining uncertainty:** Mandatory visual layers, cache rebuild, pathfinding, whether a land/sea class switch is permitted.
- **Architecture implication:** Attribute success gates T1; class success gates T1.5.
- **Status:** **NOT-RUN** because the owner requested no further game launches this session.
