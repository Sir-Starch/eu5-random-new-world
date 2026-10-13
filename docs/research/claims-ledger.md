# Claims ledger

Game paths are relative to the installation root listed in [inventory](game-install-inventory.md). `[V-GAME]` reports observed startup/log behavior only, unless a row says otherwise. All dates are 2026-10-13.

| ID | Claim | Evidence label | Evidence | Game version | Date |
|---|---|---|---|---|---|
| C01 | Installed build is Steam 1.4 open beta build 25905365 | [V-LOCAL] | `../appmanifest_3450310.acf`, Steam library metadata | 1.4 beta | 2026-10-13 |
| C02 | The running game identifies as 1.4.1 | [V-GAME] | Main menu; isolated `logs/debug.log` mod-version line | 1.4.1 | 2026-10-13 |
| C03 | Map identity uses a 16384×8192 RGB location raster and named color declarations | [V-LOCAL] | `game/in_game/map_data/locations.png`, `named_locations/00_default.txt` | 1.4.1 | 2026-10-13 |
| C04 | Hierarchy is continent → subcontinent → region → area → province → location | [V-LOCAL] | `game/in_game/map_data/definitions.txt` | 1.4.1 | 2026-10-13 |
| C05 | Parsed hierarchy has 28,573 locations, 6,174 under America; parsed color list has 22,314 unique names/colors | [V-EXEC] | `uv run rnw inspect GAME_DIR`; local game files in C03–C04 | 1.4.1 | 2026-10-13 |
| C06 | `default.map` references locations, rivers, adjacency and port files, separates sea/lake keys, wraps horizontally | [V-LOCAL] | `game/in_game/map_data/default.map` | 1.4.1 | 2026-10-13 |
| C07 | Terrain rendering has heightmap, biomes, layers, masks and caches; which are mandatory for a changed map is unknown | [V-LOCAL]/[UNKNOWN] | `game/in_game/gfx/terrain2/` | 1.4.1 | 2026-10-13 |
| C08 | Location templates hold topography, vegetation, climate, culture, religion and raw material fields | [V-LOCAL] | `game/in_game/map_data/location_templates.txt` | 1.4.1 | 2026-10-13 |
| C09 | Setup couples locations to pops, countries, markets, roads, institutions, buildings and colonies | [V-LOCAL] | `game/main_menu/setup/1337/` | 1.4.1 | 2026-10-13 |
| C10 | A lexical American-key scan found 104 file categories and 106,418 summed distinct-key/file hits; these are broad candidates with false positives | [V-EXEC] | `uv run rnw coupling GAME_DIR local_data/coupling.json`; raw output gitignored | 1.4.1 | 2026-10-13 |
| C11 | A metadata-only `rnw_exp_*` mod was recognized and its `1.4.*` version matched 1.4.1 | [V-GAME] | Isolated `logs/debug.log` line with `rnw_exp_001_metadata` | 1.4.1 | 2026-10-13 |
| C12 | The isolated user profile entered a Select Language screen and input did not dismiss it; in-game geography was not observed | [V-GAME] | Direct screen observation; game process stopped | 1.4.1 | 2026-10-13 |
| C13 | File-level map overrides, path replacement, new IDs, cache rebuilding, pathfinding and save compatibility are not established | [UNKNOWN] | Required experiments 2–6 not run | 1.4.1 | 2026-10-13 |
| C14 | External preprocessing and a complete mod package are candidate designs, conditional on C13 | [INFERRED] | C03–C11 and experiment ladder | 1.4.1 | 2026-10-13 |
| C15 | Paradox permits noncommercial original user-generated mods, subject to rights and terms | [SOURCE] | https://legal.paradoxplaza.com/eula §§1,5 (accessed 2026-10-13) | Terms dated 2026-01-21 | 2026-10-13 |
| C16 | EU4 Conquest of Paradise advertises a randomized American continent, colonies and native gameplay | [SOURCE] | https://www.paradoxinteractive.com/games/europa-universalis-iv/add-ons/europa-universalis-iv-conquest-of-paradise (accessed 2026-10-13) | EU4; current page | 2026-10-13 |
| C17 | A community engine catalogue targets EU5 1.3.11 and advertises `script_docs`; transfer to 1.4.1 is unverified | [SOURCE] | https://github.com/mattebin/eu5-engine-atlas (accessed 2026-10-13) | 1.3.11 | 2026-10-13 |
| C18 | Future 1.4 patches may change game files or behavior; compatibility must be retested | [SOURCE]/[INFERRED] | https://legal.paradoxplaza.com/eula §3; C01–C13 | 1.4 beta | 2026-10-13 |

Do not infer that a successful version match (C11) proves a mounted gameplay file or that a lexical hit (C10) is a real reference. A more precise script parser and actual map experiments are priority work.
