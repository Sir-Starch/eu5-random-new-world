# 040 - The colonial path: does the scripted name apply to a colony made the game's way?

2026-10-23, probe 0.4.0 (`rnw_exp_probe_hooks`), generator 0.10.10 unchanged. **NOT RUN.** It answers what [038](../038-lobby-list-and-colony/README.md) could not: the scripted country name of a mod did not reach a subject made with `create_country_from_location`, whether the subject was a plain `vassal` (C207) or a `colonial_nation` (C210). The game's own colonies are made another way (C218), and the 70 colonial names of [039](../039-new-world-content-n4/README.md) lean on that way. Claim C221.

**Retired.** 2026-10-24, owner: the probe mod is retired and its code deleted (`eu5_probe.py`, `rnw probe-hooks`, `tests/test_probe.py`); the player enables the map and nothing else, and anything the game needs sits in the world's mod. This record stays as history. The question stays [UNKNOWN] and blocks nothing; if it is ever asked, it is asked from the console of a world mod (`effect` with the body of the charter goal's effect below), not by a mod of its own.

## What changed in the probe

Beside the old decision (*Probe: found a subject*, Interlaken by the vanilla country-from-location effect, kept as the control) there is a second one, **Probe: colonize a free province**. It copies the effect of the game's colonial charter goal `form_colonial_nation` (`colonial_charter_goals/form_colonial_nation.txt`): the best capital location of the province becomes a town (`cc_setup_new_town`), `create_location_country_from_province_definition` makes a `colonial_nation` of Bern (`from = scope:owner`, `capital = scope:new_town`, `setup_colonial_nation`, a mutual truce), with the scopes the goal is given (`owner`, `target`) and its helpers read (`new_town`). The province is `dharug_province` (the Sydney region), which no country holds at the start of 1337 (checked against the installation when the probe is built, as are the five words of the goal and the two helper effects). A second scripted name, *Probe Overseas*, asks for a colony of Bern with its capital in that area; an event then finds the new country (`random_subject` by the area of its capital) and shows the name the game gives it.

## For a sitting of a batch (not a request now)

Start as Bern with the probe and any world enabled; the two decisions are in the infrastructure category.

| # | Do | Expect |
| --- | --- | --- |
| 1 | Take *Probe: colonize a free province* | an event, **Probe: the overseas colony**, naming the colony: *Probe Overseas* if a colony made the game's way gets the scripted name; *Colony of ...* or the location's name if not. Its first option says whether a colonial nation of Bern stands in the province at all |
| 2 | Take *Probe: found a subject* (the control) | as in 038: *Colony of Interlaken* |

Then the agent reads `error.log` and `game.log` for the effect (an unknown parameter or a scope error would be there): that is most of the answer. The two rows take about two minutes.

## What each outcome decides

- *Probe Overseas* shows: the game applies scripted names to its own colonies, and the colonial names of 039 can show in play; the earlier negative (C207, C210) was the effect, not the mechanism.
- The colony is made and keeps the game's name: scripted names are not applied to colonies this way either (or the conditions of the mod's entry were not met); the 70 names stay harmless and the colony stories do not depend on them.
- The effect is refused or logs an error: its scopes are not what the copy gives it; the log names the line. Nothing in a world mod calls it, so no world is affected.

## Evidence

[V-EXEC] `tests/test_probe.py` (18 tests: the anchors and their refusal, the copied effect line by line, the event, the keys) and the two local tests `test_local_hook_probe_anchors_hold` and `test_local_probe_scripts_use_only_words_the_game_uses` pass on the installation; probe 0.4.0 is installed (21 files, [INSTALLED](../INSTALLED.md)). [V-LOCAL] the effect is used once by the game, in the charter goal; `random_subject`, `capital.area = area:` and `province_definition:x = { }` are vanilla forms. [UNKNOWN] everything the engine does with it.
