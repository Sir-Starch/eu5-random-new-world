# 036 - One console sitting for N1 to N3

2026-10-23, generator 0.10.5, probe rebuilt. **NOT RUN.** It replaces the owner's steps of [033](../033-new-world-content-n1/README.md), [034](../034-content-hooks-n2/README.md) and [035](../035-new-world-content-n3/README.md) (what each asks and decides stays in those records). Claim C197.

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
