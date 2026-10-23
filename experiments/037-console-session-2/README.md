# 037 - The second console sitting: what 036 left open

2026-10-23, generator 0.10.6, algorithm epoch 16, probe rebuilt. **NOT RUN.** It asks again what [036](../036-console-session/README.md) could not answer because of the faults it found (C200 to C204), and nothing else. About ten minutes. Claims C198 to C204 give the reasons.

## Before

1. Close the game. In the launcher playset keep the hub and **RNW probe: content hooks**, and enable **RNW: Small continents PRJ3** (`rnw_exp_world_prj3zj4whq`, world code `RNW1-0426C-SYW6B-MW73Y-C0050-C075Q-E4G`) *instead of* EIL2. It is the same land and the same peoples as EIL2 (the tags `ERY`, `SYF`, `CLB` and the places are unchanged); the files that differ are the lobby list, the river events, the story texts and two DLC picture files.
2. Launch the game as before. Everything else of the sitting is typed in the console (`~`), as in 036.

## The sitting

| # | Do | Expect (and what it tells me) |
| --- | --- | --- |
| 1 | On the new-game screen open the country list. Scroll it slowly and fast, search `Ber` and clear the search | No flicker of flags (the engine no longer reports an unsupported size at load; if flags still flicker, tell me *when*: at once, only while scrolling, only far down the list). The list has no blank stretch and no New World country |
| 2 | Start as **Bern** (`BRN`), 1337 | The first event is **Probe: start state** with four lines (H3: the mod's start hook runs *beside* the game's own start, which now has its turn: no `flavor_bul.7 is orphaned` in the log) |
| 3 | Open the decisions: **Probe: found a subject** is listed under that name. Take it | The event **Probe: the new subject** names the subject as the game shows it: *Probe Colony* if the scripted country name applies (H2), else *Interlaken*; its adjective too. Tell me which |
| 4 | Open the formables | **Probe Realm** under that name (not `rnw_probe_f`) |
| 5 | `tag CLB`, open the formables | The union listed by a name (*...Union*), not `rnw_union_2_f`, with its text |
| 6 | `tag ERY`, `event rnw_story.1001`, take the **second** choice (squeeze the river trade) | Nothing visible; the story records that the river silts |
| 7 | `event rnw_river.3`, take the first choice (clear the channels; it needs more than 100 gold: `effect { add_gold = 500 }` first if it is not offered) | The silt modifier is removed from the city with no error (the engine said at load that this effect was in the wrong scope) |
| 8 | `goto rnw_loc_02594`, select the location, open its panel; look at two or three other locations (an Old World one with a famous monument if you like) | Nothing visible. The log must be free of `Invalid right side during comparison 'location'` (79,000 lines in 036) |
| 9 | Quit | I read `error.log`, `game.log`, `debug.log`, `gui.log` and the autosave |

## What each outcome decides

- Row 1 still flickers: the list is a `vbox` of every country of the game (2,900 cards), where the game's own big lists are fixed-row grids (`countries_list_view.gui`), and the flags are probably drawn for every card at once. Then the lobby needs another way to leave the New World out of the list than hiding cards, and the answer waits for what the log says (C203).
- Row 3 *Probe Colony*: the plan of N4 (colonial names bound to the generated hierarchy) is possible; *Interlaken*: the scripted name needs another trigger or a later moment, and N4 waits.
- Row 2 shows the four lines: stories and unions may be bound at the start of a game by a sub-on-action (the pattern the game's own `ai_personalities_setup.txt` uses).
- Row 5 or 4 still bare: the key convention for formables is not the one the engine log suggests.

## Evidence

[V-EXEC] `make check` passes (1,048 Python tests, 23 Rust tests); the reference world of epoch 16 (784 files, digest `84d0787b...ec2ad46`) is made again from the installed game; against EIL2 the new world differs in exactly the lobby GUI, `rnw_river.txt`, the eleven story localizations, the two DLC picture files and the metadata. `rnw content-inventory` on the installation: 636 consumers, 0 undecided, 0 stale. [UNKNOWN] everything in the table.
