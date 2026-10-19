# Start economy (phase R7)

**Status:** R7a implemented on 2026-10-19 (product version 0.9.2, claims C73–C75), NOT GAME VALIDATED. Designed in [sonnet-r7a-development](handoff/sonnet-r7a-development.md); it passes the offline acceptance on three worlds (C75); in-game test pending (experiment 012). It covers start development, harbour suitability and market villages. Institutions, roads, other buildings, technology and extraordinary societies are open work.

## Goal

Product rule: strength comes from population, land and organisation, not flat modifiers ([product spec](product-spec.md)). The vanilla 1337 Americas get their start economy from the development rules of `14_development.txt` plus pops, ranks, markets and a few buildings [V-LOCAL C73]. R7a keeps those rules and changes only their inputs, so the generated world uses the same model for the map, the societies and the economy.

## How vanilla sets it up

- Development of a location is the sum of `base`, `coastal` × harbour suitability, `river` × river size, `road`, `city`/`town`, vegetation, climate and topography values, and entries keyed by region, area, province or location (C73).
- The Americas take their civilisation level from the keyed entries (Mesoamerica 12, Andes 10, Central America 9, Aridoamerica and Colombia 7, Great Plains 5, Cahokia +7 and so on). The maximum keyed sum of any American land location is 12.
- The 1337 Americas have no institutions and no roads. Their 88 buildings include 79 `market_village` in 79 of 223 state capitals (35.4%).
- Harbour suitability has 1,092 values in the Americas: 758‰ are 0.00, 13 are −0.10 and the mean is 0.101.

## What was wrong before 0.9.2

The generator kept the 14 American region entries, and generated regions reuse vanilla keys by position. The bonus therefore followed the old positions, not the generated societies; cities got none, and 55% of the keyed development landed on unorganised land. Every generated port got harbour 0.50 (C74). A negative harbour value in a donor template also stayed beside the new one, because the regular expression that removed it did not match a minus sign.

## Algorithm (implemented in `eu5_development.py`)

| Stage | Method |
|---|---|
| Calibration | `calibrate` parses the vanilla setup texts and templates: the rules, the maximum keyed sum `B` (12), the sorted American harbour values, the share of American state capitals with a market village (354‰) and the estimated mean development per class. |
| Positional entries | `eu5_rewrite.drop_block_entries` removes every entry keyed by a region, area, province or location of the vanilla New World from the `development` block. `vanilla_new_world_keys` fails the export if a kept vanilla location lies under one of them. |
| Society term | `society_term`: `(B × level + 500) // 1000` per generated land location, with level = `min(1000, complexity × 1000 // full)` and complexity the permille level of the society model. `fit_full` picks `full` per world among 250…3000 (step 5): the smallest candidate for which the estimated mean development of state capitals and members together comes closest to the vanilla mean (`FULL_CANDIDATES`). Only terms of 1 or more become `<key> = <n>` lines; `full` is reported as `society_full_permille`. |
| Harbours | `shelter` casts 48 integer-direction rays of 64 px from each port's dock on the final world raster (columns wrap, lakes count as water) and counts those that meet land. `harbour_values` sorts the ports by (score, key) and takes the vanilla value at index `(2i + 1) × m // (2n)`. Shelter predicts vanilla values only weakly (Spearman 0.10–0.19, C74), so the distribution is what is reproduced. |
| Market villages | `market_villages` gives the vanilla share of generated state capitals one level-1 `market_village`, most complex first, ties by population then key. |
| Output | `14_development.txt` gets the dropped entries and the term lines; `07_cities_and_buildings.txt` gets the village lines in `building_manager`; location templates carry the harbour values of ports only. |

Choices marked [INFERRED design]: a term that follows complexity and saturates at a level fitted per world, the use of shelter to order harbours, and the choice of village capitals by complexity. The fit exists because vanilla's keyed entries lift state land to a similar level on any terrain (Mesoamerica +12 on jungle, Great Plains +5), whereas the physical rules give generated state land different development per world. Copying vanilla's per-class bonus would have given states 8.7–10.6 against 4.1 (C74); a purely linear term left continents states at 0.63–0.73 of the vanilla mean and a fixed saturation of 800 permille left archipelago 5 states at 1.55 (C75).

## Results (C75)

On continents 3706823338, archipelago 5 and continents 515055336 the estimated mean development of state members is 4.42, 4.31 and 4.33 (vanilla 4.13) and of state capitals 4.13, 4.42 and 4.40 (vanilla 4.60). Tribes and unorganised land stay under 0.3 (vanilla 1.14 and 0.70). The fitted saturation is 760, 1115 and 810 permille. Towns (3.05–6.55) and cities (7.80–9.71) lie below vanilla (6.13, 12.22) because they stand on poor land; this is watched, not a criterion.

## Settings

None. Presets (R8) will own a development control.

## Checks

- Synthetic tests (`tests/test_development.py`): decimals and signs; templates with nested blocks; calibration on a small setup; terms, harbour quantiles, shelter geometry (including the map wrap), village choice, rank correlation; line insertion; `drop_block_entries`; `verify_development` accepts the plan and rejects a kept New World entry, a repeated key, a sea key, a value above `B`, a harbour on a location without a port and a village outside its capital.
- Export invariants (`verify_development`): the checks above on the final texts.
- `tests/test_local_install.py` reads the vanilla calibration (`B = 12`, 1,092 harbour values, 354‰).
- `report.json` section `development` holds `B`, the entry count, the share of land with a positive term, the rank correlation of term and population, harbour histograms, village counts and the estimated mean development per class for the generated world and for vanilla. The estimate is a clamp-at-zero sum without the river term (the engine's river size is unknown).

## Open work

- Institutions, roads and other buildings (terraces, walls, culture buildings).
- The river term in the estimate and the effect of `development` on pops after the start.
- Technology and institution spread per society; extraordinary societies (R7 proper).
- Whether the engine honours entries for new keys (experiment 012).
