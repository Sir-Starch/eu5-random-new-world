# 039 - New World content, N4: the formable families

2026-10-23, generator 0.10.8, algorithm epoch 18. **NOT GAME VALIDATED, NOT RUN.** Stage N4 of the [content plan](../../docs/content-plan.md), first version (N4a); claims C212-C214. It keeps everything of [035](../035-new-world-content-n3/README.md) (the river and sacred stories, the river-basin union) and adds four more families of formable countries.

## What a world holds

Each world offers the formable families below wherever its land and peoples allow, and records in `report.json` (`text_stats.stories.absences`) why a family has no place. The reference world of the epoch (`RNW1-0426C-SYW6B-MW73Y-C0050-G0432-TXG`, small continents) offers **nine formables** (it offered two before): two of each of the first four families and one realm. The four other presets, made at seed 20261023, offer every formable family too.

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

[V-EXEC] `make check`: 1,066 Python tests and the Rust ones; the reference world of epoch 18 (784 files, `7995b07651d6114f2c932be1fe132840cc33faba73c914dee8c8b29309151b70`) came out the same twice with `RNW_REPRODUCE=1`; `RNW_LAYERS=1` passes with the formables in the compared files (rerolling the peoples changes them, rerolling the resources leaves them byte for byte). The plan was also run on the facts of four more worlds (islands, archipelago, supercontinent, continents; seed 20261023): every formable family is offered in each. [V-LOCAL] The syntax of each entry is that of `ADU` or another vanilla formable (`required_locations_fraction`, `capital_required`, `potential`, `allow`, `locations`, `form_effect` with `set_country_rank_effect` and `add_country_modifier`); `num_of_ports >= N` is used by vanilla decisions; the five emblems and the five modifier sources exist in the installation, and the generator stops if one is gone. [UNKNOWN] that the engine accepts each entry as written, that the formables list shows the families readably, and what the AI does with them.
