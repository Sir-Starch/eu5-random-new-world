# 030 — Why the roads vanished: the corrected spline network and an Old-World-only probe

Date prepared: 2026-10-23. **NOT-RUN: PREPARED, INSTALLED, NOT LAUNCHED.**

- **Background:** with the spline network of 0.9.30 (experiment 029) the game starts, writes no strip error and no crash, but draws no road anywhere, the Old World's included [V-GAME owner C164]. The difference to the 0.9.29 world, where roads draw, is that one file. 0.9.31 keeps vanilla's segments and points in vanilla's order (C165).
- **Hypotheses**, in the order the probes test them:
  - **H1** The engine relies on the order of segments or the numbering of points, which 0.9.30 changed for the Old World too (segments renumbered by the strips that use them). 0.9.31 does not change it: a map that lost nothing gets vanilla's bytes back.
  - **H2** Something in the added strips (a chain of short segments, new anchors beyond vanilla's highest index 27,923, the point numbering base 30,211) makes the engine drop the whole network.
  - **H3** The engine also needs data we did not regenerate: the 281 MB baked `navmesh2.cache` of vanilla's map in the same folder, or something else tied to vanilla's locations.
- **Method:** three launches, each with only the hub and one world in the playset; stop when roads return. For each, let a 1337 game run at speed for a minute, look at the roads on the map (Old World: Stockholm–Uppsala, Dublin–Naas; New World: the empires' tags below), then copy `debug.log` and `error.log` before the next launch (read `debug.log`: `error.log` rotates when something floods).
  1. **A: `rnw_exp_world_amk4jfomct`** (`RNW: Continents AMK4`, 0.9.31, code `RNW1-080G0-00003-EF38N-A004H-Y0813-BM0ET-JH64`): the product. Roads in the Old World, in the New World's empires (`YKO`, `RJT`, `VMI`, `UKM`)?
  2. If none: **B: `rnw_exp_probe_splnet_oldworld`**, the same map with a spline network that holds only the vanilla strips of the locations still there (16,605 anchors, 40,919 strips). Old World roads draw? (The generated roads will log the strip error again; that is expected.)
  3. If still none: **control: `rnw_exp_world_canszr3phf`** (0.9.29, vanilla's own file): do the Old World roads draw there at all, in this playset and at this zoom?
- **Reading the result:**

  | A | B | Control | Meaning |
  |---|---|---|---|
  | roads | not tested | not tested | H1 holds: the order mattered; done |
  | none | Old World roads | not tested | H2: the added strips break it; look at the added segments and anchors |
  | none | none | Old World roads | H1 refuted for the kept part, so renumbering, removal or H3 (vanilla's baked navmesh) |
  | none | none | none | the roads are not about this file in this playset; check the road lens and the owner's settings |

- **Diagnostics, optional and untested** (from the engine's own strings, [V-LOCAL] `local_data/re/eu5_strings.txt`): the console command `Draw.SplineNetwork` (the debug menu has a "Splines" button for it) draws the network the engine loaded: strips, anchors and segments; `SplineNetwork.Graphics.ClearAllSplines` followed by `SplineNetwork.Graphics.AddAllSplines` rebuilds the road graphics. If `Draw.SplineNetwork` shows the lines but no road draws, the network loaded and the road assets did not.
- **Files/tools:** `debug.log`, `error.log`, `report.json` (`text_stats.splines`) of the worlds; `rnw logdiff`.
- **Game version:** 1.4.3 open beta, build 26105915 [V-LOCAL C148]. Basis: C162, C164, C165; [interoperability register](../../docs/research/interoperability.md) R-001.
- **Result/evidence:** none yet.
- **Remaining uncertainty:** the engine's reader is not available, so the rules of the format are inferred from one vanilla file. If A, B and control all fail to explain it, the next step is to read how the engine loads the file, which is a different kind of work (the register records the method of each step; disassembly has not been done for this case).
- **Architecture implication:** If H2 holds, add strips more like vanilla's (shared segments, junction points). If H3 holds, the mod needs its own navmesh or the roads of generated land cannot work, and the generator should write no `road_network` pairs. If H1 holds, nothing more.
- **Status:** **NOT-RUN** — prepared and installed; the owner's test decides.
