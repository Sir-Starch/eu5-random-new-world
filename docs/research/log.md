# Research log

## 2026-10-13

- Initialized the repository and evidence policy before inspecting the game. No game behavior has yet been verified.
- [V-LOCAL] Found Steam app 3450310 on branch `1.4-open-beta`, build 25905365, with a Windows executable run through Proton. Inventoried map rasters, hierarchy, setup and user paths; see `game-install-inventory.md`.
- [V-EXEC] `rnw inspect` counted 28,573 location keys and 6,174 in America. This is a syntax/hierarchy count, not a proof that all have map colors or playability.
- [V-GAME] A normal launch reached the EU5 1.4.1 main menu. A later isolated profile recognized the metadata-only test mod, but opened a first-run Select Language screen that did not respond to input. After the owner reported this, the game and input helper were stopped. No further launches are authorized in this session.
- [V-EXEC] Ran a lexical cross-reference scan. It found 104 candidate file categories and 106,418 summed distinct-key/file hits. This is a deliberately broad inventory with false positives; precise dependency and failure classifications remain open.
- [SOURCE] Reviewed Paradox terms, the EU4 Conquest of Paradise product page and two EU5 community repositories. Only the terms and product page support current claims; the 1.3.11 engine atlas is a lead, not 1.4.1 proof.
- [INFERRED] Revised the working architecture toward external generation conditional on a real map override test. The highest in-game geographic tier remains unverified, including T0.
- [V-EXEC] Built a metadata preparation/installation CLI, read-only hierarchy inspector, broad coupling scan and log diff. Added synthetic tests, optional local-install test, Linux/Windows CI and `uv` lockfile. `make check` passed with 4 tests and 1 local-only skip.
- [V-GAME]/[V-EXEC] Experiment 001 ended INCONCLUSIVE: version matching was logged, but complete comparable error-free startup was not established (900 baseline versus 898 current error-log lines). Recorded experiments 002–006 as NOT-RUN after the owner requested no more game launches.
- [INFERRED] Completed conditional external-generator recommendation, T2 runner-up, roadmap, product goals, legal/distribution risk and handoffs. These design documents preserve the distinction between local static files and in-game behavior.
- [V-EXEC] Cloned the committed repository into a fresh temporary directory and ran `uv sync --locked --group dev` followed by `make check`: 4 tests passed, 1 local-only test skipped, Ruff and basedpyright passed. Audited tracked file sizes (largest: 20 KiB lockfile), local Markdown links (none missing), ignored generated/local/third-party data and README/feasibility/handoff status agreement. The task brief remains local and ignored.

## Continued research, 2026-10-13

- [V-EXEC] Found and corrected an evidence error: the first color regex omitted inline-comment lines and mixed-case keys, yielding a false 22,314 count. The corrected read finds 28,582 color declarations, all 28,573 hierarchy keys covered, nine extra declarations, and no duplicate names/colors. Revised C05 and all dependent documents; no game behavior was inferred.
- [V-EXEC] Counted `default.map` class lists: 4,793 distinct sea, 918 lake, 1,868 impassable and 153 non-ownable tokens. American hierarchy intersects those lists in 984, 292, 460 and 7 keys respectively, with possible overlap. This ruled out a simple `continent = america` land mask for the generator.
- [V-EXEC] Added strict named-color parsing, stronger hierarchy errors and synthetic regression tests. Added a bounded-memory SHA-256 map-contract fingerprint command; its local raw output is ignored, and the ten-file aggregate digest is in C20. No game launch or game-directory write occurred.
- [SOURCE] Evaluated REA and a 1.4 map-mod Workshop lead. Neither was executed or treated as proof of EU5 1.4.1 topology support. Local GNU `objdump` exists, but no full decompiler provider is installed [V-LOCAL].
- [V-LOCAL]/[INFERRED] Compared only the temporary and normal `pdx_settings.json` files: the temporary profile lacks the `first_time_playing` flag found as `false` in the normal profile. This may explain the first-run screen, not its lack of input response; no game workaround was tested.
- [V-EXEC] Refocused the Opus handoff on implementing a seeded geography-changing `rnw_exp_*` package candidate now, with offline invariants and future T3 capacity. `make check` passed 11 synthetic tests with 1 local-only skip; the optional local installation test passed. All Markdown relative links resolve.

## 2026-10-14 — D0 geography candidate (Opus)

- [V-EXEC] Raster audit of build 25905365: all pixels declared; the nine extra colour declarations are the nine zero-pixel colours (C23). `rivers.png` background is a water/land mask (C24). Locator/port rows are flipped (C26).
- [V-LOCAL]/[V-EXEC] `terrain2/heightmap.png` turned out to be a partial Eurasia/Africa layer with no Americas; the real terrain uses 65536×32768 decal tiles and a cache (C25). The planned heightmap adjustment was dropped; the visual mismatch is reported as untested.
- [V-EXEC] Implemented the D0 slice: SplitMix64 RNG and integer fractal noise; game-independent `World` model with new-ID support; synthetic generator with `continents`/`archipelago` presets; contact-preserving coast mover; typed validators; deterministic PNG writer; read-only EU5 adapter; staged exporter with manifest and report; `rnw synth` and `rnw generate`. Added `numpy` and `pillow` dependencies.
- [V-EXEC] `rnw generate --seed 42 --preset continents` produced `generated/rnw_exp_d0_coast_s42` in about 10 s: 16,205 pixels moved, all invariants passed after re-decoding the files, and a repeat run was byte-identical (C28). The archipelago preset and seed 7 gave different geometry (C29). Only `generated/` was written; nothing was installed and the game was not launched.
- [SOURCE] Verified the SplitMix64 constants and a seed-1234567 vector against the reference C file and Rosetta Code (C33).
- [V-EXEC] `make check` passes with 68 synthetic tests and 2 local-only skips; the optional local tests pass against the installation. Windows CI has not run because nothing was pushed (C31).
- [V-EXEC] A fresh clone of branch `d0-geography-candidate` passed `uv sync --locked --group dev && make check` (68 passed, 2 local-only skips). Tracked files total 456 KiB; no game-derived file is tracked.
- [V-LOCAL] Owner installed `rnw_exp_d0_coast_s42` into the normal profile's new `mod/` folder (12:35); the agent verified the installed files are byte-identical to the manifest. Baseline logs from the owner's 12:31 launch without the mod were copied to gitignored `local_data/baseline/2026-10-14-normal-no-rnw/`. That log also shows the active playset references two Workshop mods whose metadata the game could not open; they were not touched.
- [V-GAME] Owner launched EU5 1.4.1 with `rnw_exp_d0_coast_s42` in a separate playset: the mod mounted, location outlines followed the generated raster (Erie encloses lake pixels moved by the mod), drawn terrain stayed vanilla (C34). Error-log triage found nothing related to changed locations, but the baseline stage differed (C35).
- [V-LOCAL]/[V-EXEC] Mapped the drawn relief: 16 height decals on a 4×4 grid, 2 decal pixels per location pixel, LZAV-compiled tiles plus 16-bit PNG sources; heights > 2300 match land at 99.1% in a US region (C36). A visual coastline needs generated height (and likely material) decals; which file the engine reads (PNG or `.bin`) is the next experiment.
- [V-OWNER DECISION] After the D0 result the owner asked for real generation: new IDs, an empty 1337 New World, visible terrain. Built `rnw newworld` (T3): seeded continents on an America+ocean canvas, new locations/provinces with reused area/region names, rewritten map/setup/localization files, and rebuilt terrain decals (C38-C42). The format work used a locally compiled reference LZAV decoder only as a test oracle (C39).

## 2026-10-15 — first T3 launch

- [V-GAME] The T3 candidate loaded map, setup, scripts and the modified decal cache but crashed while starting 1337, right after failing to set up a holy site on a removed location (C43). Built v2 with script-reference remapping, area adoption, locator fixes and a location cap (C44).
- [V-GAME] v2 loaded into a playable 1337 start with the generated continent (C45) — first in-game proof of generated New World geography with new IDs. Visual defects traced to lake meshes, water/foam textures, per-decal fields and cliff heights; all rebuilt offline (C46).

## 2026-10-19 — owner review of terrain

- [V-GAME owner observation] Coasts and water accepted as fixes; terrain still pixelated and incoherent up close. Measured that per-pixel fragmentation matches vanilla, so the missing piece is biome structure (C47). Recorded the mandatory terrain/biome synthesis phase V1 with algorithm and acceptance metrics.

## 2026-10-19 — V1a terrain and biome synthesis

- [V-LOCAL] Found the rendering model: per-location biomes from template climate, vegetation and topography; slot-coded material layers; pre-placed vegetation instances (C50, C52). This replaced the planned exemplar quilting with reverse-engineered vanilla rules.
- [V-EXEC] Measured vanilla slot rules on four decals and reproduced them (85.6% structural agreement, C51); calibrated relief heights per topography (C48) and latitude anchors (C49).
- [V-EXEC] Implemented `fields.py`, `relief.py`, `climate.py`, `eu5_biomes.py`, `eu5_slots.py`, `eu5_objects.py`, the rebuilt `eu5_terrain.py` and organic border wobble; removed the interim patch-transfer `terrain_materials.py`. Generator version 0.4.0. `make check`: 84 passed, 2 local-only skips; the three local tests pass.
- [V-EXEC] Built `rnw_exp_new_world` V1a (C53): coherent climate bands, vegetation zones and per-vegetation tree densities matching the Old World. Not installed by the agent; NOT GAME VALIDATED.

## 2026-10-19 — V1a review and V1a.1 fixes

- [V-GAME owner observation] V1a loads and renders; owner reported a crack along the map wrap, city models with a corner in water, brown pixel patches in white desert and green city ground in sand (C55).
- [V-LOCAL] Found that most biome material lists are shorter than 16, that the shader clamps slots to 15, and that material 0 is `fallback_material`; vanilla city ground is green for every non-Mediterranean biome (C54, C56).
- [V-EXEC] Generator 0.5.0: seam strait, shore-aware city points, slots limited to each biome's list, no desert wetlands.
- [V-GAME owner review] V1a.1 (commit 80b0a2d) installed, checked in game and accepted (C58).

## 2026-10-19 — V1b rivers

- [V-OWNER DECISION] Generation must be verified as random, not tuned to one continent: validate several seeds and presets offline, and use a fresh seed for the next in-game build.
- [V-LOCAL] Measured the vanilla `rivers.png` conventions and statistics (C59).
- [V-EXEC] Implemented `rivers.py` (priority-flood drainage, rain-weighted catchments, head-down drawing with join pixels, valley carving) and the EU5 encoding; generator 0.6.0. Five worlds over two presets pass every river rule, the seam strait and the city-point checks (C60). `make check`: 93 passed.
- [V-EXEC] The first full export on a fresh random seed failed sea reachability: land enclosed the sea around a protected islet. Added strait cutting for enclosed seas (C61). `make check` 88 passed; the three local tests pass.
- [V-EXEC] Full exports of continents 7, continents 2026 and archipelago 5 pass every invariant and river rule, about 10 minutes each (C63). The first batch had been left running unattended in the background; the owner killed it as hung. Long exports now run one at a time under a timeout while the agent waits.

## 2026-10-19 — V1b accepted; seed-driven coastlines (V1b.1)

- [V-GAME owner review] Hydrology approved; V1b rivers accepted. Defect: the north-west ("Alaska") was the same as in the previous seed (C64).
- [V-EXEC] Cause: the canvas-edge ramp grew with `feature_px` (533 px) and left only the canvas core for the land budget, so all seeds filled the same outline (IoU 0.53–0.67). Generator 0.7.0 shares one guard for the canvas edge, the seam and strait axes, with a 4-margin ramp moved inland by stretched warped noise; slivers stay sea; the wobble cap bug that speckled archipelago land is fixed. Enclosed seas get a strait axis in the guard instead of a straight canal. Overlap is now 0.31–0.45 (C64). `make check`: 96 passed; the three local tests pass.
- [V-EXEC] Built seed 3706823338 (C65); all invariants and river rules pass.
- [V-GAME owner review] V1b.1 checked in game and accepted (C66). V1 physical geography is accepted; work moves to natives (R6). The owner asked to batch changes and request a game test only when one is really needed.

## 2026-10-19 — R6a native societies

- [V-LOCAL]/[V-EXEC] Surveyed the vanilla 1337 American setup read-only: pops, landed and `type = pop` countries, tag definitions, templates, town setups, markets, holy sites and densities (C67).
- [V-EXEC] Implemented `societies.py` (game-independent hearths, complexity, population, nested religion and culture zones, states, tribes, ranks and markets on the location graph) and `eu5_natives.py` (vanilla calibration, homeland matching of vanilla American cultures and religions, new tags, pops, countries, definitions, names, towns, markets, holy sites); generator 0.8.0 with a `natives` settings section. Tuning on cached worlds: state land as a quota (11%) instead of a complexity threshold; hearths scored by food within half a reach, so a lone fertile islet no longer wins; a growing-season factor keeps hearths below about 50°; cultures reuse their own religion's pool before foreign ones, and an unused identity must fit within a slack. `make check`: 107 passed; the four local tests pass.
- [V-EXEC] Full build on fresh random seed 3200056429 passes every invariant; every native reference resolves against the 1.4.1 definitions (C68). Experiment 010 (in game) is next.
- [V-GAME owner review] R6a loads; states show with names, flags and rulers. Defect: stepped terra incognita edge (C69). The shader blends visibility over one location pixel only; the next build patches `terra_incognita.shader` (read from the local install) to average 13 samples within two pixels near edges, and natives now know the seas along their coasts.

## 2026-10-19 — R6b names and vassals

- [V-LOCAL]/[V-EXEC] Vanilla place names, culture languages and families, and diplomacy setup read (C70).
- [V-EXEC] Generator 0.9.0: `names.MarkovNames` (order-3 character chain, never copies its corpus) and `eu5_natives.PlaceNamer` name land, wastelands, provinces, areas, states and tribes in the local culture's language with back-off to family, religion and all Americas; the largest 5% of states take bordering co-religionist states as vassals; natives know their coastal seas; the terra incognita shader was softened (removed again, see below). `make check`: 111 passed.
- [V-GAME owner review] R6b works overall; border lines did not follow the fill at close zoom (C71). Cause: `wobble_borders` discarded the bending of every border when one cell vanished; generator 0.9.1 repairs only the affected cells. The owner asked to keep the vanilla terra incognita and fix the map instead; the shader patch is removed. The generated terrain coastline follows the raster as closely as vanilla's (C72).

## 2026-10-19 — Product rules and versioning

- [OWNER DECISION] Vanilla first and no crutches: no patched engine files, no self-repairing output; fix the generator at the source (AGENTS.md).
- [OWNER DECISION] One SemVer product version for the Steam Workshop ([ADR 0003](../adr/0003-versioning.md)): 0.MINOR.PATCH development (MINOR per phase accepted in game), and the first publication is the complete product, 1.0.0 (owner correction the same day). The four drifting version strings (three mod metadata versions and the generator output version 0.9.1) are replaced by `version` in `pyproject.toml`; run specs carry `version` instead of `generator_version`. The owner kept the number the work was tracked by: 0.9.1.

## 2026-10-19 — R7a design: development and market villages

- [V-LOCAL]/[V-EXEC] Read the vanilla 1337 economy setup of the Americas (C73). Development is the sum of rules in `14_development.txt`. The Americas get their civilisation level from region, province and location entries (Mesoamerica 12, Andes 10, and so on). They have no institutions or roads. Their buildings are 88, 79 of them market villages in state capitals. Build 25905365 is unchanged.
- [V-EXEC] The 0.9.1 build of seed 517130602 keeps the American region entries, so development follows the old region positions, not the generated societies (C74). Every generated port gets harbour 0.50 (vanilla American harbour values: 758‰ at zero, 13 of 1,092 negative). Generated natives have no buildings.
- [V-EXEC] Probes: copying vanilla's per-class bonus would over-develop states (8.7–10.6 against 4.1), because generated hearths lie on better land. A term of 12 × complexity lands near vanilla's class means. Coast enclosure predicts vanilla harbour values only weakly (Spearman 0.10–0.19).
- Designed R7a for Sonnet in [R7a design](../r7a-development.md): drop the positional entries; a society term `round(B × complexity / 1000)` with B calibrated from vanilla (12); harbour values quantile-mapped from the vanilla American distribution by shelter; market villages in the vanilla share of capitals, most complex first. It adds invariants, a report section, offline acceptance on three worlds and experiment 012 for the owner. No code changed.

## 2026-10-19 — R7a implemented (product version 0.9.2)

- [V-EXEC] `eu5_development.py` and the export wiring follow the design: positional American development entries are dropped (`drop_block_entries`, with a check that no kept vanilla location lies under them), a society term follows complexity, harbour values reproduce the vanilla distribution ordered by coast shelter, and the vanilla share of state capitals gets a market village. `verify_development` checks the final texts. `make check`: 134 passed; the five local tests pass.
- [V-EXEC] Corrected vanilla numbers: the American harbour values include 13 negative ones (1,092 values, 758‰ zero, mean 0.101); the donor regex for harbours did not match a minus sign (C73–C74).
- [V-EXEC] First build (continents 3706823338, linear term): states at 0.63–0.73× the vanilla mean. A fixed saturation of 800 fixed it there and failed on archipelago 5 (members 1.55×). The saturation is now fitted per world to the vanilla state mean; all three builds (continents 3706823338, archipelago 5, fresh random continents 515055336) pass every acceptance criterion (C75). Golden digests of `rnw synth` changed only through the version string. The bundle of seed 515055336 stays in `generated/rnw_exp_new_world`; experiment 012 is the next in-game test.

## 2026-10-19 — R7a audit (product version 0.9.3)

- [OWNER] Not satisfied with the weaknesses left by R7a (cities and towns below vanilla, rank correlation near its bound, no byte-identity check, river term left out); audit and fix.
- [V-EXEC] A scratch harness runs the export up to natives and development on cached worlds (about 1 minute instead of 11) and reproduces the full builds exactly.
- [V-EXEC] Findings (C76): rivers are far more common on generated urban and state land than in vanilla, so the estimate without the river term was biased; generated cities and towns stand on poorer land than the rest of generated state land, unlike vanilla. Fixes: the estimate includes `river` × river size (rank of the widest river pixel, [INFERRED]); the saturation is fitted per settlement class; a new invariant keeps Old World development entries identical to vanilla. Rejected: a term from ungated hearth influence (cities worse) and a tribal fit (needs the full term on all reached tribal land and still misses).
- [V-EXEC] The positive-share bound measured the hearth count (3-hearth world: 229‰ of land reached, below the 250‰ bound); replaced by coverage of reached land (≥ 850‰), reported as `coverage_permille`.
- [V-EXEC] Three full builds pass every criterion; cities 12.07–12.29 and towns 6.29–6.40 against vanilla 12.28 and 6.38; two builds of seed 3717486232 are byte-identical. `make check`: 137 passed; local tests pass. Seed 3717486232 stays staged for experiment 012.

## 2026-10-20 — Compact connected hierarchy (product version 0.9.4)

- [V-GAME owner] The 0.9.3 build loads and the world map looks right; areas and regions lie in pieces inside other regions (C77). Experiment 012 is PARTIAL.
- [V-EXEC] Cause (C78): `plan_identities` gave every generated cell the vanilla area under its centre, so vanilla outlines were stamped onto an unrelated geography; new areas joined the vanilla region nearest them. 24 of 252 land areas, 12 of 14 regions and 14 of 35 sea areas were in pieces.
- [V-EXEC] New game-independent `hierarchy.py`: parts grow from sources by Dijkstra over cell contacts (shortest-path trees, so connected); islands without a source join the nearest part whole; additive handicaps balanced with the sources held still, then a Lloyd move (capacity-constrained centroidal partition). A first version that moved sources while balancing oscillated and let one sea area shrink to a single zone on archipelago seed 5; balancing to convergence before each move fixed it.
- [V-EXEC] `eu5_newworld.py` builds land top-down (vanilla subcontinents → vanilla regions sized by vanilla location counts → at least the vanilla number of areas per region → provinces) and matches vanilla keys to the nearest parts; sea zones split into the touched vanilla sea areas, a cut ocean area growing from the generated zones that touch its remainder. A planner check fails the export if any group has two pieces on one landmass or water body.
- [V-EXEC] Full build of seed 3717486232 (0.9.4) passes every invariant; read back from its files, no American group has two pieces on one landmass (vanilla has 15 such groups). `make check`: 144 passed; the five local tests pass.

## 2026-10-20 — Water belongs to the region of its shore (product version 0.9.5)

- [V-GAME owner] On 0.9.4 the region map mode colours the sea by region; the water around an island belonged to a region whose land lay elsewhere (C79).
- [V-EXEC] Cause (C80): sea areas kept their vanilla regions and were placed by vanilla position; 10 of 16 water pieces of land regions did not touch that region's land. In vanilla every piece does.
- [V-EXEC] 0.9.5 builds water top-down like land: shore zones take the region whose land they touch most, every region's water grows from its shore, the coastal share of water is vanilla's, and a region's water is split into its vanilla sea areas plus new ones; the open ocean keeps the ocean areas, cut ones still grow from their remainder. A first version left one- and two-zone sea areas where a region's short shore stretch was enclosed by a neighbour's water; such secondary pieces below 13 zones now join the water around them, as small islands join their nearest part. American sea area keys stay, because exploration triggers, exploration preferences and events reference them. A new check fails the export if a piece of a region's water does not touch that region's land.
- [V-EXEC] Full build of seed 3717486232 (0.9.5) passes every invariant; read back from its files, all 17 water pieces touch their region's land and no American sea area is in pieces. `make check`: 146 passed.

## 2026-10-20 — Roadmap: player experience and publication

- [OWNER] Two phases added to the [roadmap](../roadmap.md): U1, a comfortable setup inside the game (generation settings, visibility modes including a New World hidden by terra incognita already at country selection, seed QoL, ideally without a restart), and P1, preparation of the GitHub repository and the Steam Workshop page.
- [V-LOCAL] Vanilla declares 30 lobby game rules in `main_menu/common/game_rules/` (C81), a lead for in-game options.
- [V-GAME owner] Correction of the first U1 premise, which assumed a new seed needs a game restart: EU5 reloads mods in the main menu without closing the game, map mods included, and builds the world when a new game starts (C82). U1 now requires a reroll that never closes the game; open is whether the reload re-reads a mod rewritten on disk.

## 2026-10-20 — Delivery: a generator application with a window

- [OWNER] The player must not generate in a terminal or keep scripts; control belongs in menus, a restart only if unavoidable, and the game must never look frozen.
- [V-LOCAL]/[V-EXEC] The game cannot compute a geography (C83): no random-map generator in `eu5.exe`, `CMapGenerator` reads the locations PNG, mods are mounted data, and script effects change the start state but not land, sea, relief or climate. The owner's `debug.log` shows playset switching in the running game and a fresh mount of every mod's `in_game` at each new game (21.8 s behind the loading screen).
- [OWNER DECISION] Of a pool of pre-generated worlds, a pool with societies rerolled by script, and a local application with a window, the owner chose the application ([ADR 0004](../adr/0004-generator-application.md)). Roadmap U1, R9, R10 and P1, the architecture, product spec and legal notes follow it.
- [V-EXEC] Experiment 013 (does a new game read a mod rewritten on disk while the game runs?) is prepared: world B, continents seed 34378487 (0.9.5), is built for it.

## 2026-10-20 — Experiment 013 and the 1.4.2 patch

- [V-LOCAL] Steam installed 1.4.2 (build 26043558) at 15:59, after world B was built from 1.4.1 files at 15:41–15:52. The patch changed three map-contract files, about 500 Old World location templates and several files the mod overrides whole (C84); the generator now refuses the build, as intended.
- [V-GAME owner] Experiment 013 (C85): a new game after replacing the mod on disk kept the old map and read the new setup (rung a failed); a playset round trip reloaded the mod in the game, then generating the 1337 game crashed (rung b). The control and a 1.4.2 rebuild are needed before the crash can be attributed.
- [V-GAME owner] Control of experiment 013: after a full restart world B loads and the 1337 game starts; the government-type errors appear there too. The crash belongs to the in-game reload path. ADR 0004 now installs a world only while the game is closed and asks for one restart; a restart-free flow needs a clean reload test on mods built for 1.4.2.

## 2026-10-20 — Regression to 1.4.2 (product version 0.9.6)

- [V-EXEC] The local install tests pass on build 26043558; its map-contract digest joins the known builds (C87). A full build of seed 34378487 on 1.4.2 passes every invariant, and its overrides now match 1.4.2 outside American content (the 1.4.1 build differed in 497 Old World templates and more). The same seed gives a slightly different world on another patch; ADR 0003 now says so, and a shared seed must carry the game build.
- [V-EXEC] Correction: the `invalid government type` lines are not a 1.4.2 regression. They name exactly the 544 vanilla American tags the mod removes and appear in 1.4.1 sessions with RNW too (C86); with a localization hash collision of `rnw_loc_05454`, they are open defects of the generator.
- [V-GAME owner] Clean rerun of experiment 013 on 1.4.2 builds (C88): with world A′ installed while RNW was inactive, switching RNW on again loaded A′ in a new game, without a restart and without a crash. The first activation after the install still logged the old mod name. ADR 0004 now uses the reload flow: the application writes only while RNW is not the active playset.

## 2026-10-20 — Removed tags and localization hashes (product version 0.9.7)

- [V-LOCAL]/[V-EXEC] Vanilla defines a tag only together with its 1337 setup entry, and the engine creates every defined tag as a country; the 544 removed American tags kept their definitions and logged `invalid government type` (C86). The export now rewrites the American definition files without them and fails unless defined tags and setup entries disagree only as in vanilla (`DUMMY`, `MER`, `PIR`). References to removed tags stay, as vanilla references formable tags without a definition (C89).
- [V-EXEC] The engine's localization key hash is MurmurHash3 x86_32, seed 0 (C89). The new game-independent `rnw.loc_keys` claims every generated key (locations, provinces, areas, tags and adjectives) against the 316,231 keys of the installation and skips a taken serial or tag; `verify_localization` checks the written files. The 0.9.6 keys held three collisions that the owner's session logged exactly; 0.9.7 has none (C90). `make check`: 163 passed; local tests pass. Experiment 014 checks both in game.
- [V-GAME owner] Experiment 014 on 0.9.7 (C91): no localization collisions and no removed vanilla tag in the error log; 15 generated states with an open republic template still log `invalid government type`. 0.9.8 completes open templates from their vanilla users (`template_governments`, following template includes) and fails on a template no vanilla country completes.
- [V-EXEC] A profiled full build (cProfile, seed 319218363) runs to find where the 11 minutes go (R10).
- [V-EXEC] Profile (C92): of about 11 minutes, terrain decals take a third (material slot noise most), the generated geometry a sixth, and decoding the same vanilla decals with a pure-Python LZAV decoder a fifth; everything runs on one core. R10 now orders the work: per-build cache of vanilla inputs, parallel decals, then a native core for noise, distances and LZAV where they still dominate.
- [V-GAME owner] Rewriting the mod while RNW is active and applying the same playset once loads the new world without a restart (C93); ADR 0004 simplifies the reload flow to that.
- [V-LOCAL] The session's error log against the vanilla baseline (C94) lists further generator defects. 0.9.9 fixes the largest one: generated countries now write the government fields their template's vanilla users write (66 monarchies had a tribal heir selection). The rest are queued.

## 2026-10-20 — The defect batch of C95 (product version 0.9.10)

- [V-GAME owner] The vanilla 1.4.2 baseline log now exists (Default playset, a new 1337 game): 736 normalised categories. Against it, the 0.9.8 world's log has 746 lines of its own (C95).
- [V-EXEC] Causes: the engine cap of 2^24 map objects (the world held 19.5 million instances, vanilla 15.9 million; the incomplete locators are its consequence), 53 dynamic historical events of removed tags, vassal pairs without ranks, DLC city graphics and list keys the remap did not read, a volcano object naming a removed location, 3 unported land cells, a colour clash with a vanilla country, base values only removed locations used, cultures and religions without pops and villages in city or town capitals.
- [V-EXEC] 0.9.10 fixes all of them in the generator (C96): an instance budget, event retirement, ranks, a DLC-aware remap, `seal_pockets`, unique colours, a diaspora of small pops, village rules and base value cleanup. Two more defects found on the way: generated templates copied a donor's base value (Potosi's silver) and trimmed ocean zones got locators vanilla does not have. Seed 319218363 rebuilt (12 minutes) and verified offline.
- [UNKNOWN] `Locator transform overrides modified` for `city` and `vfx` is not explained; the override file is no longer shipped when unchanged. Experiment 015 checks the log in game.
- [V-GAME owner] Experiment 015, first run: the 0.9.10 world loaded with only 5 lines the vanilla baseline lacks (none of the C95 categories), then the game crashed a few seconds after the start (C97), at the same address and with the same registers as the crash of 14:44 (world B′). Both followed a vanilla game that had run in the same process before the switch to RNW.
- [V-EXEC] 0.9.11: events that only dropped events fired (chains) go too; generated country names avoid vanilla country names.
- [V-GAME owner] Experiment 015, second run: with RNW active at the launch and no game before, the 0.9.10 world starts and runs without a crash (C98). The crash of C97 is therefore a matter of order: a vanilla game, then RNW activated from inside the running game.
- [V-GAME owner] That session's log still has 9 invalid vassals: ranks are not the reason (C99). All invalid pairs have an overlord whose template sets no starting technology level (0 of 18 valid against 23 of 23 for level 2 in two worlds). 0.9.12 takes overlords only from templates at vanilla's lowest lord level and drops the explicit ranks.
- [V-GAME owner] Experiment 015, third run: 0.9.12 on a fresh launch runs without a crash and without invalid vassals (C100). The remaining lines are the two locator hints, 39 unused modifiers of dropped events (retired in 0.9.13) and 3 never-set variables read by kept scripts.

## 2026-10-20 — The Rust core (ADR 0005, roadmap R10)

- [V-EXEC] ADR 0005 chooses a hybrid: Python generator and readers, Rust (PyO3 and rayon, built by maturin) for the hot integer kernels, NumPy versions kept as the references in `tests/reference/`. Kernels moved so far: LZAV decode and encode, value and fractal noise, step and Euclidean distance fields, label spreading and connected components, bilinear upsampling, block means and box blurs, the vegetation pixel keys and sampling, the priority-flood drainage, the best pixel per label, the material slot synthesis and the layer packer; the terrain decals run on threads.
- [V-EXEC] A full export fell from 11 min 55 s to 2 min 31 s with identical output (C101). `make check` now builds the extension and runs `cargo fmt`, `clippy` and `cargo test`.
- [V-EXEC] Memory is the next limit: the build peaks at 38 GB and spends a third of its CPU time in the kernel on page faults. The remaining stages are the generated world (31 s), identities, biomes and rivers, water and the text rewriting.
- [V-EXEC] Later in the same session: the text rewriting and the raster stages run on two threads, the decal heights and the water textures are native or overlapped, and a build takes 2 min 3 s (peak 21 GB) with all 733 files unchanged (C101). Threads for Python and NumPy stages gave no gain because of the interpreter lock; the front half (world generation, identities, biomes, natives, about 75 s) is the next target and needs more kernels.

## 2026-10-21 — Memory of the export (ADR 0006, roadmap R10)

- [SOURCE] EU5's Steam page asks for 16 GB of RAM at the minimum and recommends 32 GB; the owner asked that the mod cause no problems for any player, that its kernels adapt to the machine and that its memory suit EU5, not a calculator.
- [V-EXEC] The 21.8 GiB peak of the Rust export (C101) came from whole-map eight-byte arrays in every stage, decal windows of 2.7-7.7 GiB each (eight at once), output files held until the bundle was written, a decoded copy of all vanilla decals and one malloc arena per thread. Measured per function with `/proc/self/status` after a reset of the high-water mark, then by sampling the live process.
- [V-EXEC] Decals now run in bands with a halo, the water, vegetation, relief, rivers, climate and world statistics in strips, the big files go to a spool, `interior_points` is one native kernel, and glibc is limited to two arenas. Peak 6.9 GiB (6.3 GiB with one thread, 3 min 48 s), 733 hashes unchanged in all runs, also with `RNW_MEMORY=2500 RNW_THREADS=2` (C102).
- [V-EXEC] The machine is read at each run (`rnw.parallel`: cores with affinity and container quota, `MemAvailable`, cgroup headroom, Windows `GlobalMemoryStatusEx`); the export refuses to start below 7 GiB free and says so; `--ignore-memory` starts anyway.
- [UNKNOWN] The Windows and macOS memory paths are untested here; a leftover spool or staging directory of a killed run blocks the next run until `--replace` clears it.
- [V-EXEC] Speed, same day (C103): a lookup table instead of a binary search in the slot kernel, band kernels that evaluate noise and rules only on the band's core, and an export built from overlapping stages (`parallel.Stages`, one worker below four threads or 10 GiB free) in which everything that reads only the vanilla game runs beside the world generation. 124 -> 94 s; six threads give 96 s, three threads 137 s, one thread 192 s, always with the 733 hashes of the Python build. The next limit is the interpreter lock held by the text half's pure-Python parser while the decals wait.

## 2026-10-21 — Progress, cancel and Windows readiness (roadmap R9, U1)

- [V-EXEC] `rnw.progress` announces every stage of the export (22 weighted stages and 4 parts) to a listener and carries the cancel flag; long loops call `checkpoint()`. A cancel at 20-66 s of a real export raised `Cancelled` within 0.2-3.2 s and left no spool, staging or half-written output (the earlier bundle stays); `rnw newworld --progress` prints the stages.
- [V-EXEC] The Rust crate passes `cargo check` and `clippy -D warnings` for `x86_64-pc-windows-gnu`; the Windows memory path (`GlobalMemoryStatusEx`) is covered by a test with a fake kernel, the structure layout by a size and offset test, and busy files are retried on Windows only (`when_free`). CI runs Linux and Windows but has not been run: nothing is pushed [UNKNOWN].
- [V-EXEC] The application window exists (ADR 0007, C105): Qt (PySide6) over a toolkit-free controller, game and profile discovery, world codes, history, install and uninstall of `rnw_exp_*` mods only, progress per stage and cancel. `rnw gui` / `rnw-gui` open it, `rnw world CODE` makes the same world headless, `packaging/build.py` freezes it with PyInstaller (246 MB on Linux) and `--self-test` checks the folder. The CI workflow gained a packaging job for Linux and Windows that has not run [UNKNOWN].
- [OWNER 2026-10-21] After the window was built: the mod should be inside the game; a separate generator program is hardly a normal solution. ADR 0004 had been chosen by the owner on 2026-10-20 (a question with three delivery models; the answer was the generator with a window, the question having said that it lives outside the game). Work on the window stopped and ADR 0007 is on hold until the delivery model is decided again.
- [OWNER 2026-10-21] Asked how a mod that is not inside the game could be published on the Workshop. A Workshop item is a data folder the game mounts and never runs; I found no Paradox rule that bans executables, but nothing starts one from the game. [ADR 0008](../adr/0008-workshop-worlds.md) replaces ADR 0004: worlds are Workshop mods (a base mod with game rules plus one mod per world), the generator is our factory.
- [V-LOCAL] Engine facts found for the in-game design (2026-10-21, files and `eu5.exe`): mods can add windows through scripted widgets; the game's mod manager has an Open in folder button for every mod (`LocalMod.OpenInFolder`); the script effect `debug_log` writes a string to the debug log; no plugin or native-mod hook was found by static search (imports, strings; dynamic loading not excluded). [ADR 0009](../adr/0009-hub-mod-with-generator.md) proposes one Workshop mod that carries the generator, explains it in the game and is opened from the mod list.


## 2026-10-21 — The generator under Proton (ADR 0009, experiment 019)

- [V-GAME owner] Open in folder in the game's Mods window opens Wine's own explorer at the mod's folder. A Linux player therefore stands inside the game's Wine prefix, and the program to start there is the Windows build.
- [V-EXEC] The Windows build under the game's Proton (11.0, a community build), in a prefix made by `proton run`: the window's self-test passes, and from a Workshop item folder (`S:\` or `Z:\`) it finds the game and the profile (C106). An earlier `DLL load failed` for QtWidgets came from a test prefix made without the `proton` script (no ICU 68, no DXVK `d3d11.dll`), not from Proton.
- [V-EXEC] Discovery fix: Proton's Steam stub writes `"LibraryFolders"`; the KeyValues reader folds keys to lower case. Discovery also walks up from the program's own folder to the Steam library (`game_beside`), which a program inside a prefix needs.
- [UNKNOWN] Experiment 019, part 3 (owner): start the program from that explorer while the game runs.
- [V-GAME owner] Experiment 019, part 3: a Windows probe in `rnw_exp_new_world/generator/`, without the executable bit, starts from the running game's Open in folder, shows its window and runs in the game's prefix with everything the generator needs in sight (C107). It inherits an affinity of 16 of 32 processors. The game ignores the folder: no new error line.
- [OWNER 2026-10-21] Asked how safety can be shown and whether Windows antivirus will complain. [SOURCE] SmartScreen needs the Mark of the Web (Steam reportedly writes none); Smart App Control blocks unsigned unknown programs anyway; PyInstaller's stock bootloader is a known false-positive source. [V-EXEC] In our Windows layout Python is signed by the PSF and Qt by The Qt Company; NumPy, Pillow and `_native.pyd` are not (C108). ADR 0009 now ships the embeddable Python with a small launcher, signs our two binaries (SignPath Foundation or Azure Artifact Signing, the owner's decision) and keeps the behaviour provable: no network, no admin, writes only to `mod/rnw_*`.
- [OWNER 2026-10-21] Asked whether a DLL mod is allowed and would give real generation inside the game. [SOURCE] Paradox's agreement counts "scripts and programs" as UGC and forbids hacks; [V-LOCAL] no confirmed official code-mod interface, and static analysis found no path that loads code from a mod (dynamic loading not excluded, correction relayed by the owner), so the known way for a DLL is a proxy file in the game folder (as Anvil for EU4), which the Workshop cannot install (C109). Rejected in ADR 0009: it would run the same generator inside the game, break with every patch and look like a cheat to antivirus. The nearest thing inside the rules: the generator started once, answering an in-game Generate button through `debug_log` (experiment 017).

## 2026-10-21 — Final delivery scheme and licence (ADR 0009 accepted)

- [OWNER 2026-10-21] Asked for a final brainstorm and the final scheme for the most convenience, legal and safe, with an honest Workshop description, and for the licence best for the owner's interests. ADR 0009 is accepted: one Workshop item with the data mod, a launcher at the top of its folder and the generator's runtime; Open in folder, Generate, tick the generated world once, apply the playset. Ten options are weighed in the ADR (code host, world pool, DLL, script, WebAssembly, a Steam app, writing into the Workshop folder, editing the playset, an in-game Generate button as phase 2). The Workshop text is drafted in `docs/workshop-description.md`.
- [OWNER relay] A second opinion corrected the DLL finding: imports and strings do not exclude dynamic loading, so the claim is "no confirmed official interface; no static path found" (ADR 0009, C109). The decision against a DLL stands on the other grounds.
- Licence: first GPL-3.0-only; the same day MPL-2.0 after the owner relayed a second opinion and the aim that Paradox might one day take the mechanism into the game. MPL keeps our files open and lets them into a larger closed work, is OSI-approved for SignPath and fits every dependency (C110). `LICENSE` is Mozilla's text (byte-identical to an independent copy); `pyproject.toml` and `native/Cargo.toml` say `MPL-2.0`.

## 2026-10-21 — The hub build and its first checks (experiment 021)

- [OWNER 2026-10-21] Approved `rnw_exp_hub` as a second test mod and asked to start the tests.
- [V-EXEC] `packaging/hub.py` builds the hub: embeddable Python, locked Windows wheels with Qt cut down, our own maturin wheel for Windows and a MinGW launcher with manifest and version resource (C111). A first build copied our sources without package metadata; the launcher showed the resulting traceback on the owner's desktop, because my Wine test drew its dialog there. Since then the scratch prefix uses Wine's null graphics driver, checked by a load trace.
- [V-EXEC] Offline under Proton: the launcher's self-test passes with the real Windows Qt plugin, and the hub's Python generates the 733 reference files in 2 min 33 s.
- [V-GAME owner] Experiment 021, first run: the generator ran from the game, found game and profile and generated the reference world (733 of 733 equal, installed files equal). Installing failed on deleting the old world, whose decal height file the game held (Wine semantics); the new world was in place nevertheless (C112).
- [V-EXEC] Fixes: retire-then-sweep install with a wait and an instruction if even the rename is refused; Windows affinity read with `GetProcessAffinityMask` (31 threads had been 16). Both checked under Wine; the hub is rebuilt.
- [V-GAME owner] Experiment 021, second run: the rebuilt generator made and installed a new world while the game held the old one (15 threads, 187 s, installed). The new game after the reload crashed at the address of C97 with different registers (C113). The ADR and the Workshop text now say to restart EU5 after generating; the open question is whether the reload itself or the world changes the outcome. (A first reading that eight other mods were in the playset was wrong: the owner's RNW playset enables only RNW; the log mounts installed mods' folders whether enabled or not.)
- [V-GAME owner] Experiment 021, third run: world B plays on a fresh launch; vanilla game → switch back to RNW → new game crashes with the registers of C97 byte for byte (C114). Re-applying the same playset does not reload the mods fully (no loading-screen transition). The generator's last instruction now says to restart EU5.
- [V-GAME owner] Experiment 021, fourth run: generated before the session's first game, a world starts after a switch of playsets without restarting EU5 (C115). The generator now reads the session from `debug.log` and the active playset from `playsets.json` (read only) and tells the player whether to switch playsets, to tick the world, or to restart EU5.

## 2026-10-21 — Worlds as mods of their own, world types, playable settings (0.9.14)

- [OWNER 2026-10-21] The generator's window must let the player see and manage earlier worlds, show a preview only on request (terra incognita by default), keep every world as a mod of its own, offer world types and settings, keep worlds playable, check that resources fit the New World and its locations, let states be more than three clusters, and present the generator as a factory of complete, shareable map mods that need no generator to play; the avatar is the item's picture and a world's picture is its (covered) preview.
- [V-EXEC] The library (`rnw/app/library.py`) keeps each world's code, pictures and report; every generation is a new mod `rnw_exp_world_<id>` (same code and build, same world); the export writes a covered preview and the mod-list picture covered by default (`rnw/pictures.py`); the window lists worlds, shows them covered until asked, and adds, removes, renames, deletes and copies.
- [V-EXEC] World types measured on three seeds (C116); twenty settings with playable ranges from edge exports and a location estimate (C118); world codes with changes in a compact format 2.
- [V-EXEC] Two generator defects found and fixed: raw materials came from the Old World (C119), and state land formed one block per hearth (C117).
- [V-EXEC] 735 of 735 files equal on Linux and under Proton (C120).
- [V-EXEC] Timed exports of 0.9.14 (94.2 s, 92.3 s): the vanilla-only stages all finish under the world generation, so a per-build cache of vanilla inputs saves nothing on six or more threads and at most about 45 s of 137-192 s on fewer (C121). R10's cache item is dropped.
- [OWNER] 2026-10-21: finish the mod's settings inside the game, with the New World hidden by the game's terra incognita already at country selection (every lens, countries on it included, no start on it; optional, on by default, switched on the new-game screen); and move the common generator settings out of Customize, after EU4's random New World.
- [SOURCE] EU4's options for its random New World: *Terra incognita in lobby* and *Fantasy Random New World* (never, seldom, sometimes, often), scenarios on or off (C122). The EU4 wiki refused automated requests, so only search summaries were read.
- [V-LOCAL] The new-game screen is the lobby; its Game Rules tab lists every rule of `common/game_rules` (C123). No handle for covering the New World in the lobby was found; which country's knowledge the lobby map shows is unknown (C124). Experiment 022 (a probe rule and two log lines, NOT-RUN) asks the game; no rule that would do nothing is shipped meanwhile.
- [V-EXEC] Generator 0.9.15: great empires (`natives.empire_permille`, default Seldom; chance 0 leaves 0.9.14's bytes: C125) and *World basics* in the window, five questions over the controls (C126); world codes carry the new field (format 2, field 26). Golden digests of the synthetic bundle renewed for the new version and settings. 584 tests pass; `ruff` and `basedpyright` are clean; a continents export of seed 42 with always-empires passes every invariant.
- [OWNER] 2026-10-21 (with a screenshot of TI in a campaign): the New World is not hidden at selection at all; the engine draws the map the same way in the lobby and in the game, with no loading screen between, so the same TI must be applicable at selection.
- [V-LOCAL] Agreed, and read why: TI is the engine's own, computed from a **viewing country** (the local player's, or a forced observed one); with none, the known-locations map is all ones, so everything shows (C127). Selection has no player country yet. A viewer in the lobby is what is missing, not a tool.
- [V-LOCAL] A data-driven filter system for lists (C128) lets a mod add a default-on filter that reads a game rule; a candidate for hiding New World countries from the lobby's list without overriding a vanilla file. Experiment 022's probe carries one (4 → 5 files); the owner reinstalls it with `--replace`.
- [OWNER] 2026-10-21: the probe's rule is listed (bottom of General) and TI covers nothing at selection; the approach was too indirect: hiding the New World at selection is a plain modification (visual cover with the game's TI texture, no clicks into it), and adequate changes to game files are what the project is for. AGENTS.md and memory now say what a "crutch" is and is not. Also noted: achievements show as Available with the mod enabled (C130).
- [V-GAME] Experiment 022 first part: rule listed, `debug_log` works, `on_game_start` runs before the lobby, `on_game_started_after_lobby` after it with the rule as chosen (C129).
- [OWNER] 2026-10-21: achievements stay as they are; the game should itself say which mods are compatible. [V-LOCAL] Checked: it does, by its listed conditions (C130), and a content mod is not among them, so Available is the game's own verdict for any such mod. No rule of ours blocks achievements; the earlier suggestion to add `blocks_achievements` is withdrawn.
- [OWNER] 2026-10-21: the Hidden filter did nothing, the selection screen worked as before (C129). The filter route is closed; selection in the lobby is GUI (list item, context menu entry *Select*), so blocking it is a small change of GUI files, made from the installed game at generation time (AGENTS.md).
- [OWNER] 2026-10-21: hiding the New World at selection is a QoL feature, not a prohibition: no guarantee needed, and a service location must not add a location or a country.
- [V-EXEC] Generator 0.9.16: the world mod carries the rule `rnw_new_world_rule` and the changed game files of C131, with no new location (the sample points are existing locations). Tests on synthetic layouts; the two game files take the edit at one place each; a full export of the owner's world type and seed passes every invariant. [UNKNOWN] in game: experiment 023.
- [V-GAME] Experiment 023, first run (owner, 2026-10-21): nothing changed; the New World stays open and the rule does nothing. The logs say why: EU5 1.4.2 refuses `defines` in a rule's setting (`Unexpected token: defines`), so the shader's switch never moved, and the GUI condition of *Select* did not convert. A New World country chosen in the lobby leaves the map open: the lobby's country is not TI's viewer (C132).
- [INFERRED] A rule's setting reaches the interface (flags) and characters (modifiers), not a shader; no other way from the new-game screen to the map's shaders was found (C132). [OWNER] 2026-10-21: the choice moves into the generator, a box on by default; then the box for the mod-list pictures and the preview's Show button go too, and one setting, whether the New World is shown before it is played, decides everything.
- [V-EXEC] Generator 0.9.17 (C133): `Preferences.show_new_world` (off by default) decides the window's pictures, the mod-list picture and the cover at selection; the export keeps a copy of the cover's 14 files beside each mod and the library takes them out or puts them back, for every world, without making it again. No game rule; the shader covers whenever the sample locations are all known; *Select* asks a scripted GUI of the mod for the capital's continent; the filter reads no rule. `make check`: 594 tests pass, 6 skipped; `ruff`, `basedpyright`, `cargo fmt`, `clippy` and `cargo test` clean. Golden digests renewed for the new version. The owner's world exports with every invariant (746 files). [UNKNOWN] in game: experiment 023, second run.
- [V-GAME] Experiment 023, run 2: a first attempt is void (EU5 started at 19:19:15, the install replaced the mod at 19:19:26 and the game listed the old files); the clean launch at 19:23 with 0.9.17 covered nothing and kept New World countries in the list (C134).
- [V-LOCAL] The cover was compiled (shader cache), but only the TI overlay and the borders include the TI include, and the TI overlay is not drawn at country selection; so a cover there has to be drawn by the layers drawn there. The lobby list ignores mod filters (C134). [OWNER] 2026-10-21: one probe launch first.
- [V-EXEC] Experiment 024 prepared: `experiments/024-terrain-cover-probe/build.py` (deleted 2026-10-22) builds `rnw_exp_probe_cover` locally (the terrain shader tinted over the world's cover grid by what the TI texture reports for the sample locations and the pixel's own location). `ruff` clean on `experiments/` (INP001 ignored there, as in `packaging/`).
- [V-GAME] Experiment 024 (owner, 2026-10-21 21:46-21:53): the probe's tint is cyan at selection and in the campaign, over a blocky region that is not the New World (C135).
- [V-EXEC] The region is the world's cover grid flipped north-south (IoU 0.959 against at most 0.41 as built, `experiments/024-terrain-cover-probe/fit.py`, deleted 2026-10-22): world z grows northwards, image rows southwards, so 0.9.16-0.9.17 covered the mirror image and sampled mirrored locations. Measured on the screenshots, the terrain reads Portugal's known Iberia as known in the campaign and the same locations as unknown at selection: the terrain reads TI, and at selection everything is unknown, not known (C127 corrected).
- [OWNER] 2026-10-21: the next build covers the four layers seen in the screenshots (terrain in 3D and flat, water, borders, names); trees, rivers and towns follow if they show through.
- [V-EXEC] Generator 0.9.18 (C136): the cover is drawn by the terrain (3D and flat), the water, the borders and the map names, with the vanilla rule *cover where unknown* inside the New World, from two includes of the mod, a mask texture (generated locations plus the 13 ocean wastelands that border them in the owner's world) and the game's TI texture; the TI include, sample points, grid and lobby filter are gone. Anchors checked on the installed 1.4.2; a full export of the owner's world passes every invariant and its mask lies on the New World. The probe of experiment 024 must be unticked before the test: it would replace the world's terrain shader. Experiment 023, run 3, is prepared.
- [V-GAME owner] Experiment 023, run 3 (0.9.18): EU5 crashed as the map was first drawn, twice (C137).
- [V-LOCAL] The shader cache holds the map-name shader as source without a binary, and the source reads the mask's texture without declaring it: the game drops a sampler that names neither a `Ref` nor an `Index`, and every vanilla sampler with a `File` has one. [V-EXEC] Generator 0.9.19 keeps the grid as a constant array in one include (32-pixel cells, smoothed) and paints the colour without the drawings; a test now compiles the include's HLSL with `glslangValidator`, declaring only the samplers the game would, and fails on 0.9.18's sampler. The full export of the owner's world passes every invariant and its include compiles. Run 4 is prepared.
- [V-GAME owner] Experiment 023, run 4 (0.9.19): the same crash; no crash report (C138).
- [V-LOCAL] The map-name shader compiled; terrain, water and borders were never compiled, in 0.9.18 and 0.9.19 alike. Each of them already had a sampler of a slot the include declared again; the map-name shader had none. [INFERRED] a slot named twice stops a shader before it compiles and the game crashes when it draws with it. [V-EXEC] A check over the installed game's includes finds exactly those three. Generator 0.9.20 passes the shaders' own samplers to the cover and adds one of the mod's only where a slot is missing; the export runs the check. Run 5 is prepared, with Proton's log on.
- [V-GAME owner] Experiment 023, run 5 (0.9.20): no crash; the New World is covered at country selection (political lens) and under the game's own terra incognita in the campaign. Every compiled variant of the four shaders has its binary (C139), which supports C138: the slot named twice was the crash. The cover is the right hue but about 1.7 times brighter than vanilla terra incognita and has no drawings. Not yet seen: the 3D map close up, choosing a covered country by click or *Random Country*.

## 2026-10-22 — Cleaning up after the cover (experiments 022-024)

- [V-LOCAL] The owner's profile still held `rnw_exp_probe_lobby`, enabled in the RNW playset: its game rule `RNW probe: New World` is listed on the lobby's Game Rules tab and changes nothing (C129), and its hooks still write two lines to `debug.log`. The playset also named `rnw_exp_probe_cover`, whose folder is gone. Neither is the product's: the generated world and the hub define no game rule (checked over `src/` and `packaging/`).
- [V-EXEC] Deleted from the repository: the probe mod of experiment 022 and its test, the builder and the fit of experiment 024 (their READMEs keep what they did). Deleted from `generated/`: the staged probes of experiments 001, 019 and 024. Also gone, unused since the first commits: `fields.coarse_noise`, `fields.resample_nearest`, `eu5_nw_export.LOCALIZATION_DIR`, and the `experiments/**` ruff ignore, now that no script is left there. No generated file changes: version and digests stay at 0.9.20.
- [OWNER to do] With the game closed: `rnw uninstall-mod rnw_exp_probe_lobby`, and drop `rnw_exp_probe_lobby` and `rnw_exp_probe_cover` from the RNW playset in the launcher.

## 2026-10-22 — The generator beyond its first window (ADR 0010, proposed)

- [OWNER] Five requirements: regenerate only a part of a world (states, resources); several pictures, with countries and what else matters for judging a map; load by hand a generation made elsewhere; the generator as a program of its own, not only a Workshop mod; shorter, more convenient mod names; and the quality of life that follows.
- [V-LOCAL] Read before designing: every stage draws from `derive_seed(seed, stream)`, the raw materials (`eu5_biomes._raw_materials`) and the peoples (`eu5_natives.build_natives`, with the place names) take the seed as an argument, and no stage after the land reads `raw_material` but the texts that write it; so a part can have a seed of its own [INFERRED]. A world mod is 1.2 GB, 1.1 GB of it `in_game/gfx` (the owner's profile, 0.9.20): variants are heavy and should replace by default. The game's list shows a name of about 80 characters with a 19-digit seed; the player's rename never reaches it.
- Decided in the ADR for the owner to confirm: layers by rolls appended to the world code (old codes unchanged), pictures per layer with an atlas, small `.rnworld` files without a built mod (moving a built mod is a function of its own, owner), one program with two doors, names `RNW · <name>`. Five open questions, the first being what "a generation from elsewhere" means. Nothing built; no output changed.
- [OWNER] Two more requirements, 2026-10-22: reproducibility beyond the seed (versions of the generator and the world format, EU5 compatibility and every parameter, since algorithms and game data change; a hash proves integrity, not reproducibility), and a strict line between what works without EU5 (viewing a finished atlas) and what needs it (generation), with no protected game file in a public release.
- [V-EXEC] Read before writing section G of the ADR: the `report.json` of a 0.9.20 export holds the resolved settings, the RNG version, the build fingerprint and 15 hashed map files, but the code names a product version, not an epoch; the export also reads the setup, definitions, localization keys, templates, decals, water files and scripts, which no manifest lists; worlds are keyed by the Steam build id. Decided: a reproducibility record with an algorithm epoch, an inputs manifest of every file read, a checked output digest and four verdicts on opening (phase G0); and three kinds of data (ours, keys, derived from the game) with the viewer free of the game and generation tied to it, enforced by an import-graph test and a release allowlist. The owner's distribution table is in section D. Nothing built yet but the names (G1a, in progress).
- [V-EXEC] Generator 0.9.21 (G1a, C140): `rnw.worldname` builds the one name (`RNW: <Type> <TAG>`, 30 characters at most, the player's name replacing the type and tag), `rnw.tagfont` and `pictures.tagged` draw the tag in red in the middle of a covered mod-list picture (none on a revealed one), `library.retitle` writes a rename into the mod's metadata (kept or in the game; if the file is held, the name is saved and the player told), and the export takes the title and the tag from the service. A full export of seed 42 passes. Owner's check in game: the title in the mod list, the tag on the picture. Next: G0 (the reproducibility record), then G1b.

## 2026-10-22 — The reproducibility record (G0, 0.9.22, C141)

- [V-EXEC] `rnw.epoch` (the algorithm epoch, from 0.9.20), `rnw.record` (the record, five verdicts), `rnw.inputs` (every game file the export opens, noted by the interpreter's audit hook and hashed afterwards). `run_spec` carries the epoch, not the release, so the synthetic goldens are keyed by epoch. The service stores the record in `world.json`; `service.check` compares the epoch, then the game's files with the manifest, then rebuilds from the record's own settings in a scratch folder and compares every file of the mod but `.metadata`; the window has a *Check* button and a line on the world page, the command line `rnw verify-world`. `world-code` prints the epoch; a code from another epoch is told apart from one of the same epoch with another release.
- [V-EXEC] The export reads 13,870 files of the game, not the 15 its report listed. The owner's installed 0.9.20 world and the same code made again by 0.9.21 and 0.9.22 are identical in all 739 files but `.metadata`; the reference world (`tests/golden_world.json`) records the digest. `rnw verify-world` on a world of the library: identical in 101 s.
- Next: G1b (stand-alone first run, destinations, viewer mode, boundaries), then G2 (layers and rerolls); G0b (a patch that touched nothing a world read keeps its mod) when wanted.

## 2026-10-22 — Resume Claude ae82fdd4; application phases through G4 and artifact builds (0.9.23)

- [OWNER] Continued the final instruction of the recovered session: complete ADR 0010 offline and leave the game acceptance to the owner. No EU5 launch, normal-profile modification, commit, push or publication was performed in this continuation.
- [V-EXEC C143] Recovered the unfinished tree, fixed the interrupted public land-stage import and its obsolete type-ignore, and completed Candidates, the queue, destinations, notes/favourites/tags, copy actions and undo. Existing layers, atlas, exchange, quick settings, logging, diagnostics and viewer boundaries are integrated. A transferred revealed mod now retains the cover's source files so the global setting can hide it again. Input manifests also record scanned directories; manifests without them keep C141's limitation.
- [V-EXEC C144] The land cache uses bounded strip hashing and raw typed arrays with checksums, no executable serialization. Cold and warm full exports of the epoch-1 reference took 132.313 s and 104.997 s and match every one of its 739 non-metadata files. Epoch 1 and its goldens therefore stay unchanged. The product version is 0.9.23. The installed Steam manifest still says build 26043558; seven read-only local-install tests pass, with the separately gated reference test skipped (the two full exports supply that evidence here).
- [V-EXEC C145] Built the Linux folder and tarball, Windows standalone ZIP and Workshop/Proton ZIP, and a source distribution. The Linux app and Windows runtime under Wine pass the built-app self-test and CLI world-code command. Archive checks found no game assets. Added a tag-checked artifact workflow for Linux, macOS, Windows and the Workshop layout, without any publishing step. Runtime notices and available licence files accompany the packages; public distribution still requires the legal/signing gates. Native Windows, macOS and the remote workflow are not claimed tested.
- [V-EXEC C146] Captured 68 offscreen desktop frames: 17 states, two sizes, two palettes. Fixed the main window's forced expansion beyond 1080×760 and illegible secondary text on theme changes. Overview scrolling and smaller action grids keep controls reachable; a regression test enforces both supported sizes.
- [V-EXEC] Python suite: 795 passed, 8 skipped; lint and type checking pass. Raw evidence, generated worlds, package builds and the isolated Wine prefix remain under ignored local paths. Usage is documented in [generator guide](../generator-guide.md). The owner can check the complete interface and generated worlds together; no claim of new in-game validation is made.

## 2026-10-22 — Owner's UI corrections (0.9.24)

- [V-EXEC C147] The supplied screenshots exposed a gap in C146: synthetic palettes did not
  catch the compressed Settings dialog or the installed dark theme's disabled-button contrast.
  An isolated reproduction measured 12px controls against 25px size hints; changing only
  the forced zero-height resize restores the hinted height. A regression with long paths
  fails before the fix. The Settings dialog now uses natural height and bounded selectors.
- [V-EXEC C147] New-world controls are grouped by task, progress details are optional and
  idle progress is hidden. Ready-world actions are grouped on Versions & files. The
  preview visibility checkbox is on the main World tab for both new and existing worlds.
- [V-EXEC C147] Visibility persists independently for each world and updates existing mod
  presentation from the stored cover and preview, with no generation call. Missing sources
  fail explicitly. Legacy worlds inherit the old global preference once; the future-world
  default then leaves them untouched. CLI, reroll, add and undo use the saved world choice.
- [V-LOCAL/V-EXEC C147] The installed ImperialGeassNoir palette and Breeze style are available
  to Qt through the system plugin path. The app keeps active colours and native rendering,
  adds font-derived control heights and derives readable disabled text from the palette.
  No game, desktop theme or normal profile files were changed; no EU5 launch was performed.
- [V-EXEC] The algorithm and epoch-1 reference are unchanged; the release increment updates
  application code and metadata, not the default geography or cover generation.
- [V-EXEC C147] Final verification: 811 Python tests passed, 8 optional tests skipped;
  23 Rust tests passed; lint, format and strict type checks are clean. Captured 135
  frames with zero undersized visible buttons across Breeze dark, Fusion dark and
  Fusion light, both supported sizes and a 125% font. The Linux 0.9.24 package passes
  the game-asset guard, self-test and CLI help. The self-test now uses an isolated
  temporary library: the new migration had exposed a write side effect, caught by the
  sandbox before writing player data and locked by a failing-first regression.
  Native Windows/macOS and live Wayland interaction are not claimed re-tested.

## 2026-10-22 — Commit the verified development checkpoint

- [OWNER] Commit each completed, verified phase before reporting completion; no separate
  request is needed. The standing rule is explicit in `AGENTS.md`.
- [V-EXEC] `d390810` records release packaging and CI; its exact index snapshot passes
  the three release tests. `237fa7f` records the integrated generator 0.9.24 and its tests;
  its exact index snapshot passes 811 Python tests with 8 optional skips.
- [V-EXEC] `uv sync --locked --group dev && make check` passes: formatting, lint,
  strict types, 811 Python tests (8 skips), and 23 Rust tests. Local agent verification
  transcripts under `.omo/evidence/` are ignored, alongside existing generated/local data.
  The documentation checkpoint follows separately. No push or publication was performed.

## 2026-10-22 — 1.4.3 offline regression (0.9.25)

- [OWNER] Reported patch 1.4.3 and approved a full isolated generation, without EU5 launch.
- [V-LOCAL/V-EXEC C148] Installed beta build 26105915; only location templates changed in
  the ten-file map contract. The full C144 input comparison finds 977 changed files and
  16 changed inputs that the old world mod overrides. Old worlds should be regenerated
  [INFERRED]; no existing world or profile was changed.
- [V-EXEC C149] Register the exact fingerprint, release 0.9.25, retain epoch 1: no algorithm
  changes. The real application CLI makes the reference world in 92.4 s, passing every
  invariant; all 739 non-metadata mod files rehash to the report's digest. Fifteen differ
  from the 1.4.2 reference; no raster or terrain file differs. Renew the current-build
  reference; the earlier digest remains in C144. See [experiment 025](../../experiments/025-patch-1-4-3/README.md).
- [V-EXEC] All eight local installation tests pass with `RNW_REPRODUCE=1` in 113.27 s,
  including an independent full export matching the new reference digest.
  Formatting/lint, strict types, 811 Python tests (8 optional skips), and 23 Rust tests pass.
  The sandbox prevents the type checker from inspecting Python; running it outside the
  sandbox succeeds. No code or configuration was changed for that environment limitation.
- [UNKNOWN] No claim of 1.4.3 loading or playability; no installation, game launch, push
  or publication.

## 2026-10-22 — Close-zoom cover and lobby safeguards (0.9.26)

- [V-GAME owner / V-LOCAL C150] The owner sees trees, rivers, resource markers and
  cities through the cover at close zoom and starts as a New World country from the
  map. The latest profile log mounts the 0.9.20 world on EU5 1.4.3. C139's political
  lens success did not validate these open checks. Record the failure in experiment 026.
- [V-EXEC C151] Extend cover output from 9 to 19 files: eight shader/include and two
  GUI overrides. Include tree shadow passes, standard mesh rendering and lobby-only
  marker suppression. Hide covered country cards/selected-country information and
  guard start/join controls; suppress the unfiltered random selector while covered.
- [V-EXEC C151] A failing-first regression catches an include-resolution hole in the
  binding audit: generated overrides now take precedence over installed includes.
  Five consumers of the standard mesh include have no duplicate slots. Four tree
  shadow HLSL variants compile with typed native-call stubs; this is not EU5 compilation.
- [V-EXEC C151] Raise release to 0.9.26 and epoch to 2, preserving epoch-1 digests.
  A real CLI export takes 90.2 s and passes all invariants; independent disk hashes
  give 749 non-metadata files, `e1654f67aa8fdae52b988bb96dc6dd75f16f289563ba448230dba9add85e708b`.
  Ten files are added and only the scripted GUI changes relative to C149; all existing
  geography, civilization and raster files remain identical. Renew the reference.
- [V-EXEC] Required checks pass: formatting/lint, strict types, 835 Python tests
  (8 optional skips), 23 Rust tests. All 8 installation tests pass in 109.34 s with
  an independent full reference export. The candidates stay outside every profile
  under `local_data/close-zoom-cover/`; no existing mod, game or playset was changed.
- [UNKNOWN] Native map picking is not intercepted, and UI guards do not establish an
  engine-level ban. Concealment, UI start prevention, discovery, keyboard routes and
  multiplayer still require in-game confirmation. No EU5 launch, push or publication.

## 2026-10-22 — Install the cover candidate (owner request)

- [OWNER] Install verified updates directly instead of asking the owner to copy files.
  The standing workflow is now recorded in `AGENTS.md`.
- [V-EXEC C152] With EU5 closed and the destination absent, install 0.9.26 into the new
  profile folder `mod/rnw_exp_world_hgihw5wfjp` through `rnw install-mod`.
  Independently hash all 751 files, including metadata: every hash matches the source.
  Displayed name: `RNW: Small continents HGIH`. Installation leaves the active playset
  pointing at the older DSLL world; HGIH needs selection in the game's playset.
- [UNKNOWN] No game launch, runtime validation or change to earlier gameplay verdicts.

## 2026-10-22 — R7b and R7c designed for Sonnet (Opus)

- [V-LOCAL/V-EXEC C155] Technology at the start is `starting_technology_level`: age-of-traditions
  advances above a country's level start unresearched. Vanilla American states are 191 of 223 at
  level 2; the 1337 Americas have no institutions, roads or rivals, so R7 needs none for them.
- [V-EXEC C156] On the 0.9.23 small_continents world 109 of 131 generated states start at level 0:
  the level follows the culture's vanilla template and one complexity threshold, not the society.
  Its great empire is large (58 locations) but has no other cause of strength and no weakness.
- [V-LOCAL/V-EXEC C157] Advance trees and units follow three regional families chosen by the
  capital's region key, which the hierarchy places by vanilla position; cultures are matched by
  climate. Only 56 of 131 states and 40.4% of the population sit in their culture's family.
- [V-LOCAL/V-EXEC C158] Vanilla levers for extraordinary societies: `country_rank`, start-up
  opinions (the Andes and Mayapan records), and roads, whose 1,646 pairs all join locations in
  pixel contact. Tributaries are out of reach for native monarchies.
- Design [R7b and R7c design](../r7-technology-and-empires.md):
  R7b (S09) levels by complexity on the vanilla quantiles, templates that follow the level, the
  family in the homeland vector; R7c (S10) empires at `min(T, S + 1)` with the highest American
  rank and royal roads, feared by neighbours and resented by vassals. No generated output changed;
  no version bump, no game launch, nothing installed.

## 2026-10-22 — R7b: technology from the societies (Sonnet)

- [OWNER] The 0.9.27 cover candidate was uncommitted at the start of R7b, as the handoff foresaw;
  the owner asked for it to be committed first (`b4661b2`). Base builds of four worlds were made on it.
- [V-EXEC C159] Generator 0.9.28 (epoch 4): a state's `starting_technology_level` follows the rank of its
  capital's complexity on the vanilla American distribution (11 × 0, 17 × 1, 191 × 2), a great empire gets
  the highest, a tribe none; the template follows the level within one level of the culture's own
  (`template_for_level`); the homeland vector gains the three regional family shares
  (`FAMILY_WEIGHT = 2`). New module `eu5_technology.py`; `verify_technology` and the report section
  `technology`.
- [V-EXEC C159] Four builds against their base builds: all invariants pass; levels equal the vanilla
  quantiles within one state; family agreement 924–1000‰ of states, 943–996‰ of the population (C157:
  427‰, 404‰); homeland distance at most 1.092 times that without the families; land, gfx, development and
  markets byte-identical to the base. The weight of 2 met every criterion at the first attempt.
- [V-EXEC] The reference world is renewed for epoch 4 and made again byte for byte; all 8 local tests pass.
- [UNKNOWN] Written levels, researched advances and the lords' vassals are untested in game. No EU5
  launch, push or publication.

## 2026-10-22 — R7c: great empires with causes and weaknesses (Sonnet)

- [V-EXEC C160] Generator 0.9.29 (epoch 5): a great empire starts at level 3 (`min(T, S + 1)`) over a
  level-2 template with `rank_duchy`, gets royal roads over land contacts from its capital to its
  vassals' capitals, its ranked places and the biggest location of each area, is feared by its independent
  neighbours and resented by its vassals (`opinion` records after the Andes and Mayapan blocks). New
  module `eu5_empires.py`, `societies.land_routes` and `trunk_roads`, `verify_empires`, report section
  `extraordinary`, window texts. A world without empires is byte-identical to R7b's but for `.metadata`.
- [V-EXEC C160] Five builds, all invariants pass; every empire has level 3, `rank_duchy`, 0.24–0.31 road
  pairs per location (bound 1.0), no unlinked target and at least a feared neighbour and three resentful
  vassals. The road bound reads 1000‰ only when a pair belongs to its first location's owner; C158's 260
  countries and median 0.5 were not reproduced exactly.
- The first run on a world without empires failed `verify_empires` because the export leaves the unchanged
  `09_roads.txt` out of its outputs; an absent file is now vanilla's, with a test. The check had not been
  repaired, the fault was in the check.
- [V-EXEC] Reference world renewed for epoch 5 (750 files); all 8 local tests pass. Installed as
  `rnw_exp_world_canszr3phf` (752 files hash like the manifest; the other mods and the profile root are
  unchanged), recorded in `INSTALLED.md`. Experiment 028 is prepared, NOT-RUN.
- [UNKNOWN] Written level, rank, roads and opinions, and their direction, are untested in game. No EU5
  launch, push or publication.

## 2026-10-22 — Interoperability register checked against primary legal texts

- [SOURCE] Read Directive 2009/24/EC, the SAS and Nintendo judgments, Directive 2001/29/EC
  (2019 consolidation), Paradox's current User Agreement and conduct rules, EU5's Steam EULA page,
  and the Steam Subscriber Agreement clauses cited in the [register](interoperability.md).
- [V-EXEC] Replaced the memory-based legal paragraph and corrected the old/current article numbering;
  separated format research, code translation, asset copying and publication. Added source dates,
  provision/paragraph references and a case-specific evidence checklist. Qualified R-001's legal basis
  without revalidating its technical observations or changing generator output.
- [UNKNOWN] National-law application and rights in particular copied geometry remain unresolved;
  local generation and an asset-free repository are project safeguards, not blanket legal permission.
- [V-EXEC] `uv sync --locked --group dev && make check` passes: formatting, lint and type checks,
  943 Python tests (9 optional local-install tests skipped), Rust formatting/clippy and 23 Rust tests.

## 2026-10-22 — First game session of R7b/R7c (owner), read-only log analysis

- [V-GAME owner C161] The owner ran the CANS world and reports that visually everything seems to work.
- [V-LOCAL C161] The agent read the session's logs (read only, copies under `local_data/r7c/`): 125,820
  `Could not find spline network strip` lines in `debug.log`, for 83 of 97 generated road pairs (once at
  load, then thousands a minute once the game ran) and for 6 roads built in play. `error.log` rotated every
  15–20 s and lost its first 12 minutes. No other line names the new keys or tags. Cause [INFERRED]:
  strips live in the 30 MB binary `spline_network.splnet`, which has vanilla locations only.
- Experiment 028 is PARTIAL; the R7 gate stays open. Not changed: generator, worlds, profile.

## 2026-10-22 — R7d: the spline network of generated locations (owner's choice, Sonnet)

- [OWNER] After the log finding of C161 the owner chose to research the `.splnet` format now. [OWNER] A new
  standing rule: every reverse-engineered closed format or written binary of EU5 gets an entry in the
  [interoperability register](interoperability.md) (necessity, why official means fall short, what is studied or
  changed, how compatibility is kept without distributing Paradox's resources; EU frame Directive 2009/24/EC).
  R-001 is this file; earlier cases are added when next touched.
- [V-LOCAL/V-EXEC C162] The file is the engine's tagged binary with points, segments and strips; an anchor is a
  location's index in `definitions.txt` order; vanilla has a strip for every land-land contact and every road.
  `rnw.splnet` reads and writes it back byte for byte (31,615,438 bytes, 0.8 s and 0.3 s).
- [V-EXEC C163] Generator 0.9.30 (epoch 6) writes the mod's file: the vanilla strips of kept locations
  renumbered by the mod's order and a strip for every land contact of a generated location. An independent
  check against the mod's raster finds every anchor on its own location; the three builds differ from R7c only
  by the new file, `.metadata` and `inputs.json`. Reference world renewed; 9 local tests pass. Installed as
  `rnw_exp_world_6wbnuwo42f`; experiment 029 is prepared, NOT-RUN.
- [UNKNOWN] The engine's acceptance of a file written by us is untested; its own reader is not available. No
  EU5 launch, push or publication.

## 2026-10-23 — A report of vanished roads with 0.9.30 (owner; retracted below), 0.9.31

- [V-GAME owner C164, retracted in C166] The owner reported that the 0.9.30 world loaded, wrote no strip error and no
  crash, and drew no road anywhere; the owner later found the wrong lens had been on. The logs hold no line about
  splines or roads; the world differs from the 0.9.29 one in the spline network only.
- [V-EXEC C165] 0.9.30 changed the order of the Old World's own segments (renumbered by the strips that use them);
  a first reading that vanilla numbers points in segment order was a flawed test and is withdrawn (vanilla numbers its
  points in runs along roads, its segments in an order of their own). 0.9.31 keeps every kept segment and point in
  vanilla's order and only closes the gaps (the identity rebuild writes vanilla's bytes), adds new roads as chains of
  short segments after the old ones and spaces their points evenly. Epoch 7, reference world renewed, 9 local tests pass.
- Installed `rnw_exp_world_amk4jfomct` and the probe `rnw_exp_probe_splnet_oldworld` (the same map, only vanilla strips of
  the locations still there); [experiment 030](../../experiments/030-spline-probes/README.md) says how to bisect with at
  most three launches. (Those probes answered a premise that was retracted; no defect in 0.9.30 is established.)
- No EU5 launch by the agent, no push or publication.

## 2026-10-23 - Owner acceptance of TI drawings; country-list layout candidate

- [V-GAME owner C173] 0.10.0 shows vanilla TI drawings, including dragons. The country list still has a large gap: the tag-matched filter of experiment 031 did not achieve its intended result. The screenshot depicts the cover; the list result is the written owner report.
- [V-LOCAL C174] Rechecked Steam build 26105915 (1.4.3), the lobby's fixed 74-pixel rows, and vanilla vbox lists with ignoreinvisible=yes. [INFERRED] Fixed rows reserve the hidden widgets' space. The reason the script filter has no effect is not established.
- [V-EXEC C174] 0.10.1/epoch 11 replaces that one layout with a vbox excluding invisible children, 67-pixel cards and 7-pixel spacing. Search/sort/model and visibility guards remain. Removed the ineffective filter and ten text files. Both regression tests fail on the previous exporter and pass with this change; missing/duplicated anchors fail closed.
- [V-EXEC] At the owner's request, removed exactly ten obsolete profile mods: the road probe and worlds 6WBN, AMK4, BDWK, CANS, DSLL, HGIH, HU2B, J3ZE, QDUV. Hub and CYHL retained; all their files and every profile-root file compare byte-identical. Library worlds, saves and playsets were not modified.
- Experiment 032 records the owner's required scrolling/search/sort and card-size checks. No agent game launch, push or publication. Visual acceptance of 0.10.1 remains [UNKNOWN].
- [V-EXEC] Full checks pass: 958 Python tests and 23 Rust tests, formatting, lint and type checks; all 10 optional local tests pass with `RNW_REPRODUCE=1` (152 seconds). Epoch 11's new reference has 752 non-metadata files, digest `652b1c86bc96d972ed5845c254490f841b7ceadd39981e3b0bb128dba32809e0`. The candidate 6DIV is installed and kept in the normal library: all 754 files match the staged world. Against CYHL, only the lobby GUI and metadata change and the 11 filter/text files disappear; all map, shader and start bytes match. All profile-root files, hub and CYHL remain unchanged after installation.

## 2026-10-23 — The roads had not vanished (owner), C166

- [V-GAME owner C166] The owner looked again with the Roads lens: roads are there, a network over the Old World and a
  dense one over the four empires' territories; the report of vanished roads came from the wrong lens. The session
  (00:15–00:18) started 6WBN (0.9.30) and then AMK4 (0.9.31); the screenshot is probably AMK4. Both starts have 0
  `spline network strip` lines, no spline or road line in `error.log`, no crash.
- C164 is marked retracted; C165's premise is withdrawn, its file facts stand. Experiment 030 is superseded (probe B and
  the control are not needed), experiment 029 is PARTIAL. Whether 0.9.30 would have shown roads too is unknown; the
  order-preserving rebuild of 0.9.31 stays as the safer design.
- Not yet seen: a long run (the 0.9.29 flood began after about five minutes of play), roads built in play between
  generated locations, the empires' roads as lines, caravans. No EU5 launch by the agent.

## 2026-10-23 — A long run with 0.9.31 (owner), C167; wording about 0.9.30 corrected

- [V-GAME owner / V-LOCAL C167] AMK4 (0.9.31) ran 5 min 43 s at maximum speed: 0 strip errors, none in `error.log`
  about the mod (only the old `rnw_probe_hidden` lines), no crash, three autosaves; the AI tried `build_road` 15 times and
  each was logged as an invalid AI command, among thousands of invalid commands of other kinds. Whether a road was built
  in play is not shown.
- Wording corrected across the documents (README, C164 to C166, experiments 029 and 030, the register, the roadmap,
  `natives.md`): a defect in 0.9.30 is **not** an established fact, the report was most likely an observation error, and the
  order-preserving rebuild of 0.9.31 is a precaution, not a verified fix. The history of the commit `b6fd2da`, whose
  message says 0.9.30 drew no road, is left as it was.

## 2026-10-23 — The map's frame is black over the New World (owner), C168, C169, C170; 0.9.32

- [V-GAME owner C168] The owner's screen recording of the 0.9.30 session shows the proximity lens in observer mode, not
  Roads, and roads drawn on the map at zoom: 0.9.30 drew roads, the report of C164 was an observation error, and the
  order-preserving rebuild of 0.9.31 stays a precaution. A road built by hand in Bohemia works. Roads between generated
  locations in play cannot be tried: the world is covered at selection and the owner cannot start there.
- [V-GAME owner / V-LOCAL C169] Two screenshots at country selection: above and below the map the table of the frame is
  black over the New World's longitudes. The installed AMK4 cover's first and last grid rows are covered at those stretches
  of x; the clamp of `RnwCell01` extends them beyond the map's edge, and the mesh shader clips the table there.
  [V-LOCAL] No `RnwVisibility` or shader-compile line in the latest logs; the owner saw no problem with loading art and
  portraits (experiment 027 passes for them).
- [V-EXEC C169] 0.9.32, epoch 8: `RnwMask` returns 0 outside z 0 to 8192. Test, synthetic digests of epoch 8 and the reference
  world renewed (`RNW1-0426C-SYW6B-MW73Y-C004J-0054V-AW0`); `make check` 946 passed (one of three full runs failed
  `test_window.py::test_new_world_visibility_is_a_default_and_leaves_the_existing_world_hidden`, which passes alone five
  times and in the two next full runs; a flake, not investigated); 9 local tests pass with `RNW_REPRODUCE=1`.
  The candidate `RNW1-080G0-00003-EF38N-A004J-00813-BM0FJ-JT80` (AMK4's world) is installed as `rnw_exp_world_j3ze425437`;
  against AMK4 only the cover include and `.metadata` differ.
- [V-LOCAL C170] 17 `have not discovered the capital ... scripted bias` lines in every session since 0.9.30, all from
  the opinions of R7c; the vanilla logs have none. Found by reading the logs; not fixed.
- No EU5 launch by the agent, no push or publication.

## 2026-10-23 — The opinions of the empires: every holder knows its partner's capital (0.9.33), C171

- [V-LOCAL] Vanilla's countries get `discovered_areas` of a whole region from an exploration template (`expl_andean` lists
  the eight areas of the Andes), so the opinions of the Andes block never name a capital the holder has not discovered. A
  generated country knew its religion zone and its own areas only, which is where the 17 warnings of C170 came from.
- [V-EXEC C171] 0.9.33, epoch 9: after the empires are planned, the holder of every generated opinion discovers the area of its
  partner's capital (`discover_opinion_partners`); `verify_empires` checks it on the written records. 7 new tests (953 pass).
  The AMK4 world made again: 17 areas added to 16 countries, one per warned pair, nothing else changed in the setup, the
  mod differs from the 0.9.32 one in `10_countries.txt` and `.metadata` only. The reference world has no pair that needs
  an area, so its digest stays that of epoch 8 and only its code (the release) changes; it no longer exercises this rule,
  the AMK4 world does. Installed as `rnw_exp_world_bdwkgaakvy`.
- [UNKNOWN] Whether the game applied the bias before, and whether the 17 lines disappear in game.
- No EU5 launch by the agent, no push or publication.

## 2026-10-23 — 0.10.0: the cover's drawings and the list without a gap (owner), C172

- [OWNER] The latest run looks right in shaders and in the hiding of the New World; two items remain (the covered New World is a flat colour without the game's dragons and compasses; the lobby's list has empty stretches where the hidden countries stand), and the version is to be raised to 0.10.0, "we have stayed on minor updates". [V-LOCAL] The run's `error.log` has no `have not discovered the capital` line (C171 works at load) and no shader line.
- [V-LOCAL C172] The gap: the list is a `fixedgridbox`, a hidden item keeps its cell; vanilla uses `ignoreinvisible` on boxes (never on a `fixedgridbox`), and the lobby asks for the scripted filters of the tag `no_filters`, which no vanilla filter has. The drawings: `terra_incognita.shader` reads `terra_incognita.dds` (16,384 x 8,192, DXT1) through a sampler with `Index = 2` and `file`; the shader graphs of the terrain and the water hold no `Index` sampler.
- [V-EXEC C172] 0.10.0, epoch 10: the cover reads the drawings through a sampler of the mod's declared like the game's (no copy of the texture), in the terrain and water shaders only; the export refuses a shader where Index 2 is held by another sampler; a scripted filter and its texts in ten languages leave the New World's countries out of the lobby's list. 958 tests pass (one local test more); the reference world has 763 files and is renewed; 10 local tests pass with `RNW_REPRODUCE=1`. Installed as `rnw_exp_world_cyhlrdiik7`; against 0.9.33 only the two shaders, the cover include, 12 new files and `.metadata` differ. [experiment 031](../../experiments/031-cover-drawings-and-list/README.md) says what to look at.
- [UNKNOWN] Whether the engine binds an `Index` sampler in the terrain and water draws (the one precedent is the overlay's own shader and `tree.shader`); a failure is a missing or garbled drawing, or a crash at the first map frame as in C137 and C138. Whether the filter is applied in the lobby.
- Searching the strings of `eu5.exe` for the slot names found nothing usable (`PdxTexture0` to `2` and the TI names only); nothing was derived from the binary. The shader cache's generated sources were read to see how samplers are declared (a `Texture2D` in `space1` each, bound by the engine at run time).
- No EU5 launch by the agent, no push or publication.

## 2026-10-23 — Content plan reviewed against the installation, C175–C180

- [V-LOCAL C175] 95 of the 154 vanilla formable target tags have no country definition and no 1337 country (`ADU`, `AZT`): the plan's "target tags without ghost starting countries" is vanilla practice, not an engine unknown; only a mod-defined tag remains to be seen.
- [V-LOCAL C176, C177] Russian case forms fall back to *державы X* for any tag without its own; 520 of 544 American definitions have the adjective equal to the name. The plan's task of separate native adjectives and Russian inflection is dropped; vanilla's `country_flavor` gives the political titles.
- [V-LOCAL/V-EXEC C178] The game has a Turkish localization the export does not write; it becomes the first item of N1.
- [V-EXEC/V-LOCAL C179, C180] Region and area keys survive by position (`_land_areas`); 525 references to them, among them eight American scripted country names, keep vanilla meaning on random land. The plan's G1 is widened from locations to these keys, with a decision per consumer (keep, rebind, neutralize, replace) and region keys by content as option N5.
- [V-EXEC] `docs/content-plan.md` rewritten as stages N0–N5 with a river pilot, R7d split off, static templates in the world mod (the hub carries no game files) and three owner decisions. No code or output changed; no version or epoch change.
- No EU5 launch by the agent, no push or publication.

## 2026-10-23 — Languages and the scope of 1.0.0 (owner)

- [OWNER] The mod's languages are the game's official languages everywhere. Authored text is English for now; before release everything, the generator included, is localized into all eleven. Recorded as a product rule in `AGENTS.md`, in the product spec and as roadmap phase L1; the export is to take its languages from the installation (C178), and a release check is to fail on a missing or stale translation.
- [OWNER] Everything in the content plan is part of 1.0.0; nothing is deferred. The plan, its roadmap row and P1's dependencies say so; R7d is included. N5 stays an open decision (whether, after N0).
- [V-LOCAL] The owner's profile `pdx_settings.json` holds no language entry; where the game keeps its language choice is not known.
- No code or output changed; no EU5 launch by the agent, no push or publication.

## 2026-10-23 — N0: the New World's vanilla content consumers inventoried and decided, C181–C185

- [V-EXEC C181, C182] `rnw content-inventory GAME_DIR OUT` scans the scripts under the remap roots and lists every top-level object that names an American tag, location, province, area, region or subcontinent, is retired by the exporter, or reads state only retired objects set: 634 consumers. Each has one decision in the committed table (`content_decisions.py`, identifiers only): keep 391, rebind 6, neutralize 84, replace 153. The export now stops on an object without a decision (`content_check.py`); the reference world of epoch 11 came out byte for byte the same.
- [V-LOCAL C183, C184] Two retained rewards lose their path in ways the earlier retirement did not show (`flavor_chk.32`, `hurin_qusqu_privilege`); five of the eight American formables are culture-bound and can be rebound to the territory their culture holds (N1), three are colonial and wait for the postcolonial federation (N4); the Panama canal is a seven-object chain that cannot stand on random land.
- [V-EXEC C185] The positional mechanics for N5 are 68 objects in 27 files that name every American region key and 53 areas. The decision stays with the owner, after seeing whether those read sensibly on random land.
- Judgement, not measurement: which events name "American history" was decided by title, text and gating (the rule is in the plan); the table is the place to disagree.
- No game launch, push or publication; no version, epoch or output change.

## 2026-10-23 — 0.10.2: the official languages from the installation, C186

- [OWNER] The mod uses exactly the game's languages everywhere (AGENTS.md, product spec, roadmap L1). The first item of N1 is code now: `rnw.languages.official_languages` reads the language folders of `game/main_menu/localization`; the world's name files are written for each (eleven on 1.4.3), so Turkish, which the fixed list of ten left out (C178), is written.
- [V-EXEC C186] Epoch 12 and a new reference world (754 files, two more than before); synthetic digests renewed; 978 tests pass and the 12 local tests pass with `RNW_REPRODUCE=1`. The window tests `test_window.py` failed once in four runs and passed on the others, with and without this change (timing of the controller thread); not investigated.
- [UNKNOWN] A Turkish interface's reading of the new files. Authored text still carries the same names in every language; translation belongs to L1.
- No game launch by the agent, no push or publication. Not installed: the owner's candidate of N1 follows the rest of the stage.

## 2026-10-23 — 0.10.3: the decisions of N0 carried out, C187, C188

- [V-EXEC C187] `eu5_content.py` carries the table into the scripts: 101 objects are neutralized by closing their gate, five culture-gated formables get the places where their culture dominates, the Nahuatl start effect gets a seat. Epoch 13, reference world of 761 files, synthetic digests renewed; 987 tests pass and the 12 local tests pass with `RNW_REPRODUCE=1`.
- [V-LOCAL C188] Why gates and not deletion: the events stand in on-action pulse lists and fire one another, so deleting them would leave dangling references.
- [V-EXEC] In the reference world four of the five historical formables found too few places of their culture (the American cultures that dominate a location are 161 of the 242 vanilla ones, and Nahua, Quechua, Mohawk, Keres, Zuni and Maya are not among them there). That is the "no eligible bearer" outcome of the plan, not a defect; the owner's experiment looks at a world where a culture holds ground.
- [UNKNOWN] That the engine takes `always = no` in the `potential` of a formable and in the `country_trigger` of a scripted name as it takes it elsewhere (vanilla uses `always = no` in many triggers); that no line of `error.log` follows. The exceptional resource places of N1 are still to come.
- No game launch by the agent, no push or publication. Not installed.

## 2026-10-23 — 0.10.4: exceptional resource places, C189, C190

- [V-EXEC C189] The five historical natural-resource bonuses lost with the Americas (C182) are replaced by five places of the generated land: silver in mountains and hills, a mercury lode, a fishery on a coast, each a static modifier of the mod's own with the effect size read from the installation and original names. Epoch 14, reference world of 762 files, synthetic digests renewed; 994 tests pass and the 12 local tests pass with `RNW_REPRODUCE=1`.
- [V-EXEC C190] The new local test with `RNW_LAYERS=1` (three exports) shows the layers keep to themselves: peoples rerolled leaves the places, resources rerolled leaves the countries.
- N1 of the content plan is complete offline: Turkish (0.10.2), neutralization and rebinding (0.10.3), exceptional places (0.10.4). The owner's experiment (a colony without a vanilla American name, a rebound formable that appears only to its culture, an exceptional place that shows its bonus, no new `error.log` lines) is NOT-RUN.
- No game launch by the agent, no push or publication.

## 2026-10-23 — N2: the hook probe prepared and installed, C191, C192

- [V-LOCAL C191] EU5 keeps state in variables; the plan's "variables and flags" becomes variables (no `set_*_flag` effects exist). Subjects are made with `create_country_from_location` and `make_subject_of`.
- [V-EXEC C192] `rnw probe-hooks` writes `rnw_exp_probe_hooks` (a formable of the new tag `ZQP` with the full `ADU` set of files, a scripted country name of the mod's own, start variables on France and Paris, two decisions). Every anchor is checked against the installation and a moved one stops the build. Installed into the profile as a new folder, hash-identical; no playset touched. Experiment 034 lists the steps and what each answer blocks or frees.
- [UNKNOWN] Everything the probe asks. N3 and N4 stay free to be designed and tested offline, but the branches that lean on a hook stay blocked until the owner runs the probe.
- No game launch by the agent, no push or publication.

## 2026-10-23 — 0.10.5: the content model and the river pilot, C193–C196

- [V-EXEC C194] `content.py` plans, from the finished world, who is offered a River centre, a Sacred centre or a River-basin union (and why not, where none): four, two and two in the reference world. `stories.py` holds the two story graphs as data (original English, texts for L1), `eu5_story.py` writes the world's files: a hidden start event per bearer bound to its tag, the static events of each family present, the payload copies, the privilege, the unions with the full set of files of the vanilla formable-only `ADU`.
- [V-LOCAL C193] The stories lean on practice vanilla already shows (hidden events, dynamic historical events with a tag, a variable holding a location, delayed `trigger_event_*`), so N3 does not wait for the probe of N2 on the yearly pulse or the start variables; the union alone leans on H1. All of it is NOT-RUN.
- [V-EXEC C194] Epoch 15, reference world of 782 files; 1,038 tests pass; the 13 local tests pass with `RNW_REPRODUCE=1`; `RNW_LAYERS=1` shows that the peoples' reroll changes the stories and the resources' leaves them.
- [INFERRED] The decision table rows that name N3 are now carried in purpose (C196); the building of the plan's wording became a location modifier.
- No game launch by the agent, no push or publication.

## 2026-10-23 — Experiments cost minutes: the console sitting 036, C197

- Owner's correction: experiments 033 to 035 assumed play (a colony, decades of waiting, a formation across a campaign). A development experiment must cost minutes: either console commands or none. Recorded in `AGENTS.md`.
- [V-LOCAL C197] The installed game has a console (`event`, `tag`, `effect`, `trigger`, `run_months`, `run_until`, `change_date`, `goto`, `conquer*`, `helplog`, `event_counts` and more); the names and the one-line help were read as text from `eu5.exe` (no format or code studied, nothing written to the interoperability register); the vanilla debug event `qa_debug_backdrop.1` shows `event <id>` is the way to fire an event on purpose. Argument forms and what refuses in single player are [UNKNOWN] until typed.
- Experiment [036](../../experiments/036-console-session/README.md) replaces the owner's steps of 033 to 035 with one sitting of about fifteen minutes (ten rows, EIL2 plus the probe); the agent reads `error.log`, `game.log`, `debug.log` and the event log itself. 033 to 035 keep what each asks and decides.
- The probe gained a story start in miniature (H7): a hidden `dynamic_historical_event` for Bern with a certain monthly chance in the first year, a variable holding a location, a delayed event; it has the shape of the stories' own start event. `rnw_exp_probe_hooks` was rebuilt and replaced in place (own folder, 21 files hash-identical to the generated tree, nothing else in the profile touched).
- Open: a conquered bearer's chain and a save mid-chain are not in the sitting (covered offline); a colony's name and a culture's formable need play and wait for N4 and L1.
- No game launch by the agent, no push or publication.
- [V-EXEC] Two GUI tests fail now and then, with or without these changes (about one run in ten to forty): `test_new_world_visibility_is_a_default_and_leaves_the_existing_world_hidden` (cause found: `controller._work` publishes `Phase.FINISHED` before `refresh_library` has read the new world, so a poll between the two sees no selected world; the window itself repaints on the later `_changed`) and `test_a_missing_cover_keeps_the_visibility_checkbox_and_reports_the_problem` (asserts the notice text without pumping the queued update). Not changed here: moving the phase after the refresh alters what the window shows during the refresh and wants a look at the window; recorded for the GUI work.

## 2026-10-23 — The first console sitting (036) on 1.4.4: what it showed and what it found, 0.10.6, C198-C204

- [OWNER] Ran the sitting 036 as Bern (17:02 to 17:12) with the hub, the probe and EIL2, and sent eleven screenshots with three observations: the colony of Bern could not be found, the formable and decision names looked wrong, and *many flags flicker hard in the country list, which had not happened before, even with our mod*.
- [V-LOCAL C198] The executable had been updated that morning (Steam build 26142040, **1.4.4**, 11:24): only `binaries/` changed, the data is 1.4.3's and the map-contract fingerprint is the same, so the generator accepts it. The sitting was the first in game on 1.4.4.
- [V-GAME C199] The agent read the session's `debug.log` (the whole session; `error.log` rotated five times in three minutes), `game.log`, `gui.log`, the console files and the autosave written on quitting, which is plain text and records what the sitting did (a country made from Interlaken on 1338.2.1 with `reason=ScriptedEffect`, the vassal dependency, the story variables and modifiers). What works: a formable of a mod-defined tag (H1), a dynamic start with a variable and a delayed event (H7), a yearly pulse hooked in `on_actions` (H6), the first events of the river and sacred stories, the exceptional places.
- [V-GAME C200] The probe's own `on_game_start` with an `effect` replaced the game's start effect (`There is more than one 'effect' defined using most recent`; `flavor_bul.7 is orphaned`): a mod must hook the start through `on_actions`, as the game's `ai_personalities_setup.txt` does. The probe also used `trigger_event`, no effect of the game, so its start event never opened.
- [V-GAME C201] Missing keys show as bare keys on the screen and the engine logs those of formables (`localization_util.cpp:103`): decisions need `<id>.title`/`<id>.desc`, formables `<id>`/`<id>_desc`. The probe's decisions and formable and the generator's unions lacked them.
- [V-GAME C202] 79,375 lines of `Invalid right side during comparison 'location'` from two DLC picture files that name locations the world removed (Teotihuacan and Cholula); none on vanilla. The inventory of N0 did not scan `gfx/images`.
- [V-GAME C203] The owner's flicker report meets one engine line at load: `multiplayer_lobby.gui:4792 Unsupported property: size with a percentage on widgets that are a child of a vbox/hbox`, the card of the list that 0.10.1 made a `vbox`. [INFERRED] That is the likely cause; a second suspect is that a `vbox` instantiates all 2,900 cards where the game's large lists are fixed-row grids. Our shaders do not draw flags, so the owner's guess of a shader is not supported.
- [V-GAME C204] The river story's `remove_location_modifier` was in the country's scope (two lines logged at load).
- [V-EXEC] 0.10.6, epoch 16: the card sized as vanilla sizes a `vbox` item; `gfx/images` joins the remap roots and the illustrations of removed places are dropped with their comments (636 consumers, 0 undecided); location modifiers of the stories change in the scope of the centre; the unions get their formable keys; the probe (0.2.0) hooks the start as the game does, uses the right effect and keys, and shows the name of the subject it makes in an event. Tests first for each (the lobby, the scope, the keys, the dropped pictures, the probe); `make check` passes (1,048 Python tests, 23 Rust tests); the 12 read-only local tests pass; the reference world of epoch 16 (784 files, `84d0787b...`) differs from EIL2 exactly in the lobby GUI, `rnw_river.txt`, eleven story localizations, two picture files and the metadata.
- Installed (see [INSTALLED](../../experiments/INSTALLED.md)): `rnw_exp_world_prj3zj4whq` and the replaced probe. Experiment [037](../../experiments/037-console-session-2/README.md) asks what is left, in about ten minutes.
- [UNKNOWN] Whether the flicker is gone; the colony's scripted name (H2); the formable and decision names on screen; the sacred privilege.
- No game launch by the agent, no push or publication.

## 2026-10-23 — The second sitting (037): the list still flickers; 0.10.7 stops hiding, C205-C208

- [OWNER] Ran 037 (EU5 1.4.4, 18:32 to 18:42, then a game to November 1339): *the flags of the country list flicker hard, sometimes showing another flag for a moment; the flags at the end of the list do not, probably the ones before the space once reserved for the New World; a search brings the blank stretches back*; the start state event showed; the colony was not understood, only a vassal. Proposed: fix it or change the approach, for example grey and unclickable instead of hidden.
- [V-GAME C205] The percentage size that 0.10.6 removed was not the cause: the engine's line appears at the first load (EIL2) only, and the flicker stayed on PRJ3. [INFERRED] A `vbox` of every card builds a widget and a flag for each of them where the game's big lists are fixed grids, and cards left out of layout break a search. The agent's first reading (the percentage) was wrong; recorded in C203.
- [V-GAME C206] The start hook through `on_actions` works beside the game's start (all four lines of *start state*, no `orphaned`, no `more than one 'effect'`).
- [V-GAME C207] The colony is a vassal named *Interlaken* two game years on: the scripted name does not apply to a plain vassal (the save and the tooltip). The decision itself worked on the first day. Probe 0.3.0 uses the game's colonial subject type.
- [V-GAME C208] On PRJ3 the log is free of the faults of 036 (no scope, key, picture or orphan lines); the probe's decision tooltip floods `SET_CAPITAL_EFFECT`, hidden in 0.3.0.
- [V-EXEC] 0.10.7, epoch 17: the lobby's fixed grid is the game's again; cards of the New World are dimmed and their click disabled; the guards of the start and join buttons stay. `make check` passes; the reference world of epoch 17 (784 files) differs from PRJ3 in the lobby GUI alone. The names of the New World's countries now show in the list (the owner proposed this approach); masking them is possible and not done.
- Installed: `rnw_exp_world_kpjmspjsw3` and the probe 0.3.0 ([INSTALLED](../../experiments/INSTALLED.md)). Experiment [038](../../experiments/038-lobby-list-and-colony/README.md) asks about five minutes.
- No game launch by the agent, no push or publication.

## 2026-10-23 — The third sitting (038): the list is quiet, the colony is a colony, C209-C211

- [OWNER] *The countries do not flicker, the colony works*, with a screenshot of *Colony of Interlaken* (*Colonial Nation of Bern*, loyalty 81.46 per cent).
- [V-GAME C209] The fixed grid with dimmed cards removes the flicker; `gui.log` is silent about the lobby. The owner added: the cards are grey and the click is dead; a double click still moves the camera to the country's place and that is accepted, no fix wanted. The search lists its matches with no blank stretches (owner, afterwards): the lobby list is done.
- [V-GAME C210] The colony of type `colonial_nation` shows the game's own *Colony of Interlaken*, not the scripted name; with C207 neither type reaches the scripted names from `create_country_from_location`. The plan's colonial names (N4) are then the game's default unless the game's own colonization shows another path.
- [V-GAME C211] The probe's log is clean; the rest of `error.log` is the vanilla baseline.
- Hooks of N2 now answered in game: H1, H3 (`on_actions`), H6, H7 hold; H2 is negative for names made by the effect; H4 and H5 are open and block nothing.
- No game launch by the agent, no push or publication.

## 2026-10-23 — N4a: four more formable families, 0.10.8, C212-C214

- [OWNER] "Execute N4." The sittings 036 to 038 had answered N2, so the families that need no new hook go first: the formables.
- [V-LOCAL C212] The installation has the ranks, `num_of_ports`, the emblems, the culture groups and the five modifier sources the families lean on; the readme says a formable shows only to a country that owns a place of it.
- [V-EXEC C213] One planner for every formable family; calibrated on the captured facts of the reference world and of four other presets, not on a synthetic chain: the first thresholds (centres at the 75th percentile of the states' places, a fifth of the territory on mountains) found neither a confederation nor a league (too few centres in a range or on a coast); the centre bar of those two families is now the median, and the confederation asks for high ground (mountains or plateau), because the states of the reference world stand on a plateau. The reference world offers nine formables, every preset every family. Epoch 18, reference world of 784 files; the layer test passes with the formable file among the compared ones.
- [UNKNOWN C214] The engine's verdict on the new entries and on the formables list is read in the next console sitting of a batch; experiment [039](../../experiments/039-new-world-content-n4/README.md) records what to look for and asks nothing now.
- The stories of N4 (harvest, route and market, great alliance, empire and periphery, contact, colony) and the colonial names follow in the next versions.
- No game launch by the agent, no push or publication.

## 2026-10-23 — N4b: four more stories, 0.10.9, C215-C217

- [V-LOCAL C215] The vocabulary of the new stories (food in province scope, the mutual opinion effect and its modifiers, 23 payload sources) is the game's own; a local test now checks that every word of every story script occurs in the game's scripts, which catches a misspelt effect before the engine does.
- [V-EXEC C216] The story framework moved to `storymodel.py` (a second place, common effects and gates) and the stories to `stories.py` and `stories_n4.py`. Four bearers' selections were written and calibrated on the captured facts of five worlds: harvest (high ground or the most populous tenth), route (two centres of one state, 2 to 8 steps apart over its own places), alliance (neighbours of one faith or capital culture, not subjects; one council per pair), empire (a state with subjects, the most distant subject's capital). The harvest event cuts the province's food by a fifth itself, so the story's shortage is real without a runtime guard that no vanilla event uses. Epoch 19, reference world of 788 files; the layer test passes.
- [UNKNOWN C217] The engine's verdict is read in the next console sitting of a batch (experiment [039](../../experiments/039-new-world-content-n4/README.md)); nothing is asked now.
- Left in N4: the stories that depend on colonization (contact across the ocean, colony becomes a country), the postcolonial federation and the colonial names.
- No game launch by the agent, no push or publication.

## 2026-10-23 — N4c: what waits for the ocean, 0.10.10, C218-C220 (N4 done offline)

- [V-LOCAL C218] The colonial pieces use the game's own vocabulary; one finding changes an earlier reading: the game makes its colonies with `create_location_country_from_province_definition`, so the probe's `create_country_from_location` (C207, C210) may not have gone through the path that applies scripted names. The probe is to be changed for a later sitting; nothing is asked now.
- [V-EXEC C219] Contact and colony have no bearer in the finished world, so they begin in play: the game's yearly pulse gives each country a small chance of a hidden start that checks the country's conditions (the Old World never meets them). The federation needs no named bearer either; its potential is the settlers' culture. 70 colonial names (14 regions by five traditions) take the generated region names. Epoch 20, 792 files; the layer test passes.
- [UNKNOWN C220] The engine's verdict is read in a later sitting; N4 is NOT-RUN end to end.
- N4 is done offline: eight story families in all (the two pilots and six more), six formable families and the colonial names. Left in the content plan: N5 (the owner's decision), the Russian forms and titles of N2, F1 to F4, and the languages of L1.
- No game launch by the agent, no push or publication.

## 2026-10-23 — Probe 0.4.0: the colonial path, C221

- [OWNER] Asked why the probe does not use `create_location_country_from_province_definition`.
- [V-LOCAL C221] It should have: the probe's `create_country_from_location` came from the first search (C191, `tunis_effects.txt`) and answered a different question than the one the colonial names ask. The game's colonial charter goal makes colonies with the other effect; the colonial subject type sets itself up in its own `on_enable`. The statement that N4's colonial names would be the game's default (C207, C210) holds only for the first effect.
- [V-EXEC] Probe 0.4.0 copies the charter goal's effect for `dharug_province` (unowned at the start, checked against the installation) beside the old decision as a control, with a second scripted name and an event that finds the new country; installed over 0.3.0 (21 of 21 identical). No world file changed, so no version or epoch moved.
- [UNKNOWN] The result is read in a later sitting of a batch ([040](../../experiments/040-colonial-path-probe/README.md)); nothing is asked now.
- No game launch by the agent, no push or publication.


## 2026-10-23 — F1 and F2: the offline audit of N0 to N4, 0.10.11, C222-C231

- [OWNER] "Execute F1 and F2": the final verification of the content plan that needs no game ([audit](n0-n4-audit.md)).
- [V-EXEC C225, C227] The mod was compared with the game's files object by object (2,467 script files, 52 rewritten), by record (the setup, the 544 country definitions) and by key (the localization, the map): every difference of every object is a remap, a closed gate, a rebinding, a dropped picture or an absence; the 102 absent objects are exactly the retired events and modifiers; no Old World record, tag, text or object was lost. Two things were not explained and became findings (below).
- [V-GAME C222-C224] The owner's own `error.log` of sitting 038, read against the baselines of 1.4.1 and 1.4.2, is not "the vanilla baseline" (C208, C211): 18 lines `Invalid province_definition key!` (the remap did not read that scope), 18 lines `is missing a title` (a hidden event wants a title; the game's own write `empty_text`), 3 "never set" notices of retired setters, 96 lines of coastal sea zones without ports (known), 4 lines for two islands without a port. The earlier readings looked for the faults of 036 and found them gone; none looked for the faults of the files the audit compares.
- [V-EXEC C226] The inventory reads keyed top-level objects, so two DLC unique buildings (the pyramids of Teotihuacan and Cholula, in a template of raw code) had no row and were remapped to the nearest generated cell while their pictures were dropped.
- [V-EXEC C228] The plan's stage markers said which stage was to carry a replaced object, not what carries it. `CARRIERS` now says it for all 153: 131 carried by 11 families, 22 by none, each with a reason; the table, the tests and the report check it.
- [V-EXEC C229, C230] The reference world gives the same digest under `PYTHONHASHSEED` 1, 7 and a random one; the layer test now compares every file of three worlds (resources: one file; peoples: the start, the countries, the formables, the stories and the texts).
- 0.10.11, epoch 21: `province_definition:` remapped; the DLC monuments dropped with their places; hidden events written as the game's are; `check_outcomes` refuses a world with a vanished object or a missing key; `CARRIERS`; the temple's reason. Reference world `RNW1-0426C-SYW6B-MW73Y-C0050-P001G-B20`, 793 files, digest `88e1d8d8…`, differing from epoch 20's in 14 files and one new one. `make check` passes (1,152 Python tests, 23 Rust tests); the read-only local tests, the reference test and the layer test pass.
- Installed: `rnw_exp_world_t3htedmcwr` (see [INSTALLED](../../experiments/INSTALLED.md)).
- [UNKNOWN C231] Whether the engine's log is clean of these lines after 0.10.11, and everything about N4 in game (F3).
- No game launch, push or publication.

## 2026-10-24 — Sea geography: ports, the shapes and names of water, currents, 0.10.12, C232-C240

- [OWNER] "Finish everything about sea geography; the port problem is documented. And: every sea region is a new sea. In the game the cells of the Mediterranean carry one name, the Black Sea's another, and there are bays and other kinds of cells; in the generated New World every sea cell is a Sea." ([design](../sea-geography.md))
- [V-GAME C232] The 96 `Coastal Seazone` lines of the owner's log (48 zones: 28 `ONE CONNECTOR`, 17 `Possible ones`, 3 `NO POSSIBLE`) and the 4 for Bermuda and Saint Helena are reproduced offline from the same land: each land cell named the sea it touched longest, so a zone whose neighbours all preferred another had no port, and the two islets lost their rows with their replaced sea zones. A zone beside only wasteland is not in the log.
- [V-LOCAL C233, C234, C236] What the game does with water, read from the installation: one port per land location, every port to an adjacent sea, no coastal zone without a port (but the Arctic); topography of sea by cells from land (coastal, ocean, deep two or more; inland sea for the enclosed waters; narrows for the straits) with attrition, freezing and frontage; a current on every deep zone that follows the gyres; the Black Sea's zones all named the Black Sea.
- [V-EXEC C235, C237, C238] `rnw.ports` (a port for every land, a land for every coastal sea zone where it can, by augmenting paths; `settle_seas` merges the cells it cannot serve: 16 of 1,942 in the reference world), `rnw.seas` (narrow water, enclosed water, coast shapes, depth, the game's topography), `rnw.seanames` (one name for a sea, gulf, bay, strait, run of coast, cape and island water; the game's ocean areas by key), `rnw.currents` (the game's gyres continued into the generated deep water), `rnw.eu5_seas` (the game's files: vanilla land's port rows, samples of the game's currents, the export's read-back). Settling the coast uncovered a fault of the sea hierarchy (the Caribbean lost all its water, C237), repaired by pinning shore zones and reserving water for the areas the scripts name. Epoch 22, reference world `RNW1-0426C-SYW6B-MW73Y-C0050-R00KR-D6G` of 793 files, digest `331db1c8…cd23` under two hash seeds. An independent reading of the written map files finds no generated zone or land without a port.
- [UNKNOWN C239, C240] The engine's verdict on the new water and its names, and strait crossings (not generated), are read in a later sitting; nothing is asked now.
- No game launch by the agent, no push or publication.


## 2026-10-24 — The closed ocean: lanes and impassable water, 0.10.13, C241-C244

- [OWNER] After playing 0.10.12 (two screenshots of the topography map, one of Naval Range): "in vanilla most of the ocean is impassable (grey) and there are clear lines of currents between, so the developers draw routes across the oceans; ours is all passable and there is a huge spam of arrows in some areas. I do not know whether that is this world or a systemic fault. Strait crossings also need studying and improving." ([design](../sea-geography.md))
- [V-LOCAL C241] The grey is 46 zones of `topography = ocean_wasteland`, in both `sea_zones` and `impassable_mountains`: 56 per cent of the sea's pixels, a median of 445,000 px a zone. Between them the 750 deep zones are lanes one or two cells wide, two to four cells from land, that the currents follow (median 4 degrees); all the open water is one connected network. A systemic fault: 0.10.12 made all 1,193 deep cells of the reference world deep ocean with a current, and 314 of its 464 contacts with the game's water are with closed zones that it continued with open ones.
- [V-EXEC C242] The canvas replaced 390 of the 750 lanes (14 stretches with two to twelve remaining ends each). The footprint of the replaced lanes laid over the generated cells is the design's key: where they ran over generated deep water, those cells are lanes with the current that ran there (the gyres stay where the game's were), and the rest is closed.
- [V-EXEC C243] `rnw.lanes` (courses, anchors, linking by the cheapest deep string, zones of about 48 cells), `eu5_seas.courses_over`, the impassable lists, `verify_seas` (lists, lanes, reach), `analyse(shore=...)` (cells beside the game's land are coastal: the first run closed Saint Helena's port). Reference world: 420 lanes, 36 closed zones, 1,226 sea cells (from 1,942); presets 262 to 352 lanes. The written files read back: one water with the game's, no closed zone beside land, no port missing. Epoch 23.
- [SOURCE] The EU5 wiki's map-modding page (via search summary): `adjacencies.csv`, type `sea`, the `Through` location "lets the adjacency be blockaded"; the game's own text: a strait "connects two locations separated by a seazone but close enough so armies can cross it without the need of a navy" (C245, the next phase).
- [UNKNOWN C244] The engine's verdict on generated closed zones; nothing is asked.
- No game launch by the agent, no push or publication.

## 2026-10-24 — Strait crossings, 0.10.14, C245-C247

- [OWNER] "Strait crossings also need studying and improving."
- [V-LOCAL C245] `adjacencies.csv` of 1.4.3: 184 rows of type `sea` (49 in the replaced Americas, 135 stay in the mod; C240's 135 was the mod's file) and two canals. A row is two land locations, the sea zone between and two pixels, each on its own location and 1 to 9 pixels apart; the game's text says a strait connects locations "close enough ... so armies can cross it without the need of a navy" and the crossing penalises the attacker. [SOURCE] the wiki's map-modding page (via search summary): `Through` "lets the adjacency be blockaded".
- [V-EXEC C246] The generated landmasses were 100 pixels and more apart: the reference world had two pairs of locations within 12 pixels. `rnw.straits`: near landmasses (within 36 pixels, 2,000 pixels or more) are brought together to a channel of 5 or 6 pixels by a tapered growth that merges nothing and cuts no water off; every pair of lands of different landmasses that a run of at most 9 pixels of sea divides is a crossing, written as the game writes them and read back (`verify_crossings`; independently from the written files: the same 6 pairs in the reference world). The presets 0 to 78 crossings. Epoch 24.
- [UNKNOWN C247] The engine's verdict on generated crossing rows; nothing is asked.
- No game launch by the agent, no push or publication.

## 2026-10-24 — The owner's sitting with the sea work, 0.11.0, C248-C249

- [OWNER] "Tested, looks good."
- [V-GAME C248] The sitting (05:05 to 05:13): the launcher's playset was switched to the 0.10.14 world (`rnw_exp_world_5zovefqzyg`), a 1337 game was played as an observer to 1337.8.8. The logs, read by the agent: no `Coastal Seazone` and no `has no port setup` line (the 00:50 session of the 0.10.11 world had 48 zones and two locations; the zones in that log match that world's adjacency, not the 0.10.12 world's) and nothing in `error.log`, `debug.log` or `game.log` about adjacencies, closed zones, topography, currents, `rnw_sea_` or `rnw_loc_`.
- [V-GAME C249] 263 script errors a session from the lobby's scripted GUI asked about no country (observer games, nothing selected); not from the sea work, harmless, to be repaired with the next change of the lobby.
- S1 is accepted: 0.11.0 (ADR 0003: MINOR rises when a roadmap phase is accepted in game). No file of a world changes; epoch 24.
- No game launch by the agent, no push or publication.

## 2026-10-24 — Two faults of the sitting's log, 0.11.1, C249-C250

- [V-GAME C250] The 0.10.14 world's load logged `map object locator "combat" is incomplete!` and the same for `unit_stack`; the 0.10.11 world's did not. The game's own locators of both kinds cover every land, sea and lake location and none of its 47 closed zones or its wastelands, while the generated closed zones had them (the only difference between the two worlds' locators). They have none now (epoch 25), and `verify_locators` reads the files back.
- [V-GAME C249] The lobby's scripted GUI asked of a country that is none (observer game, nothing selected): 263 script errors a session. It asks `country_exists = this` first.
- Reference world of epoch 25 `RNW1-0826C-SYW6B-MW73Y-C005G-20813-G0HNQ-QV`, 792 files, digest `0b2efd8a…9f54` under hash seeds 1 and 7; make check and the local tests pass. The land cache was not stale: epoch 25 keys fresh entries.
- [UNKNOWN] Whether both lines are gone: the next session's log. Nothing is asked.
- No game launch by the agent, no push or publication.

## 2026-10-24 — R7d (societies): four more extraordinary societies, 0.11.2, C251-C253

- [OWNER] "Выполни R7d". Two things carry the name: the spline network of 2026-10-22 (0.9.30, C162-C163, done) and the *more varied societies* of the content plan (gap G7, open). This is the second; the roadmap and the natives page now say *R7d (societies)*. No Opus design existed ([R7c handoff](../r7-technology-and-empires.md): "they need their own Opus design"); the design is the [natives](../natives.md) section, written after a survey of the installation.
- [V-LOCAL C251] Each of the four combinations has a record that the vanilla 1337 setup already uses: Tlaxcala's republic, the 22 alliances, the Haudenosaunee's `tribal_confederation` of landed tribes with one `currency_data`, the Burke feud's mutual rivals, and the theocracies of Tibet and Venda (the faith is not Christian); and the game's societal values are two-sided axes (a naval position gains sea trade and loses land trade). The survey also found why the other axes stay alone: `mercantilism_vs_free_trade` and `outward_vs_inward` hold an age.
- [V-EXEC C252] Generator 0.11.2, algorithm epoch 26: `rnw.archetypes` (who forms a sea league, a highland confederation, a fractured realm or a sacred centre, drawn once for every hearth's domain by the rare-empire chance), `rnw.eu5_archetypes` (the calibration from the installation, the lines, the checks), `hearth_domains`, landed tribes, `verify_archetypes`, report section `archetypes`, window texts (*Extraordinary peoples*). A chance of 0 is byte-identical to 0.11.1 (818 files, but `.metadata`). Exports at 1000 permille give each kind in some world and all four in continents 208; 31 worlds searched with the peoples stage alone; the reference world (`RNW1-0826C-SYW6B-MW73Y-C005G-40813-G0TQW-2Z`, 792 files, `7113a7f6…0662` under hash seeds 1 and 7) holds two confederations. `make check` (1,314 tests) and the 16 local tests with reproduction and layers pass. Installed as `rnw_exp_world_2r7bql6dk3` (continents 208 at 1000 permille).
- [UNKNOWN C253] The engine's verdict on a theocracy over a monarchy template, tribes of the plain template in a confederation, alliances and rivals at the start. Nothing is asked of the owner; the next session's `error.log` tells ([experiment 045](../../experiments/045-varied-societies/README.md)).
- Found on the way, not R7d's: seed 210 of the continents preset fails in `plan_identities` (IndexError: an area without provinces).
- No game launch by the agent, no push or publication.


## 2026-10-24 — The owner's sitting of 0.11.2 (045), logs read: C254-C256

- [V-GAME C254] The session (07:07 to 07:15, EU5 1.4.4, world `rnw_exp_world_2r7bql6dk3`) ran to 1341.8.12. The save holds the highland confederation (NGK, XUI, TQT) and a theocracy of NGJ. The guard of 0.11.1 (`common/scripted_guis/rnw_new_world.txt`, `country_exists = this` first) did not stop the 214 lobby errors at `:4`: the `is_shown` block raises them. C249's claim of the fix is wrong; the cause is inferred to be the lobby's `COUNTRY_SELECTED` expression (untested).
- [V-GAME C255] 27,573 vanilla map-mode errors, one burst at 07:09:54 (`scope:actor` none in `nobles_percentage` and `burghers_percentage`), not attributed to the mod or to a vanilla state.
- [V-GAME C256] The duplicate-key warnings of the mod's `replace/` localization against vanilla area and region names: which text wins is unknown.
- Fixed nothing: a lobby fix changes a mod file (a new epoch and reference world) and needs a short sitting to confirm; no game launch by the agent, no push or publication.


## 2026-10-24 — Sitting fixes and seed 210, 0.11.3, C257-C261

- [OWNER] “Исправь найденные проблемы”: the seed-210 crash and the lobby errors; the duplicate-name warnings of the same sitting are addressed alongside them ([046](../../experiments/046-sitting-fixes/README.md)).
- [V-EXEC C257] Reproduced seed 210 before editing the sea planner. `atlantic_north_equatorial_area` survived outside the canvas but lost every generated zone to the shore regions; an empty `_Area` reached `plan_identities`. The planner no longer emits a generated area with no members when its vanilla remainder supplies it. A typed validator rejects any other empty generated area or province. An eight-cell synthetic regression reproduces the two-anchor case; the complete seed-210 export now passes.
- [V-LOCAL / V-EXEC C258] `scripted_guis.info` documents saved scopes, and the installed GUI uses `GuiScope.AddScope` without a root. Country-selection queries now pass an optional saved country to a GUI without a typed root; it checks for the capital and enters it with `?=`. All country callers share this convention. The copied GUI anchors and emitted scripts pass offline checks. [UNKNOWN] The engine verdict; no assertion that an `Or` short-circuits.
- [V-EXEC C259] No extra localization file defines the reused American area/region keys. Instead their values change in locally derived files at the installed paths. Independent comparison of both exports finds 33 files each (three per language), original key multiplicities, unchanged BOMs/line endings and every byte outside the selected name values unchanged. The reference changes 167 American keys per language, seed 210 changes 168; no Old World key changes. Missing or ambiguous requested keys fail loudly. The localization check also rejects added, removed or duplicated keys in a same-path override and still checks new keys for hash collisions.
- [V-EXEC C260] A full test run exposed a completion race: the window could see FINISHED before its library held the new world. The worker now refreshes the library before publishing the terminal state/result; a deterministic thread-barrier regression verifies the ordering.
- [V-EXEC C261] 0.11.3, epoch 27. The reference world `RNW1-0826C-SYW6B-MW73Y-C005G-60813-G0WZ3-H9` has 814 files excluding metadata, digest `abc021ed0a1a9211efdd72b2696832601273a1c839db5cefa8d4a343ddf2b4c7`; the opt-in reference test under hash seed 7 reproduces it (136.52 s). Continents seed 210 at extraordinary chance 1000 (`RNW1-080G0-00000-00006-J005G-60813-BM0FX-JZYR`) completes in 147.2 s with 813 files, digest `650d92e74ea63ec7b08f823e6e05aa1f9f77c0f16dd792f614e0fcc44dcb2945`. The independent manifest checks pass; both exports preserve the outside-canvas pixels and lose no Old World contact. The installed fingerprint is unchanged, executable 1.4.4 build 26142040 on 1.4.3 data build 26105915.
- `uv sync --locked --group dev` and `make check` pass: 1,326 Python tests, 23 Rust tests, format, lint and typing clean. Read-only local suite: 14 passed, 2 slow opt-in tests skipped; the reference test is subsequently run separately and passes. The layer reroll test is not repeated: no layer ownership or random stream changed. Synthetic and real-world golden digests are updated. Interoperability register R-002 records the text interfaces touched.
- Installed **RNW: Continents BDI5**, `rnw_exp_world_bdi5rrmfyp`, as a new folder with all 815 files hash-identical to the candidate. Existing nine profile-root files retain hashes, and the 9,441 existing mod files retain sizes and mtimes; previous worlds and playsets stay. See [INSTALLED](../../experiments/INSTALLED.md). Local-only evidence is under `local_data/sitting-fixes/`.
- [UNKNOWN] The engine result of the new lobby scope and display-name overrides. C255's vanilla map-mode error is still unattributed; this work makes no claim about its cause. No separate owner sitting requested, no game launch, push or publication.


## 2026-10-24 — N5: region keys chosen by physical content (0.11.4, epoch 28)

Owner instruction: implement N5. Design, method, three-world audit and limits are in [N5](n5-region-keys.md); claims C262-C265 and [experiment 047](../../experiments/047-region-keys/README.md).

- [V-LOCAL / V-EXEC C262] Installation still has the 1.4.4 executable / Steam build 26142040 on 1.4.3 data, with the unchanged map fingerprint. N0's 68 positional consumers remain accounted for: 61 use land keys scored by N5, two only anchored sea areas and five individual locations.
- [V-EXEC C263] `eu5_regionkeys.py` reads installed physical templates and existing cell/contact tables; an exact integer assignment minimizes pixel-weighted climate, relief, coastal-share and relative-size differences. Regions stay inside their subcontinent and areas inside their original region; all child areas must fit. The reference's old weighted partition left Chaco three cells for four areas and dropped `moqoit_area`: unlabelled compact region parts now precede matching, preserving all 14 region and 135 land-area keys without output repair. No extra raster pass, resource or peoples dependency, random draw, GUI/shader change or new binary interface.
- [V-EXEC C264] Reference, continents seed 210 / extraordinary chance 1000, and archipelago seed 73 pass full export and independent manifest/hierarchy checks: total physical differences fall 18.91%, 22.26% and 22.20%, all 21,728 Old World location records and original land-key parents remain, no Old World contact lost or outside pixel changed. Individual keys can worsen under the global optimum and parent constraints; the audit records environmental mismatches instead of claiming historical twins. The reference's rasters, templates, resources and graphics match epoch 27 except its spline network, whose hierarchy indexes change; R-001 of the interoperability register records that follow-up.
- [V-EXEC C265] Locked sync and `make check` pass (1,344 Python tests, 16 skips; 23 Rust tests; formatting/lint/types clean). Read-only local checks: 14 passed, two opt-in skipped. Separate `PYTHONHASHSEED=7 RNW_REPRODUCE=1` reference reproduction passes (165.66 s). Two layer rerolls compare every mod file: resources change exactly one resources file; peoples change 62 owned files; both preserve all physical key records and the land, and respect story/exceptional-place ownership. Epoch-28 reference: 814 files, digest `a05a8d4a8fe252f683613fdbc0951e022f18c2c4cefd353ea9ed91ea16ef0b46`, pinned in `tests/golden_world.json`; synthetic epoch-28 goldens also recorded.
- Installed **RNW: Small continents 6RF2**, `rnw_exp_world_6rf2nzt4dv`, with all 816 files hash-identical to the audited reference. Nine profile-root files retain hashes and 10,256 existing mod files retain sizes/mtimes; all old folders and playsets remain. Exact removal in [047](../../experiments/047-region-keys/README.md) and installation in [INSTALLED](../../experiments/INSTALLED.md).
- [UNKNOWN] N5's engine and campaign results remain NOT-RUN. No game launch, separate owner sitting, push or publication. Local-only evidence: `local_data/n5/`.

## 2026-10-24 — Generator library: multiple selection and direct removal (C266)

- [OWNER] Asked for convenient, fast removal of a map-mod from the game and selection of several maps at once.
- [V-EXEC C266] The native library now accepts Ctrl/Shift selection and Select all, retains selection through refreshes and row rebuilds, and exposes counted Remove from game and Delete from library buttons below the list. The active world's Remove/Delete buttons also honour a multiple selection. Remove keeps the world's code and pictures; Delete confirms the selected recorded worlds once. Stray mods can join a removal, but are never mistaken for library records to delete.
- [V-EXEC C266] Removal takes an immutable snapshot of known installed folders and uses the existing installer safety checks. It works without the game installation. Library deletion also works without a profile, stops at a filesystem failure, and reports the failed name and completed count; errors are no longer silently swallowed by library.forget. Busy actions stay disabled. Existing files, saves and playsets were not touched by development or verification.
- [V-EXEC C266] `uv sync --locked --group dev` and `make check`: 1,349 Python tests pass, 16 local/opt-in skips, 23 Rust tests pass; formatting, lint and types clean. Five new synthetic tests include real Qt clicks and refusal/acceptance of bulk deletion. Inspected light/dark 1080-by-760 and dark 1440-by-900 window captures under ignored local_data/gui-library. Rebuilt dist/RandomNewWorld with packaging/build.py; package self-test and CLI help pass. Build log stays local. No generated-world changes, so version 0.11.4 and epoch 28 remain; changelog entry is Unreleased. This is an application update, with no game-facing candidate to install and no game launch or owner sitting requested.

## 2026-10-24 — Release architecture and Workshop terms (C267)

- [SOURCE C267] Read the Steam Subscriber Agreement as revised 2026-04-20, the Workshop submission page, the EU5 Steam listing and its linked Paradox User Agreement (updated 2026-01-21). Steam's general UGC terms grant Valve a broad licence, allow product-specific Workshop terms, and require uploaders to have sufficient rights. The EU5 listing points to Paradox's UGC terms, which include mods, scripts and programs and require free, non-commercial UGC.
- [UNKNOWN C267] The published terms do not resolve whether every file in the proposed hub has the rights needed for these grants, particularly where content incorporates EU5-derived material. Keep generated worlds local; owner/legal review is still required before uploading the hub.
- [V-EXEC] Added [release process](../release-process.md), linking the existing versioning, roadmap, legal, and artifact workflow gates into an internal checklist. No CI workflow, tag, release, Workshop item, or account was changed.

## 2026-10-24 — The probe mod is retired

- [OWNER] A third mod is too many: everything the game needs is built into the map's mod; the player enables the map only, and events and the rest are part of that same mod. There is to be no separate probe.
- [V-LOCAL] The probe `rnw_exp_probe_hooks` (0.4.0, 21 files) was research only: a formable of the tag `ZQP`, two test decisions that found subjects, start variables and a story start in miniature, all on vanilla tags. No world declared it as a relationship (`relationships` is empty in every installed mod) and nothing in a world's files refers to it. What it settled is already in the worlds' own mod: the formable of a mod-defined tag (C199), the start hook through `on_actions` (C206), the dynamic start and the delayed event (C199), keys the game looks up (C201).
- [V-EXEC] Deleted `src/rnw/eu5_probe.py`, the `probe-hooks` command, `tests/test_probe.py` and the two local probe tests; removed `rnw_exp_probe_hooks` from the owner's profile with `rnw uninstall-mod` (game closed; playsets and settings hash-identical) and `generated/rnw_exp_probe_hooks`. No generated output changed, so no version, epoch or digest moved.
- [UNKNOWN] C221 (whether the game's own colonization path gives a colony the scripted name) stays open and blocks nothing; if it is ever asked, it is asked from the console of a world mod, not by a mod of its own.
- Standing rule added to `AGENTS.md`: *One mod: the map*.


## 2026-10-24 — L1: how the game writes its languages (C268–C272)

- [OWNER] Finish L1: translate everything, improve the English while doing it, keep to EU5's style and keep the texts free of the marks of machine-written prose; record the observations and rules so that someone else can continue.
- [V-LOCAL C268–C272] Read the installed localization of all eleven languages (1.4.4 executable on 1.4.3 data): the game's language is Steam's per-game language in `appmanifest_3450310.acf`; the 6,167 American location names are transliterated in Russian, Japanese, Korean and Chinese and kept in Latin elsewhere; geographic names follow one pattern per language; country adjectives are stems in Russian and Polish and `-isch` adjectives in German; Russian declension of countries falls back to a generic noun for tags it does not know, so generated tags need nothing.
- [SOURCE] Marks of machine-written prose: Wikipedia's *Signs of AI writing* and Russian guides (Habr/Bothub, goodtarget, Skillbox), accessed 2026-10-24.
- Everything, with the rules for each language, the design (catalogs with source hashes, phrases rendered per language, rule-based transliteration) and the next steps, is in [localization](../localization.md). No code or generated output changed.

## 2026-10-24 — L1: the world's mod in every language (0.11.5, C273–C274)

- [OWNER] Finish L1: translate, improve the English, keep to the game's style, avoid the marks of machine-written prose.
- English first: the stories, formables and places were rewritten against the list in [localization](../localization.md) §3.2. The draft repeated one device (*they agree that something must be done, and agree on nothing else*) in two stories, the antithesis *X say A. Y say B.* five times, and used *some/others* where a person could be named; the narration now speaks in the country's voice where the game's own does, and several options are lines spoken at court rather than orders. Option order and effects are unchanged. `[ROOT.GetCountry.GetFlavorRank]` left one text: its grammatical gender varies with the rank, so no Russian, German or Polish sentence can agree with it.
- [V-EXEC C274] Translations into ten languages, written for each language's own conventions as the game's translators use them (Russian infinitive options and names in apposition, German plural imperatives, French first person plural, Brazilian Portuguese Title Case titles and third person plural, Polish infinitives, Turkish jussives with names only before a fixed noun, Japanese *da/dearu* narration, Korean *-습니다* narration with no particle after a name, Chinese full-width punctuation).
- [V-EXEC C273] Names: a rule-based transcription per script, measured against the game's own spellings; composed names are phrases rendered per language.
- [V-EXEC] `uv run pytest`: all tests pass; the local suite with `RNW_REPRODUCE=1` remakes the epoch-29 reference world.

## 2026-10-24 — L1: the generator's window in every language (0.11.6, C275)

- [V-EXEC C275] `gui/text.py` chooses the window's language (the player's, else Steam's per-game language from the app manifest, else the system's), and the `window` catalogs translate its 441 strings into ten languages. The generator's messages to the player moved to `rnw/messages.py`: `say(key, ...)` prints English for the command line and the log and lets the window write the message in its language. The atlas keeps names as phrases (format 2) and the window writes them in its language; with the game installed, cultures, religions, materials and lands show the game's own names (`app/gamenames.py`). A test makes the window in every language at 1,080 by 760 pixels.
- Found by looking at the captures: the estimate printed `30,871` in Russian; numbers are now grouped per language.

## 2026-10-24 — L1: the Workshop description in every language (C276)

- The English draft gained one line (the generator speaks the game's languages and starts in Steam's); the translations in `docs/workshop/<language>.md` use the window's words for its controls and the game's for its interface (§2.9 of [localization](../localization.md)), and keep our bracketed notes in English for the editor. `tests/test_workshop.py` checks each against the fingerprint of the English draft, its notes, links, paths and sections.
- [V-LOCAL C276] The mod metadata a mod list shows has no language field: beside `short_description` the executable's printable strings name only `name`-level fields of one language (`supported_game_version`, `relationships`, `game_custom_data`, `provider_id`, `rel_type`, `resource_type`); `localized_name` belongs to the modifier types. The hub's and the worlds' titles and descriptions stay English; how a Workshop item's own title and description per language reach the in-game list is [UNKNOWN] until an upload ([interoperability](interoperability.md) R-003).

## 2026-10-24 — the Workshop page for players (C277)

- [OWNER 2026-10-24] Asked for the Workshop description to read as EU5 mod pages on the Workshop do, not as a repository: what a player needs to know, sections with icons, a FAQ and links at the end.
- The text is now Steam's markup, ready to paste (`docs/workshop/<language>.bbcode`), with an emoji per section: what a world holds, quick start, the window's choices, why a program, good to know, FAQ (seeing the map first, native countries, other mods, multiplayer, Ironman and achievements, worlds without the generator, Windows warnings, Linux and Steam Deck, removal, bug reports with *Save diagnostics*), links. Unverified answers keep bracketed notes (`[Until tested:]`, `[Confirm in the release sitting.]`).
- [SOURCE C277] Steam's limit is 8,000 bytes, not characters: the first Russian translation was 9,316 bytes and was rewritten more tightly (7,885). The English lost a few clauses so that the others fit with room to spare. `tests/test_workshop.py` now compares markup and links in order, the notes, and the byte size.

## 2026-10-24 — Installed the 0.11.6 generator hub (C278)

- [V-LOCAL C278] The EU5 profile's `rnw_exp_hub` held version 0.9.14. The installed game manifest is build 26142040.
- [V-EXEC C278] Built the 0.11.6 Windows wheel from the current checkout and assembled a hub with the twelve runtime versions already present in the local 0.9.17 hub artifact; they match the current lock. The package inventory and game-file boundary checks passed; all 3,247 installed files match the prepared candidate. A separate generated-world folder is present after the update and was not its target.
- [UNKNOWN C278] No game was launched; the rebuilt launcher has not been newly exercised through the game's Open in folder flow. No generated-world output changed, so the algorithm epoch and golden digest did not change.

## 2026-10-24 — Stable generation progress and live ETA (C279)

- [OWNER] The progress panel's wrapped stage description made the window height jump; the ETA should reflect the measured stage shares and adjust to the player's current pace; the world list and progress bar should agree on the displayed percentage.
- [V-EXEC C279] The stage line and ETA each use a fixed one-line height, and the full stage line remains available as a tooltip. The ETA starts from the 120-second midpoint of the documented 90-150-second reference run, interpolates the active weighted stage, and recalibrates against this run's elapsed time and weighted progress. The ten non-English window catalogs include the ETA text with current English fingerprints. Both progress displays use one rounded integer percentage on a 0-100 scale.
- [V-EXEC C279] `ruff format --check` and `ruff check` pass. The full Python suite passes (1,431 passed, 14 skipped); Rust formatting, clippy and tests pass (23 tests). `make check` stops at basedpyright: in this environment it selects Python 3.14 instead of the project's Python 3.12 and cannot resolve PySide6 and other packages. No generated-world files changed, so the version, epoch and golden digests stay unchanged.

## 2026-10-24 — Feasibility of a wider New World canvas (C280–C281)

- [OWNER] Asked whether a fixed New World sector can extend into nearby oceans, preserve important islands and retain the names of surviving oceans, including reuniting retained and generated parts.
- [V-LOCAL / V-EXEC C280] Rediscovered the installed game (manifest 26142040) and rehashed its map contract: unchanged `592e8309b7ed9bef1cc0df3eaccd798896d75cd3c3d7ecf9ed525bb6aca3009a`. Audited `select_canvas` at the preset 1,600-pixel band. The four large Pacific/Atlantic wastelands in the assessment all contribute zero pixels because their remainders have multiple large components; the initial proposal includes 11,711,292 of their pixels. The final current canvas is 37,978,627 pixels. Counts, script and diagnostic raster remain ignored under `local_data/canvas-expansion/`.
- [V-EXEC / INFERRED C281] Recorded [the assessment](canvas-expansion.md): the core accepts arbitrary domains, but a wider fixed envelope needs deliberate handling of disconnected vanilla remainders and named ocean locations. Reusing the ocean's area is distinct from retaining its named location; passable coasts and lanes stay separate from closed water. A wholly consumed ocean must not force a water reservation back into the world. The cover at country selection also paints water, so the screenshot is not treated as a measurement of actual land.
- [UNKNOWN] Expanded-world export and engine behaviour remain untested. Documentation only: no version, epoch, golden digest, installed mod, profile, launch or owner sitting.
- [V-EXEC] Locked offline sync, audit assertions, `git diff --check` and 53 existing canvas/New World/seas/names/lanes tests pass. `make check` passes format and lint, then stops at the previously recorded basedpyright interpreter-discovery problem (Python 3.14; unresolved Python 3.12 packages); no full-suite pass is claimed.


## 2026-10-24 — Optional ocean expansion, 0.12.0 / epoch 30 (C282–C285)

- [V-EXEC] At the owner’s request this completed phase was renumbered from 0.11.7 to 0.12.0 before publication and its commit amended. The epoch stays 30, the reference code carries 0.12.0 and its 816 map files keep the same digest. Locked sync, `make check` and the rebuilt package self-test pass again.

- [OWNER] Approved implementation, then requested both approaches with a recommended ocean-expansion checkbox. Expanded is the default; original remains available and older codes select it when the flag is absent. Sketches, templates and rerolls respect the flag, translated with its recommendation in every official window language.
- [V-EXEC C282–C283] The fixed sector increases the domain from 37,978,627 to 53,240,944 pixels. Closed-ocean remainders are row runs, and the identity planner joins connected retained/generated water before serialization. Other components retain the original name through new keys. The final cap includes new remainder identities. No engine patch or post-export repair. [Design and counts](canvas-expansion.md); [R-004](interoperability.md) records the binary interfaces now regenerated over the larger domain.
- [V-EXEC C284] Regressions exposed a short crossing through two sea zones, excessive location counts in the larger canvas and the coastal-discovery list's assumption that Aridoamerica always has a coast. Their planners/explicit N0 decision now produce valid data. A trailing partial lake-transform record is rejected instead of silently discarded. Default spacings and separate budget coefficients are recorded in the design.
- [V-EXEC] Four complete exports and independent file/raster/hierarchy/contact/port audits pass: the expanded reference, continents seed 210, archipelago seed 73 and original-mode continents seed 210. 21,728 protected hierarchy records and 66,634,570 protected map pixels survive. Changed/new expanded closed locations are connected; the old Arctic port omissions remain on the same old contacts, including a small renamed Chukchi remainder. High-land seed 99 passes the physical checks at 29,098 locations against an estimate of 29,340. Full per-world counts and digests are in [049](../../experiments/049-ocean-expansion/README.md).
- [V-EXEC] Locked sync and `make check` pass: 1,445 Python tests, 14 skips, 23 Rust tests, formatting/lint/types clean. Explicit Python 3.12/.venv configuration resolves the earlier basedpyright discovery issue; its only remaining pre-existing complaint, a test's intentional private clock access, is annotated. Read-only local suite: 12 passed, 2 opt-in skips. Separate reference reproduction under hash seed 7 passes in 163.32 s. Golden record: 816 files, digest `5a5f4ed95144b0a30ce71a0ea32aa3ec5161ddbabc9579f6127a7858031464ab`. Linux folder build, self-test and CLI help pass; the Russian checkbox was rendered and clicked, and all language layout/catalog tests pass.
- [V-EXEC C285] Installed RNW: Small continents NDIW as a new `rnw_exp_ocean_release` mod, 818 hash-identical files, and updated the 0.12.0 hub, 3,254 hash-identical files. Nine profile-root hashes and 796 existing non-hub mod file sizes/mtimes are unchanged. All twelve runtime packages now match the lock. Correction to C278: the old hub's Pillow was 12.3.0 while the lock specifies 13.0.0; the exact cached Windows 13 wheel was available, so no download was needed. Source-wheel equality and package inventory/game-file-boundary checks pass.
- [UNKNOWN] Expanded-world engine behaviour and the rebuilt hub's Open in folder flow remain untested. No EU5 launch, owner sitting request, other mod/playset change, push or publication. Local artifacts and audit scripts stay ignored under `local_data/canvas-expansion/`, `generated/` and `build/`.


## 2026-10-25 — Recurring islands near Japan: seeded land-field origin (C286–C287)

- [OWNER] Requested that the former-Alaska part of the New World have no compulsory near-identical island: random islands there are welcome.
- [V-EXEC C286] Inspected the shared land threshold, canvas, seam guard and retained American land: no per-region quota or preserved American land. The land-noise lattice did have a fixed origin, with a measured synthetic node/centre variance ratio of 4.2385; [INFERRED] that biases shapes at fixed positions in the clipped lobe. One seeded stream origin across many periods removes that spatial anchor; the ratio is now 1.0822. Three of sixteen synthetic lobes stay entirely ocean; the other seeds vary. Strip equality and independent native/reference comparisons cover the new origins. The land budget and canvas policies are unchanged.
- [V-EXEC] 0.12.1 starts epoch 31, updates synthetic goldens and makes the installed candidate: 814 non-metadata files, digest `d07aed4acb7690f15d70bed95ba6e1ff30d8f11c29e2be8c169cd9fb9172da15`. Full export: 163.4 seconds. Independent written-file auditing preserves all 21,728 protected hierarchy records, 66,634,570 protected pixels and retained Old World contacts; ports and changed closed-ocean components pass. Binary-writer follow-up in [R-004](interoperability.md), detailed record in [050](../../experiments/050-seeded-land-origin/README.md).
- [V-EXEC] Linux and packaged Windows offscreen self-tests pass. Installed the reference in new `rnw_exp_seeded_land_release` (816 files) and the generator in new `rnw_exp_generator_0121` (3,254 files), both hash-identical to their candidates. The existing hub and all existing worlds are preserved: 8,044 mod-file size/time records and nine profile-root hashes unchanged.
- [UNKNOWN] In-game rendering and campaign result for epoch 31. No EU5 launch, owner sitting request, push or publication. No derived asset, raw report, log or screenshot is committed.
- [V-EXEC] The initial candidate reproduces exactly under hash seed 7, but its all-story-family reference assertion fails: no holy site is placed and the sacred-centre story is correctly absent. Peoples roll 1 also lacks it. Planning roll 2 finds three holy sites and all families; the ordinary export becomes the new epoch-31 reference, code `RNW1-0826C-SYW6B-MW73Y-C0060-20813-G126N-VS`, 815 non-metadata files, digest `a6a257f4a26137539ec128481093ed9129d38e34ddea0b863e4df41c552b20ad`. All 667 map/graphics files match the installed candidate. The reference stays uninstalled; no production fallback, story-eligibility change or probe mod. `make check` passes 1,862 Python tests (14 skips), 23 Rust tests, format/lint/types; 12 read-only installed-game checks pass.
- [V-EXEC C287] The final reference reproduction test passes under `PYTHONHASHSEED=7` in 152.48 s, including every story family and the exact 815-file mod digest. The original coverage assertion is unchanged.


## 2026-10-25 — Main installed generator updated to 0.12.1 (C288)

- [OWNER] “Собери в игру”: install the correction in the main game-side generator.
- [V-EXEC C288] Prepared the canonical `rnw_exp_hub` from the verified 0.12.1 Windows package, changing only its candidate metadata back to the standard hub identity. Wheel/source equality, locked runtime versions, executable inventory and game-file exclusion pass. Updated the existing installed hub from 0.12.0; all 3,254 files match the candidate and metadata/package versions agree. The installed window/native/world-code self-test passes under isolated Wine.
- [V-EXEC C288] Backed up the prior 3,254-file hub outside the profile and verified all hashes before replacement. All nine profile-root hashes, 3,254 other-mod size/time records and both existing mod folders survive. The separate candidate generator is preserved. Detailed installation and removal record: [INSTALLED](../../experiments/INSTALLED.md). No algorithm/source/version change, world regeneration, library/save/playset edit, EU5 launch, push or publication.


### 2026-10-25 — Correct the map-wrap division (0.12.2, epoch 32)

[OWNER report; generator installed: 0.12.1] Four worlds all had land near Japan; no continent continued
through the other map edge. [V-EXEC C289] The previous noise-origin fix left an
explicit 24 px seam channel and coast ramp. Removed that workaround from all
land paths, corrected horizontal terrain halos and crop-coordinate fine noise,
continued water distances/blur/detail and road contacts across the cylinder.
C56's engine attribution was an inference, not an established limitation; the
historical crack remains observed and the new engine rendering remains [UNKNOWN].

[V-EXEC C290–C291] Whole/rolled synthetic continents decode to identical height
and material pixels; full checks pass (1,881 Python, 14 skips, 23 Rust). The full
candidate has one 2,109,356-pixel passable landmass crossing 1,297 seam rows and
74 wrapped roads. Independent read-back protects 21,728 Old World records and
66,634,570 pixels. Updated the main Windows hub to 0.12.2 with a verified backup,
added one new world and preserved the profile and all previous mods. The installed
self-test passes and new Windows/Linux wrap sample digests agree. See
[051](../../experiments/051-wrap-continuity/README.md), the ledger and the
interoperability register; raw files stay local. No EU5 launch or manual sitting.

[V-EXEC C292] All four owner presets share one seed; their exact land parameters
now produce seam-crossing landmasses, including the 27,440,633-pixel supercontinent.
The epoch-32 reference uses peoples roll 3 for complete story/formable coverage,
with 651 map/graphics files identical to the installed candidate. A fresh no-cache
hash-seed-7 reproduction passes in 160.12 s, and 12 read-only installation tests
pass. The reference digest is pinned in `tests/golden_world.json`.


### 2026-10-25 — Physical seam and comb-shaped coasts (0.12.3, epoch 33)

[V-GAME owner C293] The 0.12.2 supercontinent has a physical crack and regular
straight coastal teeth. [V-EXEC C294] The shared noise kernel interpolated a
3,600-pixel octave with only 256 fractions; corrected to 65,536 before thresholding.
[V-LOCAL/V-EXEC C295] The terrain shader's half-open decal bounds also omit the
world endpoint and outside halos. Eight periodic placements reuse opposite-edge
heightmaps in both cached and source-instance records. Synthetic geometry tests
supply the missing sources without new interior overlap. Exact CPU admission and
candidate rendering remain [UNKNOWN]; limited read-only static inspection did not
establish them. No engine patch or agent game launch. See
[052](../../experiments/052-physical-seam-and-coasts/README.md) and the R-004 follow-up.

[V-EXEC C296] Release checks pass (1,888 Python, 14 skips, 23 Rust), plus 12 local
read-only tests and a fresh no-cache reference reproduction (194.02 s). The owner's
observed seed/shape becomes the epoch-33 reference (824 files, digest in
`tests/golden_world.json`). Independent read-back preserves 21,728 Old World records
and 66,634,570 pixels; 40,960 boundary/halo source checks pass. Installed main hub
0.12.3 and only the new **Supercontinent MKEA** world, with verified backup and
preservation of the old/active world and all profile roots. Installed Windows
self-test passes; precision and both synthetic digests agree across platforms.
The candidate's actual seam appearance remains unknown, not a claimed game pass.


### 2026-10-25 — Reinstall the requested world

[V-EXEC C297] At the owner's explicit request, restored the missing
`rnw_exp_physical_seam` (**RNW: Supercontinent MKEA**, 0.12.3) into the game profile.
All 826 files match the verified export manifest. Nine profile-root hashes and
6,528 existing mod-file size/time records are preserved, including the retired
old world; no sweep, game launch or playset/save/library change. See
[installed list](../../experiments/INSTALLED.md) and ignored `reinstalled.json`.


### 2026-10-25 — TR46 long observer campaign: documentation only

[OWNER] Record all seven reported problems and inspect the latest long-game logs;
no fixes now. [V-LOCAL/V-GAME logs C298] Identified **RNW: Continents TR46**, code
`RNW1-040XN-DR20S-1RQ4T-Z0060-602JM-HB0`, generator 0.12.3 / epoch 33,
EU5 1.4.4 / Steam build 26142040. Session 04:03:47–07:01:39 reaches 1590.11.11,
saves and exits normally. Preserved logs, three screenshots, two unchanged
campaign autosaves and selected world files under ignored
`local_data/tr46-observer-20261025/`; all 807 world files are hash-inventoried.

[V-GAME owner C299] The [TR46 register](tr46-observer-audit.md) retains the seven
owner observations as stable work items, splitting the seam appearance from
the colonial east/west and wrap-policy question. Each has evidence, unknowns,
code/data entry points and closure criteria. The three screenshots belong to
Chukotka remnants, not the seam or mountain complaint. Experiment 052 now links
the subsequent report that a different 0.12.3 world's crack persists.

[V-GAME logs C300/C302] Added twelve diagnostic groups, including five missing
river sources (698 pixels), the nonfatal port/water assertion, unreachable
western-voyage waypoints, AI/script errors, treaty text, malformed country names,
GVQ's setup relation budget, locators and presentation/environment failures.
The [catalog](tr46-log-catalog.md) accounts for all 2,366 current error records
(61 origins) and 57,352 AI warnings (42 command/stage categories), without
counting mirrors twice. [V-EXEC C301] Starting-name matches show 137 native
attacking declarations but none of the 210 colony starts. Growth, extraordinary
archetype behaviour and comparison with vanilla remain unknown.

[V-LOCAL C303] Excluded the stale event CSV, earlier rotated errors and earlier
crash from campaign attribution; recorded missing-DLC/startup background and
eight additional Workshop VFS mounts as confounders. No fixes, game launch,
probe, mod installation, save/playset change or new manual sitting. Version and
epoch remain 0.12.3 / 33 because only documentation changed.

[V-EXEC] Locked development sync and the complete project check pass with a
writable temporary uv cache (the default home cache is read-only in this
sandbox): 1,888 Python tests passed, 14 skipped; 23 Rust tests passed; formatting,
lint and types clean. Evidence inventories, log counts and documentation links
are checked separately; these checks do not close the recorded gameplay issues.


### 2026-10-25 — TR46 boundary investigation and offshore-coast correction (0.12.4)

[OWNER] Proceed with related work until an important product choice is needed
or the next task is independent. [V-LOCAL C304] Rechecked the current installation:
unchanged map fingerprint, 1.4.4 executable on 1.4.3 data. Vanilla American land
exists at both raster edges, including Aleutian/Bering islands. [V-LOCAL
executable / INFERRED C305] Limited read-only tracing of `CIsEastOfTrigger` shows
map-span comparisons in both coordinate directions, so a purely linear
right/left interpretation of the colonial division is unsupported. Exact treaty
line/runtime locations and the numeric span remain unknown; no treaty is patched.

[V-LOCAL/V-EXEC C306] Found the Chukotka remnant's written-data cause: the old
island's offshore visual footprint lies outside its location mask. Height and
material inputs now include their coast support in original water; water colour
and foam include changed distance/blur support. Retained land stays exact and
no location/hierarchy/gameplay identity changes. This is the initial field domain,
not an output repair layer. Added removed-island rim, protected-land, wrap and
adjacent-decal regressions; band/strip equality tests pass. Version 0.12.4,
epoch 34, new synthetic goldens and reference world recorded; no engine/shader
change or generated-asset distribution.

[V-EXEC C307] Full check passes: 1,896 Python tests, 14 skips, 23 Rust tests;
clean formatting/lint/types. The 824-file reference has digest e36228d2…f769a6
and all story/formable families; a fresh hash-seed-7, no-cache local run passes
13 tests with one skip in 193.36 s. The exact TR46 seed becomes **Continents
56AP**, 825 nonmetadata files, b8a8417d…8a853. Independent read-back changes ten
common files (two northern edge height/material layer pairs and two water DDSs),
keeps 19,950,952 retained land samples exact and lowers all 19 previously
above-shore samples among 5,850 changed off-canvas water height samples.
All 853 bundle entries hash correctly. The Windows hub and native/coast sample
match the Linux source and field hashes and pass the isolated offscreen self-test.

[V-EXEC C308] Installed the new 827-file world `rnw_exp_tr46_coast` and updated
the main 3,254-file hub to 0.12.4, with a checked external old-hub backup and no
retired sweep. Nine root hashes, 4,061 other-mod size/time records and all three
prior folders remain. No save/playset/library change, EU5 launch or new sitting.
See [054](../../experiments/054-tr46-coast-footprint/README.md),
[installation record](../../experiments/INSTALLED.md) and the R-004 follow-up.

The map crack remains open. The serialized original TR46 river raster has six
source-less edge fragments; five sizes match the game's loading errors. River
network validation before world placement cannot settle the final serialized
pieces. Continuing this boundary work depends on the important policy choice
presented to the owner: preserve full mainland wrap and support its rendering /
river serialization, or prohibit generated land crossing and change world shapes.
The coast correction does not depend on that choice and has been completed.


### 2026-10-25 — Mainland wrap policy and river serialization (0.12.5)

[OWNER] Preserve full mainland crossing through the seam and correct its support.
This supersedes the pending policy question at the end of the previous entry;
no seam strait, mainland exclusion or treaty patch is authorized by this choice.

[V-LOCAL executable / V-EXEC C309] Limited read-only tracing of the installed
river-component discovery routine checks neighbouring coordinates against the
raster bounds instead of wrapping. It counts green markers in each discovered
component and reports zero or multiple starts. The original TR46 raster has six
source-less edge fragments; five sizes (107, 502, 65, 16, 8) match the campaign
errors exactly. The sixth (48 pixels) has no matching message and remains an
explicit attribution limit. No executable/process/installation is changed.

[V-EXEC C310] The adapter now serializes affected continuous trees into planar
drawing fragments before writing rivers.png. Each fragment receives one leaf
start and valid tributary markers; uncut networks retain their bytes. Sparse
traversal only visits networks contacting the seam, and palette writes use
strips. Hydrology, width classes and carved valleys stay continuous. Isolated
points cannot draw a line and are explicitly counted, not turned into a new
spring or rerouted river. Invalid topology fails loudly. Version 0.12.5, epoch 35.

Verification and installation are recorded in [055](../../experiments/055-wrap-river-raster/README.md).
The separate terrain-render crack stays open; this river phase makes no claim
that the engine draws the seam correctly.

[V-EXEC C311] Full check passes: 1,949 Python tests, 14 skips, 23 Rust tests;
format/lint/types clean. Exact TR46 changes only rivers.png at 12 markers, keeps
all 792,805 channel pixels and gives every one of 716 planar components one
start. All 853 bundle manifest entries hash correctly. The 824-file reference
is reproduced fresh with hash seed 7/no cache: 13 local checks pass, one skips
in 236.01 s. The Windows hub matches source and locked dependencies; its
offscreen self-test and 180-position river parity with Linux pass.

[V-EXEC C312] Installed R7SE in new rnw_exp_tr46_rivers (827 files) and updated
the main hub 0.12.4→0.12.5 (3,256 files), preserving the old hub externally and
in the retired area without sweeping it. Nine root hashes, 8,142 other-mod
size/time records and five prior directory entries are unchanged. A later owner
session has an unterminated log but no live EU5/Wine process; its logs were
preserved separately, not substituted for frozen TR46. No launch, save/playset/
settings/library change or publication.


### 2026-10-25 — Periodic support in primary terrain sources (0.12.6)

[V-LOCAL / INFERRED C313] Retained the owner's mainland-wrap decision. Installed
shader inspection separates its half-open source test from the clamped in-world
decal-grid lookup; earlier periodic-placement tests did not prove CPU admission.
The interface explicitly supports non-power-of-two source dimensions. Exact
admission and the cause of the rendered crack remain unproved; no new engine
trace/patch, game launch or manual sitting is used to claim otherwise.

[V-EXEC C314] Each of eight edge primaries now includes 512 location pixels of
periodic support, with matching 9216×4096 source size, cached geometry and the
existing active instance. The primary centres stay inside the map and their
bounds overlap its edge grid cells. Outside-only copies are removed. Initial
band synthesis covers the support and any periodic noise cut; only in-world
material cores enter the final world raster. Layer header/sample mismatch and
unexpected geometry fail loudly. No full-map repair, added blend layer or
geography restriction. Version 0.12.6, epoch 36; updated synthetic/reference
goldens and interoperability R-004.

[V-EXEC C315] Full check: 1,956 Python tests pass, 14 skip; 23 Rust tests pass;
format/lint/types clean. Independent KUIG read-back preserves 536,870,912 original
level-zero height/material samples, verifies 67,108,864 opposite-edge support
samples and all 861 bundle entries. All changes are terrain2 paths: 25 changed,
16 added, eight outside-only copies omitted. Every nonterrain file is exact,
including the corrected rivers. Sixteen primaries, eight padded, give unique
coverage at boundary vertices and tested ±1536-unit halos. Windows/Linux layer
bytes and the offscreen self-test agree. The reference retains all content
families (832 files, 2bebfb66…c0f8dc); KUIG has 833 files, 9b5a912e…15c3d2.
Rendered disappearance of the crack, CPU admission and every engine LOD remain
unobserved; larger source dimensions naturally change the mip pyramid. See
[056](../../experiments/056-primary-terrain-wrap/README.md).

[V-EXEC C315] A fresh, no-cache reference reproduction with hash seed 7 passes
13 local installation checks with one skip in 210.43 s.

[V-EXEC C316] Installed KUIG in new rnw_exp_tr46_terrain (835 files checked)
and updated main hub 0.12.5→0.12.6 (3,256 files). The previous hub is externally
backed up and retained without a sweep. Nine profile-root hashes, 12,223 other-
mod size/time records and six prior directory entries remain exact. Log and
live-process checks agree that EU5 is closed. No existing world/save/playset/
settings/library modification, launch, process control or publication.

The boundary block now has documented offline corrections for the removed
coast, river serialization and primary terrain support, with the owner choosing
full mainland wrap. The rendered crack/coast and exact treaty allocation retain
their explicit engine-evidence limits. The next independent work block is
maritime basin identity/routes/ports (TR46-03/04, L02/L03), using the frozen audit
and the separately preserved later session where relevant.

## 2026-10-25 — TR46 maritime geography (0.12.7 / epoch 37)

[V-LOCAL / V-EXEC / INFERRED C317] Reconstructed a concrete five-name closed-ocean
chain: the 48-cell quota split one connected stretch and coastal-area naming
assigned unrelated ocean names. Global lane reachability also allowed large
local detours, including northern pairs whose route through retained water was
roughly 20–24 times the short water route. They were not globally unreachable.
Vanilla itself has adjacent distinct closed waters, so adjacency alone is not
an error. All three remapped western-voyage landfalls lack ports; the existing
one-based definition-index contract maps the two failed log IDs to two of them.
The original VFS confounder and runtime-mapping inference are retained. Limited
static inspection of the separate port/water assertion gives no runtime caller
or location, so L02 stays unattributed.

[V-EXEC C318] Add local water connections within six typical sea-cell widths
with a maximum twofold geometric detour, continue retained navigable contacts,
and fold connected closed water without size partitions. Shared script remapping
retains port and navigable-water roles, consistently in waypoints and callbacks;
missing compatible destinations fail. No output repair or engine patch. Version
0.12.7, epoch 37; updated reference and synthetic digests. Existing text/PNG and
spline interfaces are covered in the interoperability register.

[V-EXEC C319] Complete check passes 1,962 Python tests (14 skipped) and 23 Rust
tests, with clean format/lint/types. Independent final-file audit validates all
3,700 local pairs (max factor 1.90849), 29 opened cells and 20 literal sea-voyage
waypoints. No adjacent generated closed identities differ arbitrarily. Terrain,
water textures, rivers, nonempty population records and all 59,404 road strips'
coordinates remain exact. All 50,987,808 nonsea pixels retain their keys, including
30,434,666 retained pixels with exact RGB. Recolouring affects 25 generated
land/lake identities but not their geography; country setup changes only sea
areas discovered. All 861 bundle records hash correctly. BU2A: 833 files,
9bea353c…1746e. Reference: 832 files, 2cccf2b2…e770f, all content families; fresh
hash-seed-7/no-cache reproduction passes 13 local checks, one skip, 220.16 s.
Windows/Linux maritime/access parity and the isolated offscreen self-test pass.
Engine appearance/navigation/voyage outcomes remain unknown; other expedition
lifecycle problems remain open. See [057](../../experiments/057-local-sea-routes/README.md).

[V-EXEC C320] Installed BU2A into new rnw_exp_tr46_maritime (835 files) and
updated main hub 0.12.6→0.12.7 (3,258 files). The old 3,256-file hub is checked
in an external backup and retained without a sweep. Nine root hashes, 16,314
other-mod size/time records and seven prior directory entries remain exact.
Both log and live-process checks say EU5 is closed. No existing world/save/
playset/settings/library edits, launch, process control or publication.

The maritime block has offline corrections and explicit remaining evidence
limits. The next independent block is impassable-land grouping and physical
mountain relief (TR46-01/02); they still require separate evidence and have not
been implemented in this phase.

## 2026-10-25 — TR46 impassable locations and mountain relief (0.12.8 / epoch 38)

[V-LOCAL / V-EXEC / INFERRED C321] TR46's 668 impassable samples form ten land
components, the largest fragmented into 252 locations. Vanilla Siberian units
already cover hundreds of thousands of pixels but differ in biome; exact
Paradox authoring rules remain unknown. The fine mountain-height role is also
missing: vanilla adds thousands of ordinary eroded height stamps, while RNW
removed the former American placements without supplying their equivalent role.
Primary-only height statistics are not final vanilla rendered heights. Identity
fragmentation and missing fine relief are separate causes and tests.

[V-EXEC C322] Contract compatible connected impassable samples before hierarchy
partitioning, retaining physical relief/drainage and every biome distinction.
The graph expands again for connectivity checks. Primary terrain synthesis now
samples local vanilla mountain height sources in integer, continuous crop
coordinates, with bounded overlap, elevation gain and zero contribution on river
lines. Padding samples the same mountains across the seam. Increase the band
working-set allowance for the new arrays. No new format, shader/engine change,
output repair or companion mod. See [058](../../experiments/058-impassable-highlands/README.md)
and interoperability R-004.

[V-EXEC / INFERRED C323] LSI3 has 88 connected compatible impassable locations;
the largest is 426,155 pixels. Independent read-back checks 570,425,344 source
height samples including padding: 12,103,913 rise, maximum addition 13,099,
maximum final height 52,690; none fall. Outside-domain, river and low samples,
materials/water textures/river PNG, retained RGB and all 59,404 road paths are
preserved. All 861 bundle entries hash correctly; 76 nonmetadata files change.
Native regional-family matching responds to the changed hierarchy: generated
culture/religion, diaspora, names and dependent start data can change. Retained
population records remain exact; this is not an isolated civilization-AI trial.
The local same-scale height plot shows sharper crests, not engine rendering.

Final `uv sync --locked --group dev && make check`: format/lint/types clean,
1,951 Python pass, 14 skip, **18 failures** in the unchanged Workshop description
files/tests from separate commit `0735263` (ten stale source fingerprints, eight
over the byte limit). No green full-suite claim; unrelated text work is not
mixed into the map change. Separate Rust format/clippy/tests pass all 23 tests.
Reference: 832 files, 711a0e02…c88800, all content families; fresh hash-seed-7/
no-cache reproduction passes 13 local checks, one skip, 248.40 seconds. LSI3:
833 files, 69cafca4…1b6392. Windows/Linux four-case parity and the final isolated
offscreen generator self-test pass. Final game appearance remains unknown.

[V-EXEC C324] With EU5 closed, installed LSI3 as new rnw_exp_tr46_highlands,
835 checked files, and updated the main generator 0.12.7→0.12.8, 3,262 checked
files. The prior 3,258 files are externally backed up and retained without a
sweep. Nine root hashes, 20,405 other-mod size/time records and eight prior folder
entries remain exact. No existing world/save/playset/settings/library edit,
launch, process control, push or publication.

The related TR46-01/02 block has an offline candidate and recorded runtime limits.
The next independent block is native expansion/colonization eligibility (TR46-05),
using the frozen original campaign as its evidence, not a new long playthrough.

## 2026-10-25 — TR46 native expansion and the saved vanilla rule (059)

[V-LOCAL / V-EXEC C325] Inspect installed colonization rules, defines, advances,
frontier cabinet action and neighbouring-conquest planner. Vanilla defaults to
western_colonisation_only with europe as its allowed capital continent. Frontier
settlement is a separate geographically gated mechanism; only 89 of 202 starting
TR46 states meet its geographic part, neither empire nor any league member.
Other eligibility and the engine's frontier-rule interaction are not inferred.
The installed American start has 223 states, 321 pop countries and 493 of 4,434
passable locations owned, versus TR46 202/457/738 of 6,656; both about 11.1%,
not an equal-area/population or control-campaign comparison. The current
installation remains build 26142040 with map fingerprint 592e8309…03009a.

[V-EXEC C326] Read both frozen saves without launch or mutation; ZIP CRCs and
original hashes pass. A private fail-on-unknown token reader consumes 68,108,132 /
75,749,957 tokens with balanced containers. Dates: 1497.4.1 / 1590.11.11. Validate
30,565 definition IDs, 201 retained original start capitals, 738 initial native
ownership records and all 2,653 / 2,619 current country lists against independently
counted location owners. QDL needs an explicit civil-war successor binding;
WBU/LIA preserves its original object separately from a civil-war copy. Saved
histories omit some current transfers (172 / 102 disagreements, 23 native in the
earlier checkpoint); do not derive exact lifetime peaks or event causes. Register
the narrow read-only interface in interoperability R-005; raw data/helpers stay
ignored under local_data/tr46-expansion.

[V-EXEC C327] Both saves use the vanilla western-only rule and native capitals
remain American. All nine actual extraordinary member countries have colonies
researched. The empires grow 53→98→121 and 86→119→142; WBU 7→69→149, becoming
LIA. The league loses all land. The ordinary-state cohort consolidates from 193
landed states/563 locations to 50/387 and 36/314; every original state together
holds 738→710→733 locations, with land in 202→54→40 countries. The 457 original
pop countries keep that type and own no land at either checkpoint. No native
active charter among 10/16 globally, no active frontier action globally, no
acquisition outside initial native state land in current holdings or recorded
histories. Keep the history and vanilla-control limitations. Record every actual
archetype's land/direct subjects and all 659 rows privately; public aggregate
findings: [TR46 native expansion](tr46-native-expansion.md).

[V-LOCAL / V-EXEC / INFERRED / UNKNOWN C328] No blanket expansion failure is
established; no AI/technology/rule/balance change follows. Frontier selection,
vanilla-normal growth and league resilience remain explicit unknowns. L07 now
has a known archetype: GVQ is in the three-member league. Its two alliances are
not a capacity guarantee because vanilla upkeep varies. Correct that source
comment only; the conditional DIP-0 setup warning does not establish actual
starting ruler overcapacity or explain defeat. This is an evidence phase, no
game-facing candidate to install, version/epoch stay 0.12.8/38. Required sync and
make check pass: 1,969 Python, 14 skips, 23 Rust, format/lint/types clean. Separate
Workshop fix 90f531e landed before this check; 058's prior failures remain a
historical result. No profile/save/settings/playset/install change, game launch,
process control, push or publication.

## 2026-10-25 — TR46 expedition lifecycle and corrected subtype counts (060)

[V-GAME logs / V-EXEC C329] Read every exhausted-route message rather than
assigning an origin's first subtype to all its rows: 177 mining surveys and
one Pacific crossing, not 178 mining surveys. Total catalog counts remain
unchanged. Mining has 46 owner tags/locations, all retained Old World: 136
Europe, 34 Asia, seven Africa. No owner tag is an original RNW tag. The separate
Pacific failure is Spain at Dadinga Bay, ID 16084, error.log:1824, 06:41:55.
Use C326's independently bound original definitions; keep C300's eight mounted
Workshop resources as an attribution limit.

[V-LOCAL / V-EXEC / INFERRED C330] RNW does not override mining type/events/
effects. Installed eligibility accepts a capital-only mineral highland, while
route construction excludes the capital and adds it as return. The documented
duplicate-waypoint rule yields zero travel in a private script model. Thirty-three
affected tags already have that set at the frozen start; those tags account
for 138 later errors, without proving every later launch's state. Capital
comparisons and the README's default-completion/no-travel distinction are
recorded; loaded defaults and wait semantics are not reverse-engineered into
an asserted binary defect. No generated-ocean or global vanilla patch follows.

[V-LOCAL / V-EXEC / INFERRED / UNKNOWN C331] The Pacific start, Dadinga callback
and complete event .5 are byte-identical to installed vanilla. The first two
options resume at the final initial stop while scheduling return-choice .6
ten days later, with no intervening route or pause. This is a matching inherited
lifecycle gap; actual option selection/state and delayed resolution remain
unknown. It is separate from 057's western-voyage access-role correction.

[V-EXEC / UNKNOWN C332] Traverse both saves' expedition managers with the
existing narrow reader: one mining survey waiting on construction and two
relic expeditions in 1497, two cartographic surveys in 1590; no active Pacific
or western voyage. These snapshots cannot recover the failed transitions.
The 38 invalid resumes, 38 invalid-leader starts, four unavailable-type starts
and L02 assertion remain unattributed. Generic action files and possible
static destination-change callers do not supply runtime identities. Register
this limited text/save/static investigation in interoperability R-005; private
helpers and raw results stay ignored under local_data/tr46-expeditions.

[V-EXEC C332] All 37 original evidence-file hashes and 732 archived world hashes
match. Current build/fingerprint remain unchanged. Locked sync and full check
pass: 1,969 Python, 14 skips, 23 Rust, format/lint/types clean. No source/output,
version/epoch, installation/profile/save/settings/playset change, game launch,
process control, push or publication. Full findings: [TR46 expeditions](tr46-expeditions.md).
The next independent block is L04's AI command rejections/expansion arithmetic.

## 2026-10-25 — TR46 AI diagnostics and expansion scoring (061)

[V-GAME logs / V-LOCAL / V-EXEC / UNKNOWN C333] Recount every original ai.log
line: 57,352 records, 57,156 execution and 196 posting, 42 stage/command
categories. Cabinet assignment contributes 35,724 (62.29%), but the action,
actor, target and failed prerequisite are absent. Limited installed diagnostic
inspection confirms the command-name-only branches; it cannot identify a
specific engine race, rejected frontier action or native warning frequency.
Do not turn message counts into rates without successful-command totals.

[V-LOCAL / V-EXEC / UNKNOWN C334] RNW does not override the neighboring-war-
target content. Installed score opens at line 40 and divides by capital distance
at line 42 without a script guard. The README identifies future war targets,
not colonization. Three division errors omit attacker and target. All 202
native state start capitals are distinct, as are the capital IDs within the
777/597 landed location countries at the saved checkpoints. Neither snapshots
nor a limited zero-divisor branch inspection establish error-time distance,
scope/position or the final planner result. No global vanilla patch follows.

[V-GAME logs / V-LOCAL / V-EXEC / UNKNOWN C335] Building truncations clamp
232→2 for NAV, 7→0 for ABA43 and 9→0 for IFA. Their saved full handles bind to
Old World countries, outside the original native creation closure. ABA43 is
an explicitly released Novgorodian country at rokiskis; its dynamic tag does
not make it an RNW native. Installed code bounds the list, but the producing
count mismatch and later construction outcomes remain unknown. Snapshot land
counts are not the state at the error clocks.

[V-EXEC / UNKNOWN C336] Preserve three L04 subproblems and C300's mounted-mod
confounder. No new attribution reverses 059's observed conquest/consolidation
or explains native frontier selection and league defeat. No AI bonus, global
vanilla script change, warning suppression or generated-capital adjustment.
All 37 original evidence and 732 copied world hashes match, both save CRCs and
cached-extraction hashes pass, current build/fingerprint remain unchanged.
Record limited binary/save inspection in interoperability R-005. Required
locked sync/full check: 1,969 Python pass, 14 skip, 23 Rust, format/lint/types
clean. Documentation only; version 0.12.8/epoch 38 and installed LSI3 unchanged.
No game launch, source/output/install/profile/save/settings/playset edit,
process control, push or publication. Full findings: [TR46 AI diagnostics](tr46-ai-diagnostics.md).
The next independent block is L05's Tordesillas option text and its scope.

## 2026-10-25 — TR46 Tordesillas text and saved division line (062)

[V-GAME logs / V-LOCAL / V-EXEC C337] L05's four records and debug mirrors
are one failed `treaty_of_tordesillas.5.c` localization. Full original world
inventory and all 55 localization files show no RNW event/text override.
All 11 installed languages depend on `overlord`; ten use the logged accessor,
Russian its case-customization accessor. Do not infer effective UI language,
eleven runtime failures or a clean vanilla control from inherited sources;
eight mounted Workshop directories remain a confounder.

[V-LOCAL / INFERRED / UNKNOWN C338] The colony-transfer event conditionally
saves top_overlord for a subject; subject-only .c forwards after two days,
initial demand schedules after seven. Event is major for actor. Bare saved
overlord references also occur in installed vanilla, so an explicit accessor
is not an established syntax fix. Missing scope at rendering fits the log;
actual recipient/subject status/options/scopes/observer context are absent.
Neither saved event queue retains a Tordesillas string. No global text/event
patch or claim that the transfer/treaty itself failed.

[V-GAME owner / V-EXEC C339] Correct 06b's wording: the **western continuation
of the same mainland** crosses the raster seam to its right edge but counted
as Britain's east. Preserve the already chosen full mainland wrap. Reuse the
validated save reader to recover the final treaty's SPA west / GBR east,
1549.10.2–1568.10.22 and retained line 24717 / rnw_loc_01224; early record
empty. This advances C305's missing-line limit but not the observation-time
line history, affected location or exact engine comparison point/span.
Original situation has only two fallback-key replacements; tooltip/map-color
blocks match vanilla. Distinguish geographic background from province claims,
top ownership and area-conflict overrides. Text resolution and western-mainland
allocation remain separate open conditions. Record bounded map/RTTI inspection
and the read-only situation/event-root traversal in interoperability R-005.

[V-EXEC C340] All 37 evidence and 732 archived world hashes pass, both saves'
hashes/ZIP CRCs and prior structure/extraction manifest hashes pass. No new
save token. Build/executable/map fingerprint unchanged. Required locked sync
and full checks pass: 1,969 Python, 14 skips, 23 Rust, format/lint/types clean.
Documentation only: generator 0.12.8/epoch 38 and installed LSI3/hub unchanged;
no game launch, source/output/install/profile/save/settings/playset edit,
process control, push or publication. No new owner campaign requested.
Full findings: [TR46 Tordesillas](tr46-tordesillas.md).
The next independent block is L06's corrupted country-name formatting.

## 2026-10-25 — Continuous Tordesillas longitude and TR46 candidate (062)

[V-EXEC C341] `eu5_treaty.py` constructs continuous New World longitude
coordinates on the canvas axis across the raster seam for Tordesillas side
selection, line moves, side-swap estimates, map shading and final province
allocation. Immutable coordinates are dry-land centroids, exposed via
$O(\log(\text{width}))$ vanilla scripted geography bitmasks and script values.
Comparison predicates (`is_east_of`) and province distribution iterators
(`every_east_of_province_definition` / `every_west_of_province_definition`)
are rewritten with strict count guards, preserving vanilla claim gates,
religion, ownership and effects without runtime variables or engine changes.

[V-EXEC C342] TR46 candidate audit: generated mainland wraps across the
raster boundary with 164 locations across 30 provinces at raster right.
Under raw coordinate comparisons (`is_east_of`), all 164 locations evaluated
east of the recovered line `rnw_loc_01224`. Under continuous axis coordinates,
all 164 locations and all 30 provinces evaluate west of the line in both
predicate evaluation and final province distribution. Reversing rewritten files
restores source text byte-identically. All 7,324 dry generated cells match
physical centroids.

[V-EXEC C343] Generator 0.12.9 / algorithm epoch 39: 1,978 Python tests pass,
14 skip; 23 Rust tests pass; format, lint and types clean. Golden reference
world updated (`RNW1-081WG-1HAWD-H0XFH-T0060-J0840-3C082-243AG-0C700-X3YQR`,
digest `3423df6d…cee01`, 837 files). Comparing TR46 0.12.9 (RNW: Continents
QW6O, 838 mod files, digest `33ef2ed8…64bd`) against 0.12.8 (RNW: Continents
LSI3, 833 files): all 831 other nonmetadata files (geography, terrain, rivers,
heightmaps, countries, pops, diplomacy) are 100% byte-identical; only 5 added
treaty files and 2 rewritten situation files differ. Linux/Windows parity
matches and Windows offscreen self-test passes. Runtime engine appearance and
treaty events remain unobserved.

[V-EXEC / V-LOCAL C344] With log and live checks confirming EU5 is closed,
installed candidate RNW: Continents QW6O in `mod/rnw_exp_tr46_treaty` (840
files checked) and updated main hub 0.12.8→0.12.9 in `mod/rnw_exp_hub`
(3,264 files checked). The old 3,262-file hub is externally backed up under
ignored `local_data/tr46-treaty-fix/hub-backup-before-0.12.9/` and retained in
`.rnw-install/retired/`. Nine profile-root hashes, 24,498 other-mod size/time
records and nine prior folder entries are preserved. No game launch, process
control, push or publication.

## 2026-10-25 — In-game acceptance of wrap, mountains and TR46 candidate (063 / 0.13.0)

[V-GAME owner C345] Owner visually reviewed candidate `rnw_exp_tr46_treaty`
(RNW: Continents QW6O, 0.12.9) in EU5 1.4.4: the seam/crack at the horizontal
map wrap is confirmed absent (TR46-06a CLOSED [V-GAME]); impassable mountain
relief is visibly improved and accepted for release (TR46-01 / TR46-02 ACCEPTED
[V-GAME], further aesthetic ridge improvements postponed to post-release); all
done work on the cylindrical wrap, river continuity, local sea routes, and
continuous Tordesillas allocation is accepted.

[V-EXEC C346] Product version rises from 0.12.9 to **0.13.0** under ADR 0003
(MINOR rises when a roadmap/campaign phase is accepted in game). No world file
or algorithm output changes, so epoch stays 39 and golden reference world remains
unchanged (`tests/golden_world.json`). Full test suite passes: 1,978 Python tests,
14 skip, 23 Rust tests; format, lint and types clean.

## 2026-10-26 — TR46 diagnostic closure: L06 attributed to vanilla, L08 VFX locators fixed (0.13.1 / epoch 40)

- [V-GAME logs / V-LOCAL executable C347] Traced `error.log:1210–1269` (40 unknown formatting tags `.\x15.w.r.` and 20 country-name failures `\x15.\x15.W.R.`) to Morocco civil war at `game.log:7389` (`CIVIL WAR: \x15TOOLTIP:DYNASTY,623 \x15L; Wattasid\x15!\x15! Rebels against Morocco`). Binary analysis of `eu5.exe` at `pdx_text_formatter.cpp:807` and `countryname.cpp:1135` reveals that Jomini's acronym generator splits words and takes initial letters without stripping Paradox escape control bytes (`\x15`), producing `\x15.\x15.W.R.`. Attributed 100% to vanilla engine/scripts in Old World Morocco; no RNW defect (TR46-L06 CLOSED).
- [V-LOCAL executable / V-EXEC C348] Resolved `error.log:327` (`map object locator "vfx" is incomplete!`). In vanilla EU5, all 28,573 locations require a VFX locator (1:1 match in `definitions.txt`). In TR46 with `expand_oceans`, 21 `rnw_ocean_*` locations were added to `definitions.txt` but omitted from `generated_locators_vfx.txt` because `_trimmed_instances` filtered `if key in held` (where `held` only has vanilla keys). Generator 0.13.1 / epoch 40 appends `plan.oceans.anchors` to `generated_locators_vfx.txt` and verifies full coverage via `verify_locators` (TR46-L08 FIXED). Reference world digest updated to `af903212dd4c9addacdc06d8c4c676920e29f3803fc82568f3c65a8152112e7e`.

## 2026-10-26 — 657Q ocean-course ends (0.13.2 / epoch 41)

- [V-GAME owner / V-LOCAL / V-EXEC C349] Reconstructed the installed 657Q
  supercontinent from its exact code and matched all final sea topographies.
  Four open-ocean tips survive the old global/local reachability checks. The
  Ruaziasleir tooltip includes endpoint `rnw_sea_00875`; one internal cell at
  480-permille inherited-course coverage separates it from another lane fragment.
  Both halves already reach retained water. Build/fingerprint unchanged.
- [V-EXEC C350] Complete deep ends before folding closed water: water-only paths
  to existing water, excluding the incoming stem/junction, preferring the forward
  45-degree cone and stopping at the first navigable destination. A blocked
  heading takes a reachable turn; no destination fails loudly. An independent
  export check rejects deep tips even in a globally reachable component.
- [V-EXEC C351] 657Q has 165 lanes, eleven opened cells and zero tips. Independent
  raster/template read-back preserves 51,341,116 nonsea identity pixels,
  30,434,666 retained nonsea RGB pixels, 558 terrain2 files, rivers, 54,773 road
  strips and 21,525 populated location records. Full check: 1,987 Python pass,
  14 skip, 23 Rust pass; types/lint/format clean. Local game checks 12 pass,
  two opt-in skips. Windows offscreen self-test and four-case Linux/Windows
  parity pass. Epoch-41 reference: 837 files, `667a51aa…7386e`.
- [V-EXEC C352] Installed the separate EVXP world and updated the generator hub
  0.13.1→0.13.2 with verified external/retired backups. Checked all 820 world and
  3,264 hub files; preserved 1,639 other-mod file size/time records, nine root
  hashes and seven library records. The owner's revealed-world preference is
  retained through the normal presentation writer. No game launch, process
  control, save/playset/setting/library change, push or publication. Engine
  movement after this correction remains [UNKNOWN]. See [064](../../experiments/064-ocean-course-ends/README.md).

## 2026-10-26 — EVXP library registration correction

[V-LOCAL owner screenshot / V-EXEC C353] The direct 657Q fix export lacked a
library record and showed as Older world. Registered its verified bundle under
`rbsvu4fogp`, retained Supercontinent EVXP, atlas/previews/code/record, and moved
only its unreferenced folder to `rnw_exp_world_rbsvu4fogp`. All 820 files checked,
only metadata id changed. Existing seven records, other worlds and root hashes
preserved. No regeneration, game launch or product version change. The owner
then requested automatic recognition of installed RNW worlds as normal functionality;
that is the next implementation phase, separate from this one-world registration.

## 2026-10-26 — Automatic installed-world recovery (0.13.3 / epoch 41)

- [V-EXEC C354] After the EVXP registration omission, the owner requested automatic
  recognition as basic functionality. Readable installed codes now enter the
  library in place; new application-generated mods carry checked recovery data
  in .metadata. No original build/record is invented for legacy code-only worlds.
  Recovery is atomic, finishes metadata-first copies, preserves personal fields,
  checks folder aliases across profiles and handles built transfers safely.
  The visible window notices small metadata changes without losing selection or
  unsaved notes. All revised wording is translated into every official language.
- [V-EXEC C355] Full check: 1,999 Python pass, 14 skip, 23 Rust pass; types/lint/
  format clean. Real-copy recovery restores EVXP's 6,910-cell atlas and exact
  provenance/previews, with all 818 nonmetadata files unchanged. Qt UI inspected;
  Windows offscreen self-test and two-case Linux/Windows recovery parity pass.
  Epoch 41/reference unchanged; extra metadata has no new in-game observation.
- [V-EXEC C356] Final source/catalog/package checks and 3,266-file hub installation
  pass, with 3,264-file external/retired old-hub backups. The immediate baseline
  (one library record, 820 other-mod files, nine root hashes) stays exact.
  Source guard required a rebuild for a concurrently saved maps-panel change;
  no profile write occurred before that was resolved. A later existing app log
  and receipt independently show a successful native 0.13.3 generation. No new
  world creation/removal by this hub update, game launch, process control,
  playset/settings/save change, push or publication. [065](../../experiments/065-installed-world-recovery/README.md).

## 2026-10-26 — map mod descriptions

- [V-EXEC] Generated New World mod metadata now carries a player-facing description with the generator name, reproducible world code when available and a Steam Workshop call to action. The internal game-validation status remains in the generator report, not the player-facing description. Metadata is excluded from world output digests; algorithm epoch 41 is unchanged. Product version 0.13.4.

## 2026-10-26 — EVXP Windows-library preview correction

[V-EXEC C357] Confirmed the owner's square EVXP image is a source-data error,
not zoom: Windows 0.13.3 recovered the receipt-less 0.13.2 mod by copying its
512×512 thumbnail as both previews. Original Linux/export previews are
2048×1024. C355 tested a temporary copy with an added receipt; the installed
EVXP had none. Restored the verified 29-file original bundle into the Windows
library, preserving personal fields and backing up its three prior files.
Record/manifests, full previews and 6,910-location atlas checked; revealed image
visually inspected. Four other records, 7,491 mod-file stat records, nine root
hashes, preferences and original source bundle preserved. No source/package/mod
change, new version, generation or game launch. Legacy thumbnail substitution
remains an implementation limitation. See [065](../../experiments/065-installed-world-recovery/README.md).

## 2026-10-26 — EVXP hang on 22 December 1341

[V-GAME owner/recording / V-LOCAL C358] Preserved the stopped session before
the owner's restart. Steam recording shows progress from the screenshot's
30 May to 22 December, followed by an unresponsive window and forced close.
The owner independently reports normal progress past that date on the same
world after restarting. [INFERRED / UNKNOWN C359] No immediate screenshot
freeze, invariably failing date or particular cause is established. A
Spectacle pipe diagnostic and real river/VFX/treaty load errors cannot be
assigned causality; partial logs and an already-terminated process leave no
hang stack. [V-EXEC C360] Executable/build/map fingerprint rechecked; locked
sync/full check passes 1,999 Python tests, 14 skips and 23 Rust tests. No source,
world, profile or version change, game launch, termination or new owner
test. See [066](../../experiments/066-1341-hang/README.md); raw evidence stays
under ignored `local_data/hang-1341-20261026/`.

[V-GAME owner / V-EXEC C361–C363] The owner then reported another live hang,
on 2 March 1346. Captured its logs, CPU use and bounded thread state. Actual
resumed samples point to prolonged unit-graphics path-refinement work; the
triggering route and whether the generated map or engine is responsible are
unknown. An early debugger detach left a group stop, which was disclosed and
corrected; the identical paused snapshots are excluded as execution evidence.
Subsequent captures restore execution in a final cleanup step, with final
state R / TracerPid 0. No launch, termination, game-memory workaround or profile
change. Read-only executable/PE-unwind research is recorded in R-006; all raw
artifacts stay under ignored `local_data/hang-1346-20261026/`.

[V-EXEC C364–C365] Follow-up recovery advice: preserved and hash-verified the
latest autosave (**1 April 1342**, metadata and ZIP CRCs checked), without
editing the profile or asking for another run. Owner was advised that closure
was safe for the already-preserved diagnostics; agent did not terminate EU5,
and its PID was later absent. Offline stack/definition/spline binding narrows
the path-refinement lead to the two locations across the raster seam,
rnw_loc_01100 / rnw_loc_05111. Captured intermediate vectors and canonical
spline wrap need further attribution; no replacement encoding is presented
as a verified fix. See 066; no source, output, version or installation change.

## 2026-10-26 — Towa troop-raising seam reproduction

[V-GAME owner / V-LOCAL / V-EXEC C366–C367] Owner independently reproduces
the hang immediately on raising troops for seam-spanning Towa. Preserved the
new logs and console records; no process remains for inspection. Installed
Towa is KVF with 71 initial locations across 20 provinces. History separates
the 0.12.2 mainland/contact/spline wrap from 0.12.6's primary terrain extension;
the latter preserved geography and roads. Neither change is isolated as causal.

[V-LOCAL / V-EXEC / UNKNOWN C368–C369] Vanilla offers no matching wrapped
land-road example. Cylindrical spline tests do not establish engine behavior;
the path-tightening command gates a later stage than the captured search.
No guessed data rewrite or switch is shipped. Prepared a bounded, hash-pinned
route capture, with offline replay matching all 17 previous stack returns and
explicit detach/execution-state checks. Its live heap capture remains pending.
Requested one immediate owner reproduction because missing heap data cannot
be recovered after process exit. No agent launch, installation, output or
version change. See [067](../../experiments/067-towa-seam-hang/README.md) and
R-006; all raw executable/memory/log data stays ignored.

[V-EXEC C369] Locked sync/full check passes 1,999 Python tests, 14 skips and
23 Rust tests, with format/lint/types clean. These verify the unchanged
generator, not a hang remedy or the pending live heap capture.

[V-GAME owner / V-LOCAL / V-EXEC C370–C373] Owner confirms the freeze begins
after unpausing and leaves one immediate repetition open. Captured 144 route
points, IDs/flags and unit state from the same engine refiner family; verified
detach and R / TracerPid 0, preserved 27 logs. Horizontal midpoint subdivision
loads the captured map's **height 8192** instead of **width 16384**, then
normalizes by width. Independent float32 replay matches the wrong midpoint
and four subsequent bisections bit for bit. The generated seam crossing
exposes this engine defect; rewriting the road spline or undoing the terrain
crack fix is not an established repair. The two location identities are already
split at the seam. No safe data-only repair preserving mainland continuity
has been verified, no game binary/memory/map is patched and no new product
version or candidate is claimed. A later optional read finds the process gone
without attachment; agent did not terminate it. See 067 and R-006; complete
capture/derived arithmetic stay private and ignored.

## 2026-10-26 — Restore vanilla-style location identity at the raster edge

[V-GAME owner / V-LOCAL / V-EXEC C374–C375] Owner corrects the earlier
interpretation by pointing to working vanilla crossings. Local comparison finds
the actual representational difference: the production cache still forcibly
splits crossing cells, unlike vanilla's shared colour/identity. The synthetic
production call makes 171 cells rather than 157 and fails equality with the
continuous model. C373's broad repair boundary is withdrawn; the old arithmetic
trace remains evidence of that failing branch, not valid generator input.

[V-EXEC C376–C378] 0.13.5 / epoch 42 removes the legacy split and its cache
input. Corrected EVXP preserves the entire physical-class raster, all 30,434,666
retained nonsea Old World RGB pixels, rivers and height sources/placements.
Only sixteen existing material files differ among 558 terrain2 files. Towa's
false transition disappears; the earlier pair remains distinct but has seam-
continuous identities and nearby same-side unit anchors. All 6312 generated
anchors and 865 bundle files check. A dropped-area regression in the former
reference is fixed through initial shared source bindings, preserving GRL and
all script references without relaxing validators. EVXP offers all story
families and becomes the epoch-42 reference, 837 files, digest 76c17c96…f4d5b0.

Full check: 2005 Python/23 Rust pass; format/lint/types clean. Fresh reference
suite: 13 pass/one opt-in skip, 213.41 s. Final Windows self-test and Linux/
Windows geometry plus area-binding parity pass. Prepared a separate candidate
and self-describing receipt. No engine patch or campaign migration. Post-fix
game behavior is unobserved and no new owner sitting is requested. See
[068](../../experiments/068-continuous-location-identities/README.md).

[V-EXEC C379] Installed the new **RNW: Supercontinent EVXP fixed** and its
29-file entry into both generator libraries; 848 installed mod files verify.
Updated the generator-only hub 0.13.3→0.13.5, 3266 files checked, with external
and retired verified backups. Preserved all 820 original EVXP file hashes,
4225 other-mod size/time records, nine root hashes, 111 save-file stat records,
eleven old library records and two preference files. No sweep or playset edit.
Host check finds no EU5 process; stale log state remains `played` after forced
closure and is not mistaken for a live session. No game launch or campaign
migration. The source defect is fixed; post-fix engine acceptance is unobserved.

## 2026-10-26 — Current EVXP session diagnostics

[V-LOCAL / V-EXEC / INFERRED / UNKNOWN C381–C384] The owner's disease-panel
question expands to an exhaustive audit of the current launch's errors. The
[catalog](evxp-session-diagnostics.md) accounts for every captured origin and
AI category, separates initial 22F4 loading from EVXP fixed, and identifies
actionable treaty-loader, river-export, locator and starting-building issues.
These logs do not validate the earlier offline treaty/river contracts in engine.
The lower Great Pestilence counters query the player's country, explaining
observer zeros; the displayed death arithmetic remains unverified. Other
diagnostics retain source and attribution limits. Documentation only, full
check passes; no output change, game intervention or new owner test requested.

## 2026-10-26 — EVXP campaign continuation through 1682

[V-LOCAL / V-EXEC / INFERRED / UNKNOWN C385–C386] Read and hashed a stable
27-file follow-up snapshot while the game remained running. The session now has
9,096 error-log records; the largest repeated delta is 3,340 movement-religion
warnings. New actionable signatures include same-province migrations from
`settle_the_frontier` and a Pacific-crossing route exhaustion; the cargo-locator
error is mirrored in ECS output. AI warnings grow to 92,956 complete entries.
The game log reaches 1682, with no Great Pestilence end entry after its 1540
start. The installed outcome has no calendar timeout and depends on infection
coverage, disease exhaustion and remaining uninfected American countries; logs
cannot identify the unmet predicate or confirm current UI state. Snapshot and
analysis are recorded in [the audit follow-up](evxp-session-diagnostics.md#follow-up-campaign-continued-through-1682).
Documentation only; no game or generated content changed.

## 2026-10-26 — East Asian colonization and the range overlay

[OWNER / V-LOCAL / V-EXEC / INFERRED / UNKNOWN C388] A stable read-only
follow-up of the EVXP campaign logs reaches 1 January 1795: 1,460 logged
colonization starts, 131 by Muscovy and none by Ashikaga; current error/AI logs
have no colonial/range/charter keyword diagnostics. Installed vanilla rules
default AI exploration and colonization to western-only, while generated RNW
ports place the same Alaska target substantially nearer the far-eastern
Siberian candidate than the northern Japanese-region candidate in wrapped map
coordinates. The mod's copied exploration trigger keeps the vanilla AI
eligibility block unchanged and only expands discovery checks for generated
American sea areas. The default rule explains AI Japan's absence if the owner
left it unchanged; port geography, plus unknown advance-derived range totals,
is consistent with the overlay difference. Coordinate distances are not the
engine's range metric, and rule state, port ownership and exact cutoff remain
unknown. No mod script defect is established. Frozen logs and source details
are recorded in [the diagnostic audit](evxp-session-diagnostics.md#colonial-range-and-east-asian-ai).

## 2026-10-26 — EVXP campaign reached 1849

[OWNER / V-LOCAL / V-EXEC / INFERRED / UNKNOWN C389] After the owner saved and
closed the campaign, the stable log snapshot reaches 1 January 1849. The final
debug entries show game-manager serialization followed by `Quit from inside
game` and a Game→MainMenu transition; the save itself was not read. The current
launch has 21,820 timestamped error records, with repeated formatting,
list-cap, rejected-policy and sub-unit-text families, plus recurring failed
expeditions and same-province migrations. There is no direct Pestilence or
colonial-range error and no explicit fatal/crash marker. Great Pestilence has
no logged end after its 1540 start; vanilla outcome conditions have no timeout,
so its exact final state remains unknown. Colonization logs total 1,875 starts,
144 by Muscovy and none by Ashikaga or the East Asian labels checked. The
campaign's progress and orderly exit support runtime continuity through 1849,
not a claim that all scripts are error-free or that the save was reload-tested.
The full evidence and limits are in [the final audit](evxp-session-diagnostics.md#final-follow-up-campaign-reached-1-january-1849).

## 2026-10-26 — Completed-campaign mod corrections

- [V-LOCAL / V-EXEC / INFERRED C390–C391] Correct the attributable EVXP treaty, river drawing, duplicate VFX and initial guild-capacity defects in 0.13.6/epoch 43. Preserve physical geography, population and vanilla rules; retain unresolved locator/culture/runtime attribution instead of silencing warnings. The bounded interoperability finding and exact limits are in [069](../../experiments/069-campaign-mod-fixes/README.md) and the existing campaign audit.
- [V-EXEC C392] Full checks, independent reference reproduction, Windows/Wine self-test, platform parity and archive audits pass. Install the separate EVXP RC world and updated generator-only hub with verified preservation/backups, as recorded in [INSTALLED](../../experiments/INSTALLED.md). No EU5 launch or publication; the new candidate's engine result remains unknown, so no 1.0.0 completion claim.

## 2026-10-26 — Generated-country AI personalities

[V-LOCAL C393] The installed 1.4.3 setup explicitly assigns eight defined AI
personalities to 94 countries in `main_menu/setup/1337/26_ai_personalities.txt`;
the installed definitions also mark `ai_balanced` as the default. Generated tags
were absent from that assignment file, matching the owner's observation that the
New World appeared uniformly Balanced. This does not determine the engine's
initialization for every unlisted tag.

[V-EXEC C394] RNW 0.13.7 first replaced the default with seeded assignments
weighted by vanilla frequencies. The owner clarified that plausible strategic
behavior matters more than reproducing that frequency distribution: a powerful
empire and a vulnerable border state should not receive interchangeable behavior.

[V-EXEC C395] RNW 0.13.8/epoch 45 replaces frequency sampling with a deterministic,
explainable classifier. It uses generated population and technology as a comparative
power proxy, land neighbors, markets/coasts, empire prey and threat opinions,
rivalries, alliances, subjects/overlords, confederations and society archetypes.
Protection links are excluded from threatening-border comparisons; archetype and
relationship signals precede ordinary border/coastal defaults. Every sovereign
decision records its context and human-readable reason in `report.json`; pop-only
tribes remain unassigned. On the 313-country reference, profiles are
Balanced 1, Cautious 240, Defensive 12, Expansionist 42, Friendly 4, Isolationist 2
and Opportunistic 12. This distribution follows that generated world's signals,
not a target quota. The power proxy is not a military-strength estimate, so the
specific behavioral effect of the resulting profiles in EU5 remains [UNKNOWN].
The 850-file canonical reference digest is
`2fb15ba6b2e6109d23cc1c6da9f4452b126ef9e8e95ecdaecbe8b47774d12b4e`.

`make check` passes: 2,018 Python tests (14 skipped), 23 Rust tests, formatting,
lint and type checks. The offline Windows-layout Wine self-test passes. Installed a
separate 881-file 0.13.8 candidate and updated the generator-only hub from 0.13.7
to 0.13.8. The former hub is backed up byte for byte; the previously installed
world, all other pre-existing mod files, playsets, settings and continue-game data
are preserved. No EU5 launch or playset change; the in-game AI result is unobserved.

## 2026-10-27 — Balanced as the generated-country baseline

[V-LOCAL C396] In the installed setup, only 5 of the 94 countries with an explicit
personality entry are Balanced, but `ai_balanced` is also `default = yes` in the
personality definitions. Those 94 hand-picked overrides do not describe the whole
vanilla country population; Balanced is the fallback. The previous contextual
classifier overread relative population and ordinary borders, making Balanced
nearly absent. The report also omitted the `confederated` input used for some
decisions.

[V-EXEC C397] RNW 0.13.9/epoch 46 now keeps vanilla Balanced as the generated
baseline. A specialized profile requires a direct empire threat or designated prey,
a declared rivalry, subject/alliance ties, both a coast and an established market,
or a defined society archetype. Mere power advantage, a larger neighbor, a coast
alone or isolation do not override the default. On the 313-country reference,
222 are Balanced (71%), 49 Defensive, 29 Cautious, 6 Friendly, 4 Expansionist and
3 Opportunistic. The report records each decision and includes confederation status;
canonical digest `003d59758186470cda2fd2ce531ed154cb5875a405316b92eb36ad121a10b55e`.
The behavior is deterministic and no target quotas are used. `make check` passes:
2,018 Python tests (14 skipped), 23 Rust tests, format, lint and type checks. Installed
a new world whose resource-only reroll retains the reference's four empires and all
313 AI decisions; all 881 files match the prepared candidate. Updated the 3,270-file
hub 0.13.8→0.13.9 and passed its isolated Wine self-test. All ten previously installed
worlds, other mod files, and three profile-root files are unchanged. No EU5 launch or
playset change; actual AI behavior remains unknown.

## 2026-10-27 — Ocean-current geometry

[V-GAME owner / V-EXEC C401] The owner's maps exposed broad irregular current patches and ocean
ends. Sea-cell generation now follows the installed game's replaced current bands, and route
completion detects cyclic tips as well as degree-one ends. The FWL3 land mask remains identical;
the separately installed candidate and generator hub were verified offline. Actual appearance and
navigation remain [UNKNOWN] without a new game session. Details and limits are in
[sea geography](../sea-geography.md) and [INSTALLED](../../experiments/INSTALLED.md).

## 2026-10-27 — Vanilla control campaign to 1632

[V-GAME owner / V-EXEC C402] The owner completed a vanilla campaign with all mods disabled.
Its full logs show recurring base-game script errors and AI command rejections, including the
same dominant `set_cabinet_action` warning family previously seen in TR46. Those message families
are not attributable to RNW; the missing actors and failure reasons remain unknown. Full counts
and the comparison limits are in [the AI diagnostics](tr46-ai-diagnostics.md#7-vanilla-control-through-1632).

## 2026-10-27 — Ocean crossings, sea-cell geometry and designed current corridors

[V-GAME owner / V-EXEC C403] Owner screenshots on KZWN showed a hover-fill versus
outline mismatch and distant coasts separated by closed water. In the installed
0.13.11 raster, the longest shared boundary departed 42 pixels from its chord.
RNW 0.13.12 / epoch 49 switches sea-cell growth to Euclidean seed distance (reducing
chord departure to 1.03 pixels), opens useful crossings between distant coasts and
retained contacts, and names impassable zones by their area or body. Candidate
and hub verified offline.

[V-EXEC C404] RNW 0.13.13 / epoch 50 plans useful crossings over generated water
before partitioning sea locations (`rnw.sea_corridors`). Centerlines across
unobstructed water are simplified and widened into connected sea-cell bands.
Small disconnected retained-ocean remainders merge into an adjacent navigable
sea when sharing an edge, preserving principal vanilla identities and landlocked
remnants (`rnw.eu5_oceans`). Staged and verified candidate `mod/rnw_exp_kzwn_hydrology_01313`
and updated hub to 0.13.13.

[V-EXEC C405] RNW 0.13.14 / epoch 51 aligns currents along straight designed crossing
bands with a clear principal axis (`rnw.currents`). Direction is chosen from the
aggregate projection of source currents along the band; broad junctions keep
interpolated flow. Generator hub updated to 0.13.14 in the owner's profile with
passing Wine self-test. Test suite passes 2,056 Python tests (14 skipped), 23 Rust tests,
and local installation suite (12 passed, 2 skipped). In-game rendering and movement
remain unobserved.

[V-EXEC C406] RNW 0.13.15 / epoch 52 keeps water classification stable across
folding, prevents one-sided open-ocean slivers, and checks sea connectivity early.
Geographic replacement distinguishes identical names in different scopes; river
fragment starts are chosen for a valid drawing without changing the physical network.
The owner's failed world now completes offline and is installed separately; failure
messages and new-seed retry are available in the window. No EU5 launch.

## 2026-10-27 — Actual ocean exits instead of copied current remnants

[V-GAME owner / V-EXEC C408] The owner's 4TXC screenshot exposed a current crescent
with only six pixels at one nominal sea contact. Earlier reachability checks accepted
it and missed the visible defect. Version 0.13.16 plans interior routes on the finished
geography rather than preserving the old world's current outlines, requires useful
opening width at deep-route interfaces, and treats isolated short connectors as
ordinary sea. The exact written comparison removes that crescent's current and has
zero land-mask differences. The corrected world and its complete library records,
plus the verified generator hub, are installed separately. The reference export was
independently reproduced; tracked-code checks and Python/Rust suites pass. New game
rendering remains unobserved. Details and limits are in C408 and the installed record.

## Public dynamic content catalogue, 2026-10-28

[V-EXEC C409] Added the [player catalogue](../content-catalog.md) and a
[complete reference](../content-reference.md) generated from the original content
definitions, linked from the public documentation. Eligibility and actual effects
are distinguished from narrative wording and historical design notes. A regression
check keeps the reference synchronized; it requires no game installation. Product
output is unchanged. Verification and its limits are recorded in C409.

## Viable remote countries, 2026-10-28

[V-LOCAL / V-EXEC / INFERRED C410] Moved remote settlement planning before population,
required vanilla-calibrated agrarian support for every landed country, and planned
trading towns for disconnected landed groups. The same reference drops from 73 states
without peasants to zero, and from 11 isolated states to five, preserving geography.
Demographic support and graph market coverage do not prove engine income or later AI
development [UNKNOWN]. Verification, reproduction and installation are recorded in
C410 and [INSTALLED](../../experiments/INSTALLED.md).
