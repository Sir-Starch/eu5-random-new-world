# EU5 1.4.1 technical findings

This is a read-only investigation of Steam build 25905365 on `1.4-open-beta`, plus one metadata-only startup experiment. Claim IDs refer to the [ledger](claims-ledger.md). Paths are relative to the [installation root](game-install-inventory.md). A file's presence establishes a data dependency, not that a mod can replace it.

## Geography contracts seen in the installation

- [V-LOCAL] `game/in_game/map_data/locations.png` is a 16384×8192 RGB raster; `named_locations/00_default.txt` declares key/color associations, and `definitions.txt` nests location keys under province, area, region, subcontinent and continent (C03–C04). [V-EXEC] The corrected parser counted 28,573 hierarchy keys and 28,582 color declarations, with every hierarchy key covered, nine declarations outside the hierarchy, and no duplicate names or RGB values (C05). [V-EXEC] The raster audit now shows every pixel uses a declared colour and the nine extras are exactly the nine declarations with zero pixels (C23); their engine role remains [UNKNOWN], so exporters leave the colour file untouched.
- [V-LOCAL] `default.map` references locations, rivers, adjacencies, setup and location templates; it contains explicit sea, lake, impassable and non-ownable lists, `wrap_x = yes`, and `equator_y = 3340` (C06,C19). [V-EXEC] Its sea list has 4,793 distinct tokens, lakes 918, impassable 1,868 and non-ownable 153; repeated tokens and 47 sea/impassable overlaps exist in vanilla (C19). Within the American hierarchy, 984 keys occur in sea zones, 292 in lakes, 460 in impassable and 7 in non-ownable lists; categories may overlap. Thus `continent = america` is not a land-only generation mask [INFERRED]. `location_templates.txt` uses `lakes` and wasteland topographies, as well as topography, vegetation, climate, religion, culture and raw material attributes (C08). These files suggest land/sea classification is more than a raster change [INFERRED].
- [V-LOCAL] `rivers.png` matches the location raster dimensions. `gfx/terrain2/heightmap.png` is 8192×4096, while `biomes.png` is 8191×4095; terrain layers, masks, material textures and a terrain cache exist (C07). [V-EXEC] `rivers.png` also carries a water/land background mask (254/255) that agrees with the class lists (C24). `heightmap.png` is not a global aligned layer and has no Americas; the terrain is declared as 65536×32768 with 16 decal height tiles and a checksummed cache (C25). An existing flatmap cache is stored in the user profile. Whether the renderer regenerates any layer or cache for a changed map is unknown [UNKNOWN].
- [V-LOCAL] `adjacencies.csv`, `ports.csv`, `nodes.dat`, `generated_locators_port.txt` and the river image are present. The binary `nodes.dat` is 11 MiB; its semantics, generation path and invalidation are unknown [UNKNOWN]. A navigability or naval-path result cannot be inferred from these file names.
- [UNKNOWN] Minimal mandatory file set for a geometric edit. Working candidate set for a test is `locations.png`, `named_locations`, `definitions.txt`, `default.map` and any dependent setup; then test whether heightmap, rivers, terrain layers, ports, adjacency and caches must be updated. This is an experiment plan, not an exporter contract (C13).
- [UNKNOWN] Fixed map dimensions, maximum location count, permissible new IDs, partial file override and `replace_path` equivalents. No 1.4.1 experiment has touched these.

## Start state and coupling

- [V-LOCAL] `game/main_menu/setup/1337/` contains distinct files for locations, pops, countries, markets, roads, institutions, colonies, religions, development, buildings, diplomacy, wars and situations (C09). `game/in_game/common/` contains culture, religion, goods, topography, climate, vegetation, scripted geography and mission definitions. An RNW exporter must coordinate these for coherent new societies [INFERRED]. The exact minimum for a new playable country is unknown [UNKNOWN].
- [V-EXEC] `rnw coupling` scanned text-like files for tokens equal to American location keys: 104 categories, 106,418 summed distinct-key/file hits (C10). Highest categories included `in_game/gfx/map` (23,141), `main_menu/setup/1337` (8,700), English localization (6,847), `in_game/common/scripted_geography` (126), `in_game/common/on_action` (47), and `in_game/events/DHE` (38). These are **candidate occurrences**, not resolved references: localization and graphics dominate, each file counts a key once, and ambiguous/common tokens or comments can produce false positives. The raw output is in gitignored `local_data/coupling.json` on the research machine.
- [INFERRED] A New World replacement can silently distort event targets, missions, situations, scripted geography, AI preferences, exploration, trade and start setup even if the game loads (C09–C10). Precise counts by system, as well as classifications into log-only errors, dead content, crashes and gameplay distortion, remain [UNKNOWN] until a syntax-aware graph and game tests exist. It would be dishonest to label individual occurrences by failure mode now.
- [UNKNOWN] Checksum, multiplayer and ironman/achievement behavior for generated geography. Treat generated output as version-specific until observed otherwise (C18).

## Mod loading and limits of the experiment

- [V-GAME] An isolated-profile `rnw_exp_001_metadata` mod with `.metadata/metadata.json` and `supported_game_version: 1.4.*` was discovered: the 1.4.1 debug log explicitly reports successful version matching (C11). It contained no game content, so this proves metadata discovery only. The debug log's “No subdirs mounted” message is expected for an empty mod; it does not prove gameplay overrides.
- [V-GAME] The test profile reached a first-run Select Language screen but did not accept input. The game and input helper were stopped after the owner's report; further launches are outside this session's scope (C12). A roughly contemporaneous baseline/current error-log comparison found no new lines, but startup stages and log capture times were not identical; “loads without new errors” therefore remains inconclusive [UNKNOWN]. Startup timing was not measured reliably.
- [V-LOCAL]/[INFERRED] The temporary profile's settings lacked `Game.first_time_playing`, while the normal profile recorded `false` (C22). That difference may explain why the language screen appeared in the temporary profile, but it does **not** explain why mouse input failed. No workaround was verified in game.
- [UNKNOWN] File-level override precedence, partial versus full replacement, new location behavior, unresolved reference response, cache rebuilding and pathfinding. Experiments 2–6 remain pending (C13).

## Integration paths

- [INFERRED] External generation before launch is the leading candidate: the installed game consumes large static rasters and setup files, while no runtime geography API has been verified (C03–C13). A generator could read the player's installation locally, emit a complete `rnw_exp_*` mod, validate it, and have the player enable it in the launcher. Whether that mod can actually override geometry is the top gate.
- [INFERRED] A curated pack of pre-generated worlds or a template patcher might reduce runtime computation but not the map override and rights questions. In-game scripts may handle political rolls after static geography loads, yet no such split is validated.
- [UNKNOWN] One-click launcher/playset integration. The experiment used an isolated playset to test discovery; the normal user's playset was not intentionally changed. Linux/Proton's user directory was found in compatdata; a Windows installation's user path must be discovered at runtime rather than hardcoded. No Steam Workshop publishing or account action was performed.
- [INFERRED] The Old World can only be considered preserved after explicit pixel/identifier invariants, Atlantic/Pacific sea-zone connections, wrap boundary, trade and colonial references, and Old World regression tests pass. None has been demonstrated yet.

## D0 offline generator findings, 2026-10-14

- [V-EXEC] Locators and ports use a flipped row: raster row `8191 - floor(z)` (C26). Exporters can therefore freeze coasts around cities, units, docks, ports and strait endpoints.
- [V-LOCAL] Local Workshop mods use `.metadata/` plus `in_game/`/`main_menu/` at the root (C27). This is layout evidence only; it does not prove that map files override vanilla.
- [V-EXEC] The first geography-changing candidate exists offline (C28–C30). Inside a bounded North-East American window, it moves 16,205 land–sea pixels between existing IDs, keeps every cell contact, and leaves all non-American pixels and outside-window bytes unchanged. Only `locations.png` and `rivers.png` are emitted. It is **NOT GAME VALIDATED**; the drawn terrain will not match because the visual terrain layers are untouched (C25).
- [INFERRED] Contact-preserving T2 edits reshape coasts but cannot add islands or straits (C32). The T3-capable world model and the synthetic generator already create new cells, keys, colours and hierarchy; using that in EU5 waits on the new-ID experiment (005).

## Terrain rendering findings, 2026-10-19

- [V-LOCAL] EU5 draws each location with the biome selected by its template's climate, vegetation and topography; the decal material layer stores slot roles (coast, transition, water edge, border bands, variations), not textures (C50). Generated templates and the slot layer must therefore be coherent with each other, and vanilla's look follows from rules, not hand painting.
- [V-EXEC] Those rules are measurable and reproducible: rebuilding a vanilla crop from vanilla templates matches 85.6% of structural slot pixels (C51). Trees and grass are pre-placed instance lists whose densities follow vegetation and slot; 27–44% of them stood on the removed Americas (C52).
- [V-EXEC] The V1a build ties relief, climate, templates, material slots and vegetation instances to one model; climate and vegetation zones are more coherent than vanilla's, and instance densities per vegetation match the Old World (C53). NOT GAME VALIDATED.
- [V-GAME] V1a loads and renders in 1.4.1; its defects included a crack at the map wrap, short biome material lists and vanilla city ground decals (C55, C56). The engine attribution for the crack was an inference, corrected by C289: the exporter also clamped its sampling and restarted detail noise at the wrap. Generator 0.5.0 avoids the first two; the owner accepted it in game (C58).
- [V-EXEC] Generated rivers follow every measured vanilla raster rule on five seeds over both presets, at vanilla density (C59, C60). NOT GAME VALIDATED.

## Patch-sensitive research leads

[SOURCE] The [EU5 Engine Atlas](https://github.com/mattebin/eu5-engine-atlas) claims `script_docs` and other engine probes, but targets 1.3.11, so its capability list is not 1.4.1 evidence (C17). [SOURCE] The [1.4 update announcement](https://www.paradoxinteractive.com/media/press-releases/paradox-interactive/relive-and-rewrite-the-history-of-spain-and-morocco-in-across-the-pillars) and [Paradox terms](https://legal.paradoxplaza.com/eula) establish that the game changes; all map and script contracts must be fingerprinted by build (C18). The wiki map page was inaccessible and contributed no assertions.

[SOURCE] The [Steam Workshop map/overhaul listing](https://steamcommunity.com/workshop/browse/?appid=3450310&requiredtags%5B%5D=Overhaul) includes a community “More Locations Mod” lead and search results mention a 1.4 beta variant, but no files or gameplay behavior were inspected; this is insufficient to upgrade T3 from unknown. [SOURCE]/[V-LOCAL] [REA](https://github.com/morluto/rea) can coordinate native binary analysis with a provider such as Ghidra, Hopper or IDA; none of those is installed locally, although GNU `objdump` is available for limited static inspection. REA was not installed or run (C21). Static game-file contracts and an eventual controlled game test remain more direct evidence for this project.

## 0.10.0 owner test and 0.10.1 list candidate (2026-10-23)

[V-GAME owner C173] Vanilla TI drawings, including dragons, are now visible in 0.10.0. The scripted lobby filter did not remove the blank list region. [V-LOCAL C174] The exported list still assigns fixed 74-pixel rows to hidden widgets; vanilla lists can use vbox/ignoreinvisible=yes. [INFERRED] Collapsing those widgets' layout space addresses the gap. 0.10.1 generates that layout and removes the failed filter; regression and anchor checks verify the emitted content. [UNKNOWN] The engine's resulting scrolling, card width and list compaction await the owner's run of experiment 032; no agent launch is authorized.

## Mainland-wrap unit hang, 2026-10-26

The original engine-only interpretation below is superseded by the 0.13.5
vanilla identity comparison at the end of this section.

[V-GAME owner / V-LOCAL / V-EXEC C370–C372] In the pinned EU5 1.4.4 executable
(Steam 26142040), the owner reproduces a hang after raising Towa's troops and
unpausing EVXP 0.13.2. A bounded live route capture identifies horizontal
midpoint subdivision using **map height instead of map width**, followed by
normalization by width. Float32 replay matches the erroneous midpoint and
four subsequent bisections exactly. Continuous mainland exposes this engine
defect; the affected location identities are already split at the raster seam.
See [067](../../experiments/067-towa-seam-hang/README.md).

[UNKNOWN C373] A data-only repair retaining full mainland continuity is not
verified. The terrain-crack fix is not isolated as causal; changing spline
encoding or disabling later path tightening is not an established remedy.
No engine/memory patch or geography workaround is shipped. Visual continuity,
offline cylindrical geometry and stable engine unit movement are separate
claims. The first 1341 episode lacks the comparable route capture.

**Correction, 0.13.5 (C374–C378).** [V-GAME owner / V-LOCAL / V-EXEC]
Working vanilla crossings keep one identity on both raster edges. RNW's legacy
generation instead split every crossing cell, manufacturing a straight boundary
and additional adjacency. That is a generator defect; the old refiner trace
does not exclude correcting its input. Removed the split from cell construction
and the land cache. Written EVXP now follows the vanilla identity representation,
removes the specific artificial Towa transition and places the earlier pair's
anchors together in one coordinate chart. Shape, rivers and Old World nonsea
pixels are preserved. [UNKNOWN] Post-fix movement in EU5 remains unobserved.
See [068](../../experiments/068-continuous-location-identities/README.md).
