# 041 - Sea geography: ports, names, topography and currents of the water

2026-10-24, generator 0.10.12, algorithm epoch 22. **NOT GAME VALIDATED, NOT RUN.** Claims C232-C240; design in [sea geography](../../docs/sea-geography.md). It keeps everything of [039](../039-new-world-content-n4/README.md) and [040](../040-colonial-path-probe/README.md) and changes only the water.

## What a world holds

The reference world of epoch 22 (`RNW1-0426C-SYW6B-MW73Y-C0050-R00KR-D6G`, small continents, installed as `mod/rnw_exp_world_mxhxetfs3r`):

| What | Before (0.10.11) | Now |
| --- | --- | --- |
| Ports | one per land cell, the sea it touches longest: 48 coastal sea zones without a port, `bermuda` and `st_helena` without a row | a port for every coastal sea zone (16 of 1,942 sea cells merged to make it possible), 841 rows: 839 generated and the two islets relinked to a generated sea cell |
| Names | 1,942 sea cells, 1,942 names, all `<word> Sea` | 1,926 cells, 233 names: a sea of 99 cells (`X Sea`), four gulfs, 18 bays, a strait, 12 sounds, 81 coasts, 55 capes, 15 island waters, ocean areas named by the game's own keys, areas and provinces named after them |
| Topography | `coastal_ocean` and `ocean` only | 204 coastal, 342 ocean, 1,193 deep, 157 inland sea, 30 narrows |
| Currents | none in the generated water | the game's gyres continued into the 1,193 deep zones (strength 91, the game's 79 to 105) |

## What the log should show

After the world is played anyway, `error.log` should hold none of: `Coastal Seazone 'rnw_sea_…' has no ports connected to it` (96 lines before), `Location 'bermuda' … is coastal but has no port setup`, `Location 'st_helena' …`. The map files as written were read back as the engine reads them and name no zone or land without a port but the Arctic ones that vanilla itself leaves ([C233](../../docs/research/claims-ledger.md)). If a sitting happens anyway, the *Sea Currents* map mode shows the currents of the generated deep water, and the tooltip of a sea zone its name (one name for the cells of a sea).

## Installed

[INSTALLED](../INSTALLED.md). Enabling it is the owner's choice; this record asks for nothing.

## Not for the owner now

This record is not a request (the rule of 2026-10-23: manual testing is rare and in big batches). The engine's verdict on the new water, the names written as `$key$` references and the generated currents is [UNKNOWN] (C239) until a session played anyway is read; strait crossings are not generated (C240).

## Offline evidence

[V-EXEC] `make check` passes (1,199 tests); the reference world's digest `331db1c8…cd23` (793 files) came out the same under `PYTHONHASHSEED` 1 and 7 and in the local test; `RNW_LAYERS=1` passes (rerolling the peoples or the resources changes no map file of the water). The land of the reference world was also rebuilt with five presets (continents, archipelago, supercontinent, islands, small continents) and every coastal sea zone has a port after settling (2 to 28 cells merged), every vanilla coastal sea area has water. [V-LOCAL] the engine's two port rules hold on the game's own map apart from its northern coast.
