# 042 - Lanes and closed ocean

2026-10-24, generator 0.10.13, algorithm epoch 23. **NOT GAME VALIDATED, NOT RUN.** Claims C241-C244; design in [sea geography](../../docs/sea-geography.md). It keeps everything of [041](../041-sea-geography/README.md) and changes the open ocean only.

## Why

The owner's sitting with 0.10.12 (2026-10-24, three screenshots of 1.4.4) showed what 041 had missed: the game's open ocean is closed to ships (grey on the topography and Naval Range maps) with lines of currents between, while the generated New World's water was teal everywhere with an arrow in every zone (C241).

## What a world holds

The reference world of epoch 23 (`RNW1-0426C-SYW6B-MW73Y-C0050-T00YM-Q00`, small continents, installed as `mod/rnw_exp_world_6rndxwdntf`):

| What | Before (0.10.12) | Now |
| --- | --- | --- |
| Sea cells | 1,942 (1,926 after merges for ports) | 1,226: the 1,193 deep cells are 420 lanes and 36 closed zones |
| Deep ocean | 1,193 cells, each with a current | 420 lane cells, each with the current of the course that ran there |
| Closed ocean | none | 36 zones of `ocean_wasteland` (in `sea_zones` and `impassable_mountains` like the game's 46), at most 746,000 px |
| Reach | all water passable | 1,190 passable generated zones in the one water of 4,500 zones with the game's, read back from the written files |
| Coast of the game's land | Saint Helena's water could be deep ocean | cells beside the game's own land are always coastal water |

## What the log may show

The game's own zones of `ocean_wasteland` are listed like ours, so no new kind of line is expected; if the engine refuses a generated closed zone (C244) it will be in `error.log`. Nothing is asked of the owner.

## Installed

[INSTALLED](../INSTALLED.md). Enabling it is the owner's choice.

## Offline evidence

[V-EXEC] `make check` passes (1,217 tests); the reference world's digest `bec8a9fa…ea23` (793 files) came out the same under `PYTHONHASHSEED` 1 and 7, and the layers test passes; the five presets shape their water (262 to 352 lanes, 29 to 36 zones, 0 to 3 cells added to link, no sealed sea).
