# 045 - Varied societies

2026-10-24, generator 0.11.2, algorithm epoch 26. **NOT GAME VALIDATED, NOT RUN.** Claims C251-C253; design in [natives](../../docs/natives.md) (*More varied societies*). It keeps everything of [044](../044-sea-sitting/README.md) and adds four extraordinary societies besides the great empire.

## Why

The content plan lists the maritime, commercial and fractured archetypes as a gap (G7) and asks for "four more combinations of real traits": a maritime trade network, a highland confederation, a fragmented region with several centres, a sacred centre with political competitors. The owner asked for R7d (2026-10-24).

## What a world holds

The installed world `RNW1-080G0-00000-00006-G005G-40813-BM0FH-9J88` (continents, seed 208, `empire_permille` 1000, so every hearth's domain that allows one has one) holds one of each kind, besides 4 great empires:

| Kind | Countries | What is written |
| --- | --- | --- |
| Sea league | `LAK`, `KFK`, `UJP` (5 locations) | the republic of Tlaxcala's template, `land_vs_naval = 60`; a ring of three `scripted_mutual` alliances in `12_diplomacy`; a city and a market at the hub's port, a town at each other's, in `07_cities_and_buildings` and `03_markets` |
| Highland confederation | `NGK`, `XUI`, `TQT` (16 locations) | landed tribes (`own_control_core`, `capital`) with the confederates' `currency_data`; one `tribal_confederation` dated 1337.1.1 in `15_international_organizations` |
| Fractured realm | `DOX`, `KEC`, `YCI`, `GKW` (18 locations) | 8 `rival` records in `20_rivals`, each touching pair both ways |
| Sacred centre | `NGJ` and its competitors `LWH`, `SSF` (11 locations) | `type = theocracy`, `heir_selection = theocratic_elective`, `spiritualist_vs_humanist` and `traditionalist_vs_innovative` at -90; 4 `rival` records |

Every holder of a relation has discovered the area of its partner's capital. A chance of 0 gives the world of 0.11.1 byte for byte (but `.metadata`).

## What the log may show

Whether the engine takes the records is the open question (C253): a theocracy over a monarchy-derived template, tribes of the plain template in a `tribal_confederation`, alliances at the start between countries that met by an area, and rivals beyond a rank's number have no American precedent. A refusal would be a line in `error.log` that names `tribal_confederation`, `scripted_mutual`, `rival`, `theocratic_elective`, `oligarchic_elective`, `land_vs_naval` or `currency_data`, or one of the tags above. A clean log says only that the records parse; what the positions, the mutual defence and the alliances do in play is not read from a log. Nothing is asked of the owner: any session with this world in the playset (an observer game of a few months is enough) is read for those lines.

## Installed

[INSTALLED](../INSTALLED.md). Enabling it is the owner's choice.

## Offline evidence

[V-EXEC] `make check` passes (1,314 tests); the reference world `RNW1-0826C-SYW6B-MW73Y-C005G-40813-G0TQW-2Z` holds two confederations and has the digest `7113a7f6…0662` (792 files) under hash seeds 1 and 7, and the layers test passes; a world at 0 permille is byte-identical to the 0.11.1 export but for `.metadata` (818 files). Every export passes `verify_archetypes`, which reads the written records back against the plan. Of 31 worlds searched with the peoples stage alone, one held all four kinds at 1000 permille: this one.

## The owner's sitting (2026-10-24, 07:07 to 07:15)

The owner played the installed world (`rnw_exp_world_2r7bql6dk3`) as a 1337 game: the lobby at 07:08, a save loaded at 07:08:26, play to 1341.8.12, the autosave at quit at 07:15:42. No console commands and no list was asked of the owner; the logs and the autosave were read afterwards. Claims C254-C256.

- The game stayed up. The average frame delta of the session was 2 to 7 ms (`performance_degradation.log`); the one long frame, 1.58 s, is at the 1337 load.
- The highland confederation is in the save: `tribal_confederation` created 1337.1.1 with NGK (leader), XUI and TQT, as the mod's `15_international_organizations.txt` names them. NGJ (Hopi, a native of this world) is a theocracy with `theocratic_elective`, most likely the sacred centre. The sea league, the fractured realm, and the alliances and rivals are not checked by name yet.
- No engine line names a R7d record (`tribal_confederation`, `theocratic_elective`, `scripted_mutual`, `rival`, `land_vs_naval`) as an error.
- The guard of 0.11.1 did not stop the lobby's errors: 214 `Script system error!` at `common/scripted_guis/rnw_new_world.txt:4`, all at 07:08, before a country was selected (C254). The claim of C249 that it fixed them is wrong. The cause is inferred to be the lobby's `COUNTRY_SELECTED` expression, untested.
- 27,573 map-mode errors in one burst at 07:09:54 (vanilla `map_modes.txt` lines 1620 and 1693, `scope:actor` none), not attributed (C255).
- The duplicate-key warnings of the mod's `replace/` localization file (C256) are unresolved.

Not done: no change to the generated files. A fix of the lobby guard cannot be checked offline: it changes a mod file, so it starts a new epoch and a new reference world, and it needs one short sitting to confirm. Nothing is asked of the owner now.
