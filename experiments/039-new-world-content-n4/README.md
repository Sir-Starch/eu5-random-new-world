# 039 - New World content, N4: the formable families and the first four stories

2026-10-23, generator 0.10.8 (N4a) and 0.10.9 (N4b), algorithm epochs 18 and 19. **NOT GAME VALIDATED, NOT RUN.** Stage N4 of the [content plan](../../docs/content-plan.md); claims C212-C217. It keeps everything of [035](../035-new-world-content-n3/README.md) (the river and sacred stories, the river-basin union). N4a adds four more families of formable countries, N4b four more stories (below).

## What a world holds

Each world offers the formable families below wherever its land and peoples allow, and records in `report.json` (`text_stats.stories.absences`) why a family has no place. The reference world of epoch 18 (`RNW1-0426C-SYW6B-MW73Y-C0050-G0432-TXG`, small continents) offers **nine formables** (it offered two before): two of each of the first four families and one realm. The four other presets, made at seed 20261023, offer every formable family too.

| Family | Territory (connected places) | Offered to | Level and rank | Asks | Gives (copied from a vanilla modifier, a name of the mod's own) |
| --- | --- | --- | --- | --- | --- |
| River-basin union (N3) | up to 30 places a river serves | states whose capital lies in it | 3, kingdom | 60 per cent of the places | *Markets of One River* (10 years) |
| Highland confederation | up to 24 places on mountains, hills or plateau, a third of them mountains or plateau | idem | 2, duchy | 60 per cent | *Compact of the Valleys* (20 years) |
| Maritime league | up to 18 coastal places, joined by land or by a sea zone they share | idem | 2, duchy | 60 per cent and at least three ports (`num_of_ports >= 3`) | *Charter of the League* (20 years) |
| Cultural commonwealth | up to 30 places whose main culture is in one vanilla culture group, the narrowest group of the seat's culture that the world has twelve places of | idem | 3, kingdom | 50 per cent | *One People* (20 years) |
| Regional realm | up to 48 places of any kind | idem | 4, empire | 50 per cent | *Administration of the Realm* (15 years) |

A territory has at least the centres, places and states of its family's rule (`content.RULES`); at most eight states are offered it (the ones with the most places in it), and a state sees it only if it owns a place of it (the game's default). Territories of one family never overlap; those of different families may, since each is another political path over the same land and the levels order them (a country forms only a formable above its own level, so there is no circle). The names read *<seat> Union*, *Confederation*, *League*, *Commonwealth* and *Realm*; each has a flag of one emblem of its own (a checky field, a mountain, an anchor, a rosette, a star), a map colour and a name and an adjective in every language.

## Not for the owner now

This record is not a request. The next console sitting of a batch may take two minutes for it (`tag <TAG>` of a bearer named in `report.json`, open the formables list: each family's formable with its places counted, the name, the level; the league should show its ports requirement). Until then the runtime result stays NOT-RUN and the logs of any sitting played anyway are read for lines about `rnw_*_f`, `rnw_confederation`, `rnw_league`, `rnw_commonwealth`, `rnw_realm` and `rnw_union`.

## Offline evidence

[V-EXEC] `make check`: 1,066 Python tests and the Rust ones; the reference world of epoch 18 (784 files, `7995b07651d6114f2c932be1fe132840cc33faba73c914dee8c8b29309151b70`; superseded by epoch 19 below) came out the same twice with `RNW_REPRODUCE=1`; `RNW_LAYERS=1` passes with the formables in the compared files (rerolling the peoples changes them, rerolling the resources leaves them byte for byte). The plan was also run on the facts of four more worlds (islands, archipelago, supercontinent, continents; seed 20261023): every formable family is offered in each. [V-LOCAL] The syntax of each entry is that of `ADU` or another vanilla formable (`required_locations_fraction`, `capital_required`, `potential`, `allow`, `locations`, `form_effect` with `set_country_rank_effect` and `add_country_modifier`); `num_of_ports >= N` is used by vanilla decisions; the five emblems and the five modifier sources exist in the installation, and the generator stops if one is gone. [UNKNOWN] that the engine accepts each entry as written, that the formables list shows the families readably, and what the AI does with them.


## N4b: four more stories (0.10.9, epoch 19)

The same hidden start as the pilots (a `dynamic_historical_event` bound to the bearer's tag, in a window of 45 years between 1340 and 1397, a monthly chance of 2 to 5 per cent, if the bearer still owns the place), now with a second place where the story is about two: the start stores both in variables and a chain event is asked only while the bearer owns the first (and, for a route, the second too). A story ends by an option that removes its variables; a cleanup 15 years on removes what an interrupted one left. A state bears at most two chains in all, begins at most one story a year, and each family draws from a stream of its own, so adding these four moved none of the older stories (they are planned after the pilots).

| Family | Bearer and places | The story (four events, six endings) | Draws on (payloads copied from vanilla, names of the mod's own) |
| --- | --- | --- | --- |
| Harvest and food supply | a centre of a state on high ground or among the most populous tenth; up to three | *A Thin Harvest* cuts the province's food by a fifth, then: buy grain, ration and requisition, or open new fields; later the grain merchants ask for a charter, the villages remember the levy, or the new fields bear | grain, rationing, new-field, granary and shared-field location modifiers; the merchants' charter |
| Route and market | a state with two centres 2 to 8 steps apart over its own places; the two ends; up to three | *A Road Between Two Cities*: a paved road, a toll charter for the merchants, or market days at the crossings; later the road is open, the tolls grow heavy, or the fairs | road works, tolls, fairs and market-day modifiers |
| Great alliance | a state and a neighbour that shares its faith or the culture of its capital, neither the other's subject; the two capitals; up to three | *Envoys From the Next Valley*: a council of equals, protection for deference, or a polite refusal; each with opinions of both courts (`add_opinion_mutual_effect`) and later events | council, trust, pressure, closed-door and kinship modifiers |
| Empire and periphery | a state with subjects; its capital and the capital of its most distant subject; up to two | *The Far Provinces*: a governor and a garrison, a charter of customs, or settlers; later the governor takes root, the charters multiply, or the settlers quarrel with the old families | governor, charter, concessions and settler modifiers |

In the reference world: three harvests, three routes, three alliances and two empires; the four other presets (seed 20261023) offer the same numbers. `report.json` lists them under `text_stats.stories.starts` (`<family>:<tag>`).

### Offline evidence (N4b)

[V-EXEC] `make check`: 1,108 Python tests; the reference world of epoch 19 (788 files, `493f5e3babbc860b48eb29b2f76f9deefab819827a0a5527eeb93bab671337d2`, code `RNW1-0426C-SYW6B-MW73Y-C0050-J00M9-XRG`) came out the same twice with `RNW_REPRODUCE=1`, and `RNW_LAYERS=1` passes (rerolling the peoples changes the stories and formables, rerolling the resources leaves them). The new local test `test_local_story_scripts_use_only_words_the_game_uses` checks that every effect, trigger and key the stories write is a word of the game's own scripts. [V-LOCAL] The location-to-province scope (`scope:x.province = { }`), `province_food_percentage` and `change_province_food_percentage` are used by vanilla events in province scope, `add_opinion_mutual_effect` is a vanilla scripted effect, `remove_country_modifier = name` and `owner = { }` in effects are vanilla forms. [UNKNOWN] that the engine accepts the new events as written, the variables holding a second place, the harvest event's food cut, the opinion effects, and how the AI chooses.
