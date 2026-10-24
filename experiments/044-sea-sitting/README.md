# 044 - The sea sitting

2026-10-24, 05:05 to 05:13, EU5 1.4.4 (executable; the data of 1.4.3), the owner's own sitting; the agent read the logs and the autosave afterwards. Claims C248-C249. Worlds: 0.10.12's (`rnw_exp_world_mxhxetfs3r`, the launcher's first playset) and 0.10.14's (`rnw_exp_world_5zovefqzyg`, switched to at 05:07).

## What was done

The owner switched the playset in the launcher to the 0.10.14 world, started a 1337 game at 05:08, watched it as an observer to 1337.8.8 (the autosave at quit, 213 MB, holds 1,994 generated locations) and said: "tested, looks good". Nothing was asked of the owner beforehand and nothing is asked now.

## What the logs say

| What | The 00:50 session (0.10.11 world) | This session (0.10.14 world) |
| --- | --- | --- |
| `Coastal Seazone ... has no ports connected to it` | 48 zones | 0 |
| `Location ... is coastal but has no port setup` | 2 (Bermuda, Saint Helena) | 0 |
| anything naming adjacencies, `ocean_wasteland`, topography, `movement_assistance`, `rnw_sea_`, `rnw_loc_` | 0 | 0 |
| `rnw_new_world.txt:4` script errors (a country that is none) | 263 | 263 |

The 00:50 log is the 0.10.11 world's (every zone it names lacks a port in that world, and its `Possible ones` match that world's adjacency; 8 of the 48 zone keys have a row in the 0.10.12 world). The other lines of this session's `error.log` are the game's and the DHE scripts' own (`battle_for_the_strait`, `golden_century`, `gc_change_colonial_dominance`) and appear in the old baselines too.

## What it settles, and what it does not

Settled: the port lines are gone; the engine took the closed zones, the lanes and their currents, the narrows and the crossing rows without a complaint; the owner found the map good. Not settled by a look: whether ships keep out of the closed zones, what an army does at a crossing, what the Sea Currents map shows (C244, C247). The 263 errors of the lobby's scripted GUI (C249) are a fault of the lobby's GUI, not of the sea work.

## What it led to

Two messages of this session's `error.log` that the 0.10.11 world's did not have were the sea work's or the lobby's own: the combat and unit-stack locators "incomplete" (the closed zones had locators, which the game's closed ocean lacks, C250) and the lobby's scripted GUI asked about no country (C249). Generator 0.11.1 (epoch 25) gives the closed zones neither locator and guards the scripted GUI; the reference world `RNW1-0826C-SYW6B-MW73Y-C005G-20813-G0HNQ-QV` (792 files, digest `0b2efd8a…9f54`) is installed as recorded in [INSTALLED](../INSTALLED.md). Whether both lines are gone is read from the next session's log; nothing is asked.

