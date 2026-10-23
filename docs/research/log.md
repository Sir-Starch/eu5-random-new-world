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
- [V-EXEC] `bc62844` records release packaging and CI; its exact index snapshot passes
  the three release tests. `7feda14` records the integrated generator 0.9.24 and its tests;
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
- Design [sonnet-r7-technology-and-empires](../handoff/sonnet-r7-technology-and-empires.md):
  R7b (S09) levels by complexity on the vanilla quantiles, templates that follow the level, the
  family in the homeland vector; R7c (S10) empires at `min(T, S + 1)` with the highest American
  rank and royal roads, feared by neighbours and resented by vassals. No generated output changed;
  no version bump, no game launch, nothing installed.

## 2026-10-22 — R7b: technology from the societies (Sonnet)

- [OWNER] The 0.9.27 cover candidate was uncommitted at the start of R7b, as the handoff foresaw;
  the owner asked for it to be committed first (`f9f7e2c`). Base builds of four worlds were made on it.
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
  order-preserving rebuild of 0.9.31 is a precaution, not a verified fix. The history of the commit `ceea893`, whose
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
