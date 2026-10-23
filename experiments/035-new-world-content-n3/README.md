# 035 - New World content, N3: the river and sacred pilots

2026-10-23, generator 0.10.5, algorithm epoch 15. **NOT GAME VALIDATED, NOT RUN.** Stage N3 of the [content plan](../../docs/content-plan.md); claims C193-C196. It includes everything of [033](../033-new-world-content-n1/README.md) (N1) and adds the stories.

## What the world holds

Two worlds are installed (0.10.5, epoch 15; both include everything of 033):

- `rnw_exp_world_eil2f6y6cf`, **RNW: Small continents EIL2**, code `RNW1-0426C-SYW6B-MW73Y-C0050-A01QH-7WG` (the reference world of the epoch): **all three families**. River centres: `ERY`, `PZO`, `UWB`, `ZXR`; sacred centres: `SYF`, `WYX`; unions: *Neekearitagron Union* (states `CLB`, `NWX`, `RFC`, `UDS`) and *Taatsaanapeake Union* (`FYC`, `MIN`, `QZZ`, `UWB`, `XJB`). Use this one for the stories.
- `rnw_exp_world_ri4igjvamo`, **RNW: Continents RI4I**, code `RNW1-080G0-00003-EF38N-A0050-A0813-BM0FX-JBZC` (the owner's land of 033): four river centres (`DPF`, `MSU`, `RJT`, `VMI`) and two unions (*Tago Union*, `FGG` `FTX` `FXU` `ZPG`; *Tukri Apu Union*, `RPR` `XUE` `YKO`); **no sacred centre**, because no holy place lies in a state of its own faith there (recorded as an absence in `report.json`).

The plan of a world is in its `report.json` under `text_stats.stories`. Per family:

- **River centre** (`rnw_river.1` to `4`): the state that holds a populous centre on a river gets the first event at a random month of its window (45 years, between 1340 and 1397, a monthly chance of 2 to 5 per cent). Choices: embankments and canals (costs gold, later *The Banks Hold*), river tolls and neglect (later *The River Takes Its Due*), or leaving the banks to the guilds (later *The River Wardens*). Every ending removes the story's variables.
- **Sacred centre** (`rnw_sacred.1` to `4`): the state that holds a holy place of its own faith. Choices: endow the shrine (later *The Shrine Prospers*, a great temple), tithe the offerings (later *The Priests Murmur*), or give the high priest a seat among the estates (later *A Priesthood With a Seat*; the clergy estate privilege *High Priesthood of the Shrine* appears as soon as the choice is made).
- **River-basin union**: a formable named *<Place> Union* of a tag the game does not define, over up to 30 connected river places, offered to the states whose capitals lie among them.

## How the start works

A hidden event per bearer (`rnw_story.1001` and the next ones) is a `dynamic_historical_event` for the bearer's tag: when its month comes, if the bearer still owns the centre, it stores the centre in the variable `rnw_river_centre` (or `rnw_sacred_centre`), shows node 1 and schedules a hidden clean-up 15 years on. The chain events check that the receiver still owns the centre, so a conquered bearer's chain ends by itself and the clean-up removes what is left.

## Steps for the owner

**The owner runs the [console sitting 036](../036-console-session/README.md) (rows 6 to 8), not the steps below: waiting for a natural start takes decades of game time and a union a campaign. The console fires a story's first event at once (`event rnw_story.1001`) and its ending the same way.** Not covered by the sitting and read offline instead: that a conquered bearer's chain ends (step 4; `reachable` and the event guards, `tests/test_stories.py`), and a save in the middle of a chain.

1. Enable EIL2 (or RI4I) with the hub and play any country the plan names. The names are in the world's `report.json` under `text_stats.stories.starts` (`river_centre:TAG`, `sacred_centre:TAG`); the start events are in `in_game/events/rnw_story.txt` of the mod.
2. **Natural start.** Let the game run for decades with a bearer you follow (or watch the AI's through the event log). Note the year each event appears and the options the AI takes.
3. **Forced start** (the console, if the game allows it): `event rnw_story.1001` or the number of a bearer you play, as that country. This tests the effects, not how often a story begins. Take one of the three options, watch the delayed event (a few years later), then its two endings.
4. **Cut the chain.** Take the first choice, then lose the centre (let it be conquered or give it away). The later events must not fire for the old owner; after 15 years the variables should be gone (a variable viewer, if any).
5. **A union.** Play a state named by the formable's `potential`; own 60 per cent of its places, have the capital among them, and form it. Read its name, flag (a solid colour with a checky pattern), colour and rank.
6. **Save and load** in the middle of a chain and finish it.
7. Keep `error.log` and `game.log`. Expect no line about `rnw_river`, `rnw_sacred`, `rnw_story`, an orphaned event, an unknown variable or a missing modifier text.

## What each answer decides

- A hidden dynamic event that does not fire, or fires without the variable: the start has to move (a pulse or `on_game_start`, the hooks of experiment 034).
- A union tag that the game refuses: the union family stays blocked (H1 of experiment 034).
- An accepted chain with costs and endings that read badly: tuning, not design.

## Offline evidence

[V-EXEC] `make check`: 1,038 Python tests; the 13 local tests pass with `RNW_REPRODUCE=1` (reference world of epoch 15, 782 files, `5feec98a8d3488c2f02bf82a3264639158d1468e9f8327e971e7ef038d85f1b1`, code `RNW1-0426C-SYW6B-MW73Y-C0050-A01QH-7WG`) and `RNW_LAYERS=1` passes. The generated scripts read as Paradox script (`rnw.pdx`); that the engine accepts them is [UNKNOWN]. [V-LOCAL] The syntax of each block is that of a vanilla block of the same kind or of the game's documentation (`events/readme.txt`).
