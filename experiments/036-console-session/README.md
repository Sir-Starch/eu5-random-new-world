# 036 - One console sitting for N1 to N3

2026-10-23, generator 0.10.5, probe rebuilt. **RUN by the owner on EU5 1.4.4 (17:02 to 17:12): partly useful; its faults are fixed in 0.10.6 and the rest is asked again in [037](../037-console-session-2/README.md).** See *Result* at the end. **Retired probe:** 2026-10-24, owner: the probe mod is retired and its code deleted (`eu5_probe.py`, `rnw probe-hooks`, `tests/test_probe.py`); the player enables the map and nothing else, and anything the game needs sits in the world's mod. This record stays as history. It replaces the owner's steps of [033](../033-new-world-content-n1/README.md), [034](../034-content-hooks-n2/README.md) and [035](../035-new-world-content-n3/README.md) (what each asks and decides stays in those records). Claim C197.

**Rule (owner, 2026-10-23): an experiment during development costs the owner minutes, never a campaign.** Everything that would take decades or a colony is done with the console; whatever the console cannot reach is checked offline or by the agent reading the logs afterwards. Nothing here needs a save, a war or a long wait; the longest step is `run_until` over thirteen game months, which the game runs by itself.

## What the console gives (C197)

[V-LOCAL] The 1.4.3 executable carries a console with these commands (names and one-line help read from the installed `eu5.exe`; the vanilla event `qa_debug_backdrop.1` documents the first): `event <id>` fires an event for the player's country (the vanilla debug event has `trigger = { always = no }` and is meant to be fired this way), `tag <TAG>` makes you another country, `effect <script>` and `trigger <script>` run an effect or test a trigger, `run_months <n>` and `run_until <year> [month] [day]` run the game by itself and pause on arrival, `change_date <year>`, `goto <location>` moves the camera, `conquer`, `conquer_country`, `conquer_area`, `colonize_and_finish`, `make_subject`, `observe`, `helplog` (writes every command with its help into `game.log`), `event_counts`, `enable_all_commands`. [UNKNOWN] the exact argument forms and which of them refuse in a normal single-player game; if a command is refused, run `enable_all_commands` and try again, and tell me what the console answered. The commands are not used by the mod and the mod needs no cheat.

## Before

1. Close the game. In the launcher playset enable the hub with **EIL2** (`RNW: Small continents EIL2`, instead of 6DIV or FX2E) and **RNW probe: content hooks**. FX2E and RI4I are not needed for this sitting.
2. Start a new game as **Bern** (`BRN`), 1337, any speed.

## The sitting (about 15 minutes)

| # | Do | Expect (and what it tells me) |
| --- | --- | --- |
| 1 | Just look at the first event | **Probe: start state** with four lines ("set on FRA", "value on FRA is 7", "set on paris", "value on paris is 3"). H3: the mod's `on_game_start` runs. Close it |
| 2 | `helplog` | nothing visible; the command list lands in `game.log` for me |
| 3 | `run_until 1338 2 1`, click the events that come | within the first months **Probe: the dynamic start** (a hidden event with a certain monthly chance stored Bern in a variable: H7, the way every story starts); take its first option; one or two months later **Probe: the delayed event** (close it); at the first year's end **Probe: the yearly pulse** (H6: hooking the game's yearly pulse from the mod's own file) |
| 4 | Open the formables, form **Probe Realm** (Bern holds both locations from the start) | name *Probe Realm*, flag green and white checks, magenta colour (H1: a tag no country file defines, as the stories' unions need) |
| 5 | Take the decision **Probe: found a subject** | the subject from Interlaken is named *Probe Colony* if the scripted name applies (H2) |
| 6 | `tag ERY`, then `event rnw_story.1001` | the first event of the river story, with three choices. Take the first: embankments. Then `event rnw_river.2`: the ending, a modifier on the city. (If `event` refuses the hidden event: `effect { trigger_event_non_silently = { id = rnw_story.1001 } }`) |
| 7 | `tag SYF`, then `event rnw_story.1005` | the first event of the sacred story. Take the **third** choice: the clergy estate gets the privilege *High Priesthood of the Shrine* at once (look in the estate's privileges) |
| 8 | `tag CLB`, open the formables | **Neekearitagron Union** is on the list with its places counted (30 places, 60 per cent needed) and a name that is not a bare tag |
| 9 | `goto rnw_loc_02594`, select it; then `goto rnw_loc_03934` | the first holds the modifier **Great Silver Lode** (a big silver bonus), the second **Rich Fishing Grounds** |
| 10 | `event_counts`, quit the game | nothing visible; for me |

Steps 6 to 9 are the stories, the unions and the exceptional places of [035](../035-new-world-content-n3/README.md) and [033](../033-new-world-content-n1/README.md); step 3 and the logs also answer the rest of [034](../034-content-hooks-n2/README.md). An optional extra, only if your game is in Russian: read *Probe Realm* declined in a diplomacy tooltip (H4).

## What you tell me

Per row: "ok", or what you saw instead ("5: the name was just INT"), or what the console said. Then I read `error.log`, `game.log`, `debug.log` and the event log myself (they are on this machine): the engine's verdict on every edited file (`always = no` in formable `potential`, scripted names and advances, events, modifiers, localization) is in them, and your eyes are needed only for the table.

## What each outcome decides

- Row 3 shows no dynamic start, or a start without the variable: stories start some other way (a pulse or `on_game_start`); no new family until this is known.
- Row 3 shows no yearly pulse, or the game's own yearly events vanish in `event_counts`: stories cannot hook into the pulse by data (H6, see [034](../034-content-hooks-n2/README.md)).
- Row 4 fails: the unions stay blocked (H1). Rows 6 and 7 fail while 3 works: tuning of the chain, not design.
- Rows 5, 8, 9 and the logs: tuning, and the colonial names (N4) wait for row 5's answer.

## Evidence

[V-EXEC] the probe (`tests/test_probe.py`, 8 tests, and `test_local_hook_probe_anchors_hold`) builds with the miniature story start; the rebuilt `rnw_exp_probe_hooks` is installed with all 21 files hash-identical to the generated tree. [V-LOCAL] the world facts above (bearers, tags, keys) are those of `rnw_exp_world_eil2f6y6cf`'s own `report.json` and mod files. [UNKNOWN] every in-game claim, as before.

## Result (owner's sitting, EU5 1.4.4 executable, 2026-10-23 17:02 to 17:12; claims C198 to C204)

The owner's eleven screenshots, the session's `debug.log`, `game.log`, `gui.log`, `error.log` (and its five rotations), `console.txt` and the autosave written on quitting (a text file: what the sitting changed can be read from it) were read by the agent. The build of the game was no longer the one of the plan: the executable had been updated that morning (C198).

| Row | Result | Evidence |
| --- | --- | --- |
| 1 start state | **Never shown.** The probe's `trigger_event` is no effect of the game (`Unknown effect trigger_event`; the event is logged as orphaned). The variables themselves were set (the save holds `rnw_probe_start`), so a mod's `on_game_start` effect runs, **but instead of the game's own**: the log says `There is more than one 'effect' defined using most recent`, and the vanilla event that only that effect fires (`flavor_bul.7`) is logged as orphaned. The whole vanilla start (area preferences, the catholic church, the Maghreb set-up, the world mod's own rebinding of the Nahuatl seat) did not run in this sitting (C200) | [V-GAME] `debug.log`, save |
| 2 `helplog` | `Commands written to console.txt` | [V-GAME] |
| 3 dynamic start, delayed event, yearly pulse | **Works** (H7, H6): *Probe: the dynamic start* on 1 June 1337 with the variable holding Bern, *the delayed event* on 1 July, *the yearly pulse* on 22 February 1338. That the game's own yearly events go on is not read from the log; only the `effect` of an on_action is replaced by a second definition, the `on_actions` list is not (no warning, and the game's own `ai_personalities_setup.txt` hooks `on_game_start` that way) | [V-GAME] screenshots 2 to 5 |
| 4 formable | **Works** (H1): *Probe Realm* formed (`formed_from=rnw_probe_f`, tag `ZQP`, flag and colour right, *Free City of Probe Realm*); its entry in the formables list showed the key `rnw_probe_f` (and the two unions `rnw_union_1_f`, `rnw_union_2_f`): the game looks up the formable's own key, which the mod had not written (the engine logs each: `localization_util: rnw_probe_f: "Rnw probe f"`) | [V-GAME] |
| 5 found a subject | **Works, the owner did not recognise it.** The decision stood in the list under its bare key (the game looks up `<id>.title` and `<id>.desc`, the probe had `<id>` and `<id>_desc`), so it was not recognised; its red bar is [INFERRED] to be its `allow` failing once Interlaken no longer belonged to the host. The save shows that it was taken on 1 February 1338, the day of the owner's fourth screenshot: a country `AAA22` (`creation_date=1338.2.1`, `reason=ScriptedEffect`, made from `ZQP`) owns Interlaken, with a `vassal` dependency of `ZQP`. Its stored name is the location's key; whether the scripted name *Probe Colony* is applied when it is shown (H2) was not read | [V-GAME] save; [UNKNOWN] H2 |
| 6 river story | `tag ERY`, `event rnw_story.1001`, `event rnw_river.2` work: the three choices, the work levy on the country, embankments and *Safe from the Floods* on the city. The engine says at load that `remove_location_modifier` at `events/rnw_river.txt:107` and `:150` is in the wrong scope (country, not location): the generator wrote it bare (C204, fixed) | [V-GAME] screenshots 6 and 7, `debug.log` |
| 7 sacred story | `event rnw_story.1005` works: two of the three choices were offered (the first needs more than 100 gold, which the state did not have); *Tithe the offerings* shows its gold, its stability and the follow-up event. The estate privilege (third choice) was not taken | [V-GAME] screenshot 8 |
| 8 union | Offered to `CLB` with its places counted (2 of 18 needed, 16 more), but under the key `rnw_union_2_f` instead of a name (C201, fixed) | [V-GAME] screenshot 9 |
| 9 places | *Great Silver Lode* on `rnw_loc_02594` (Ingari) and *Rich Fishing Grounds* on `rnw_loc_03934` (Santicocoyampa) are on the locations | [V-GAME] screenshots 10 and 11 |
| 10 `event_counts` | Written to `logs/event_log.csv`; every count is 0, including events that fired, so it says nothing | [V-GAME] |

Faults of the world mod that the sitting found, all fixed in 0.10.6 (epoch 16): the country list of the lobby (the owner: *many flags flicker hard*; the engine said at load that a percentage `size` on a child of a `vbox` is unsupported at `multiplayer_lobby.gui:4792`, C203), and 79,000 error lines in the session from two vanilla DLC picture files that compare with locations that the world removed (C202; they also filled the log, so that its first minutes rotated away). Other new lines against the vanilla baseline are not faults: three `Variable ... is used but is never set` (the table's *lost* state), `Event rnw_probe.1 is orphaned` and the missing titles of hidden events.

