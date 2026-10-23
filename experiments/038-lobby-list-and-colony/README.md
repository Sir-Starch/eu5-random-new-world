# 038 - The lobby's list without hiding, and the colony's name

2026-10-23, generator 0.10.7, algorithm epoch 17, probe 0.3.0. **RUN by the owner (19:00 to 19:03): the flags no longer flicker; the colony works and keeps the game's own name for a colony, not the scripted one; see *Result*.** It answers what [037](../037-console-session-2/README.md) left: the flags of the country list flicker and a search brings back the blank stretches (C205), and a plain vassal keeps the name of its location (C207). About five minutes.

## What changed

- **The list is the game's own again.** 0.10.1 to 0.10.6 hid the cards of the New World, first in the game's fixed grid (a blank stretch), then in a vertical list that leaves hidden cards out (flags flickered, blank stretches in a search). From 0.10.7 the grid is untouched and every card is there: a New World country is **dimmed and cannot be chosen** (the click is disabled; the start and join buttons still refuse it, as before). The names of those countries are therefore visible in the list.
- **The probe** (0.3.0) founds Interlaken as a `colonial_nation` subject, the type of the game's own colonies, and shows the name the game gives it.

## Before

Close the game. In the launcher playset keep the hub and **RNW probe: content hooks**, and enable **RNW: Small continents KPJM** (`rnw_exp_world_kpjmspjsw3`, code `RNW1-0426C-SYW6B-MW73Y-C0050-E01PQ-P70`) instead of PRJ3. Same land and peoples as before.

## The sitting

| # | Do | Expect (and what it tells me) |
| --- | --- | --- |
| 1 | On the new-game screen open the country list; scroll it slowly and fast, from the top to the end | **No flicker of flags anywhere.** The countries of the New World stand in the list, dimmed. Tell me if some flicker still and where (the dimmed ones only? the first screens only?) |
| 2 | Click a dimmed country; double-click one | Click: nothing is chosen. Double-click may still move the map to it |
| 3 | Search `Bern`, then another name, then clear the search | The results stand next to one another with no blank stretch |
| 4 | Start as **Bern**, take the decision **Probe: found a subject** on the first day | The event **Probe: the new subject** gives the name of the subject (*Probe Colony* if the scripted name applies to a colonial subject, else *Interlaken*) and its adjective. Tell me which, and read the name once more in the diplomacy list |
| 5 | Quit | I read the logs and the save |

## What each outcome decides

- Row 1 clean: the list is done. Row 1 still flickers in the dimmed cards only: the flags of the dimmed cards are drawn by a state of the engine that I did not expect, and the next try masks them. Row 1 flickers everywhere: it is not our change but the build 1.4.4 itself, and I compare with a game without the mod.
- Row 4 *Probe Colony*: colonial names (N4) bind to the colonial subject type. *Interlaken* again: the game applies the scripted names by another path (the colonization of the game itself), and N4 is redesigned around the game's own colonization.

## Evidence

[V-EXEC] `make check` passes; the reference world of epoch 17 (784 files, digest `2ee00cf1...3d10f`) differs from PRJ3 in the lobby GUI alone, whose differences from the game's file are now a `visible` of the selected-country panel, an `alpha` and an `enabled` of the card, and the guards of the start and join buttons. [UNKNOWN] everything in the table. The `alpha = "[TransparentIfFalse(...)]"` and `enabled` of an `action_tooltip` follow vanilla precedents (`bureaucracies_lateralview.gui`, `select_interaction_target_widgets.gui`); that they dim and disable a card of this list is not known until the log and the owner's eyes say so.

## Result (owner, EU5 1.4.4, 2026-10-23 19:00 to 19:03; claims C209 to C211)

The owner reported *the countries do not flicker, the colony works* with one screenshot; the agent read `debug.log`, `game.log`, `gui.log`, `error.log` and the autosave. The game was launched with PRJ3 and the playset was switched to KPJM at 19:00:49.

| Row | Result | Evidence |
| --- | --- | --- |
| 1 flicker | **Gone** (C209). `gui.log` has no validation line for `multiplayer_lobby.gui` at all | [V-GAME] owner, `gui.log` |
| 2 click | **Works** (owner, afterwards): the cards of the New World are grey and a click chooses nothing; a double click still moves the camera to the country's place, which the owner accepts (no fix wanted, C209) | [V-GAME] owner |
| 3 search | Not reported: whether a search leaves no blank stretch is not known; the log has no GUI error | [UNKNOWN] |
| 4 colony | The decision made Interlaken a subject of type `colonial_nation` (the save: country `AAA11`, created 1337.7.31, `subject_type=colonial_nation`; the diplomacy tooltip: *Colonial Nation of Bern*, loyalty 81.46 per cent, a governor of Bern's court). The name the game shows is **Colony of Interlaken**: the game's own title for a colonial nation, built from the location. **The scripted name *Probe Colony* is not applied** to it either; the save stores `country_name="interlaken"` (C210) | [V-GAME] screenshot, save |
| log | No `SET_CAPITAL_EFFECT`, no scope, key, picture or orphan line; the errors left are the vanilla ones of the baseline (the tributary subject type, the cabinet action, the coastal sea zones of generated land) | [V-GAME] `error.log` |

What this decides (C210, C211): the scripted country names of the game are not reached by `create_country_from_location` with `vassal` or with `colonial_nation`, so the plan cannot give a colony of a generated world a name of its own by a scripted name made for this; a colony of a generated world gets *Colony of <its location>* from the game itself, which is a fitting name on land that no vanilla colony name belongs to. N4's colonial names are therefore only the game's default unless another path shows a way (the colonization of the game itself, which the scripted names are written for, is [UNKNOWN] and needs a colony settled the game's way).

