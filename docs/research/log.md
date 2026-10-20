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
- [V-GAME owner review] V1a.1 (commit 123a907) installed, checked in game and accepted (C58).

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
- Designed R7a for Sonnet in [sonnet-r7a-development](../handoff/sonnet-r7a-development.md): drop the positional entries; a society term `round(B × complexity / 1000)` with B calibrated from vanilla (12); harbour values quantile-mapped from the vanilla American distribution by shelter; market villages in the vanilla share of capitals, most complex first. It adds invariants, a report section, offline acceptance on three worlds and experiment 012 for the owner. No code changed.

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

