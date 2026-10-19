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

