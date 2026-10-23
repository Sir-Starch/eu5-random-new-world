# 034 - Content hooks, N2: a mod-defined tag, scripted names, start variables

2026-10-23, probe `rnw_exp_probe_hooks`. **NOT RUN.** Stage N2 of the [content plan](../../docs/content-plan.md); claims C191-C192. The agent prepared and installed the probe; the owner runs it. No agent launch.

The probe is a small research mod, not a world: 21 files, English texts in all eleven languages, made by `rnw probe-hooks GAME_DIR generated/rnw_exp_probe_hooks` from the installation (every vanilla anchor it leans on is checked first, and a missing one stops the build; `test_local_hook_probe_anchors_hold` repeats the check on a patch). It uses vanilla tags and locations only (Bern, Interlaken, France, Paris), so it runs on the vanilla map and on any generated world.

## What it asks, and the vanilla precedent for each

| # | Question | Precedent (offline) | What the probe does |
| --- | --- | --- | --- |
| H1 | Does a tag that no country file defines, first seen in a mod, behave like the vanilla formable-only tag `ADU` (C175)? | `ADU` has a formable, a flag definition, a coat of arms, a named colour and name and adjective keys, and no country definition | `ZQP` with exactly that set: formable `rnw_probe_f` (level 3, locations `bern` and `interlaken`, available to `BRN`), flag definition, coat of arms, `map_ZQP`, `ZQP` and `ZQP_ADJ` |
| H2 | Is a scripted country name of the mod's own taken, and when is it re-evaluated: after a capital move, an overlord change, independence, a manual rename (C180)? | `scripted_country_names/00_default.txt` (triggers on overlord, capital and locations; text under the entry's own key and `_ADJ`) | `rnw_probe_colony_scripted_country_name`: a subject of `BRN` or `ZQP` whose capital stands in `central_switzerland_area` is *Probe Colony*; a decision founds such a subject from Interlaken with vanilla's `create_country_from_location` and `make_subject_of` |
| H3 | Does a mod's `on_game_start` run beside the game's own, and do variables set there on a country and on a location survive a save and a load? | EU5 keeps all state in variables (`set_variable` 3,497 uses, `has_variable` 4,721; no `set_country_flag` anywhere, C191); `on_game_start` in `on_action/_hardcoded.txt` | the mod's `on_game_start` sets `rnw_probe_start` to 7 on France and to 3 on Paris and shows an event to Bern; a decision shows it again |
| H6 | Can a mod hook a story into the game's yearly pulse from its own file, so stories follow the current owner and not a 1337 tag? | `yearly_country_pulse` fires sub-on-actions with a cheap outer `trigger` (`yearly_flavor_ven_pulse` and nine more in `country_yearly.txt`); `on_actions.info` does not say what two files defining the same on_action do | `rnw_probe_pulse` (trigger `BRN` or `ZQP`, fires `rnw_probe.2` once), listed in a `yearly_country_pulse` of the mod's own file |
| H4 | Do the Russian case forms of a tag without any fall back to *державы X* (C176)? | `fallback = yes` in `ru_EU5_custom_loc.txt` | the name `ZQP` exists in Russian; read it declined in a diplomacy button |
| H5 | Does `country_flavor` give a vanilla title to such a tag? | `customizable_localization/country_ranks.txt` picks by government, rank and subject type | the formed `ZQP` has level 3 and Bern's republic government: read its title in the country panel |

## Steps for the owner

1. Enable `RNW probe: content hooks` in the playset (the agent did not change any playset). It can be played with the vanilla map or with FX2E of [experiment 033](../033-new-world-content-n1/README.md). Start a game as **Bern** (`BRN`, a county in Switzerland).
2. **H3.** At the start an event "Probe: start state" opens with options that show only when they hold: *The variable is set on FRA*, *Its value on FRA is 7*, *The variable is set on paris*, *Its value on paris is 3*. If it says *Neither variable is set*, the mod's `on_game_start` did not run. Close it, save, quit, load, and open the decision list: **Probe: read the start state** shows the same event again from the loaded game.
3. **H1.** In the formables list, **Probe Realm** should be offered (it needs `bern` and `interlaken`). Form it. Check the name (*Probe Realm*, adjective *Probe*), the flag (green and white check pattern), the map colour (magenta) and the saved game after a load. Note any `error.log` line about `ZQP`.
4. **H2.** With Bern or Probe Realm, take the decision **Probe: found a subject**, which makes Interlaken a subject. Read its name (*Probe Colony* if the scripted name applies). Then, where the interface allows it, try one at a time and read the name after each: move its capital out of the area; transfer it to another overlord; release it; rename it by hand and then do one of the others. Record what each did.
5. **H4.** Set the game language to Russian (the launcher's or the game's setting) and read *Probe Realm* declined in a button or tooltip of diplomacy toward it (*… державы Probe Realm* expected).
6. **H6.** Within the first game year the event "Probe: the yearly pulse" should reach Bern. If instead the game's own yearly events (flavor events of other countries, price events) stop happening, the mod's `yearly_country_pulse` replaced the game's instead of adding to it: stop, and tell me.
7. **H5.** Read the title of Probe Realm in the country panel (a title from the government and rank, not a bare name).
8. Keep `error.log` and `game.log` of the run. Remove the probe when done: with the game closed, `uv run rnw uninstall-mod rnw_exp_probe_hooks --user-dir USER_DIR`.

## What each answer decides

- H1 fails: no new formable tag in a generated world; N3's River-basin union and N4's formables stay blocked (the plan keeps `ZQP`-like tags out and falls back to nothing: a rejected branch stays blocked).
- H2 fails: no world-specific colonial names (N4); the vanilla default stays. If the name is not re-evaluated after a capital move, the catalogue keys on the founding area through a variable set at foundation.
- H3 fails: stories cannot be bound at the start; they would have to be bound by events at first contact.
- H6 fails (replace instead of add, or no event): stories cannot hook into the yearly pulse by data; the alternative is a generated copy of the game's `country_yearly.txt` with one added line, a minimal change to a game file made from the installation at generation time, as the rule for features the game lacks allows.
- H4 and H5 do not block anything; they decide whether generated native names read well in Russian and which titles they carry.

## Offline evidence

[V-EXEC] `tests/test_probe.py` (anchors, files, syntax; each moved anchor stops the build) and the local anchor test pass. The 21 files read as Paradox script (`rnw.pdx`); that the engine accepts them is [UNKNOWN] until the run. [V-LOCAL] The syntax of every block is copied from a vanilla block of the same kind (`ADU`, `00_default.txt`, `canal_construction.txt`, `tunis_effects.txt`, `_hardcoded.txt`, `thalassocracy_events.txt`).
