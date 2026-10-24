# Start economy (phase R7)

**Status:** R7a implemented on 2026-10-19 (product version 0.9.2, claims C73–C75) and revised after an audit (0.9.3, C76), NOT GAME VALIDATED. Designed in [R7a design](r7a-development.md); in-game test pending (experiment 012). It covers start development, harbour suitability and market villages. Technology (R7b, 0.9.28, C159) and great empires with causes and weaknesses (R7c, 0.9.29, C160, including their royal roads) are implemented offline and described in [natives](natives.md); institutions, ordinary roads and other buildings are open work, and the R7 gate (a region plays through exploration, colonisation and conquest without broken logs) awaits the in-game test of experiment 028.

## Goal

Product rule: strength comes from population, land and organisation, not flat modifiers ([product spec](product-spec.md)). The vanilla 1337 Americas get their start economy from the development rules of `14_development.txt` plus pops, ranks, markets and a few buildings [V-LOCAL C73]. R7a keeps those rules and changes only their inputs, so the generated world uses the same model for the map, the societies and the economy.

## How vanilla sets it up

- Development of a location is the sum of `base`, `coastal` × harbour suitability, `river` × river size, `road`, `city`/`town`, vegetation, climate and topography values, and entries keyed by region, area, province or location (C73).
- The Americas take their civilisation level from the keyed entries (Mesoamerica 12, Andes 10, Central America 9, Aridoamerica and Colombia 7, Great Plains 5, Cahokia +7 and so on). The maximum keyed sum of any American land location is 12.
- The 1337 Americas have no institutions and no roads. Their 88 buildings include 79 `market_village` in 79 of 223 state capitals (35.4%); 22 of those capitals are cities or towns, which cannot hold one (C95), so the vanilla share is 79 of 201 (39.3%).
- Harbour suitability has 1,092 values in the Americas: 758‰ are 0.00, 13 are −0.10 and the mean is 0.101.

## What was wrong before 0.9.2

The generator kept the 14 American region entries, and generated regions reuse vanilla keys by position. The bonus therefore followed the old positions, not the generated societies; cities got none, and 55% of the keyed development landed on unorganised land. Every generated port got harbour 0.50 (C74). A negative harbour value in a donor template also stayed beside the new one, because the regular expression that removed it did not match a minus sign.

## Algorithm (implemented in `eu5_development.py`)

| Stage | Method |
|---|---|
| Calibration | `calibrate` parses the vanilla setup texts and templates: the rules, the maximum keyed sum `B` (12), the sorted American harbour values, the share of American state capitals that are neither cities nor towns with a market village (393‰) and the estimated mean development per class. |
| Positional entries | `eu5_rewrite.drop_block_entries` removes every entry keyed by a region, area, province or location of the vanilla New World from the `development` block. `vanilla_new_world_keys` fails the export if a kept vanilla location lies under one of them. |
| Society term | `society_term`: `(B × level + 500) // 1000` per generated land location, with level = `min(1000, complexity × 1000 // full)` and complexity the permille level of the society model. `fit_fulls` picks `full` per world and settlement class among 250…3000 (step 5): for cities, for towns and for the other state land (capitals and members together), the smallest candidate whose estimated mean development comes closest to the vanilla mean of the same class. Tribes and unorganised land use the state-land `full`. Only terms of 1 or more become `<key> = <n>` lines; the three `full` values are reported as `society_full_permille`. |
| Harbours | `shelter` casts 48 integer-direction rays of 64 px from each port's dock on the final world raster (columns wrap, lakes count as water) and counts those that meet land. `harbour_values` sorts the ports by (score, key) and takes the vanilla value at index `(2i + 1) × m // (2n)`. Shelter predicts vanilla values only weakly (Spearman 0.10–0.19, C74), so the distribution is what is reproduced. |
| Market villages | `market_villages` gives the vanilla share of generated state capitals one level-1 `market_village`, most complex first, ties by population then key. Capitals that are cities or towns are left out of both the share and the placement: the engine refuses the building there (16 of them were logged, C95). |
| Output | `14_development.txt` gets the dropped entries and the term lines; `07_cities_and_buildings.txt` gets the village lines in `building_manager`; location templates carry the harbour values of ports only. |

Choices marked [INFERRED design]: a term that follows complexity and saturates at a level fitted per world and settlement class, river size as the rank of the widest river pixel, the use of shelter to order harbours, and the choice of village capitals by complexity. The fit exists because vanilla's keyed entries lift each settlement class to its level on any terrain (Mesoamerica +12 on jungle, Great Plains +5), whereas the physical rules give generated land of each class different development per world. Copying vanilla's per-class bonus would have given states 8.7–10.6 against 4.1 (C74); a purely linear term left continents states at 0.63–0.73 of the vanilla mean; a fixed saturation of 800 permille left archipelago 5 states at 1.55 (C75). A single state-land curve then left cities at 7.8–9.7 and towns at 3.1–6.6 against vanilla 12.2 and 6.1, because generated urban centres stand on poorer land than the rest of generated state land, while vanilla cities stand on better land than vanilla state land (C76).

## Estimate and the river term

The estimate sums every rule of `14_development.txt` and clamps at zero, the same function for vanilla and generated land. River size is the rank of the widest river pixel of the location in `rivers.png` (width codes 4, 5, 11, 15 give 1–4; a location with only source, join or split pixels gets 1). The engine's mapping is not documented; the map legend names five sizes, small river to great river [INFERRED]. The term matters because rivers are not spread alike: generated cities have a river in 857–1000‰ of cases against 111‰ in vanilla, state capitals 702–795‰ against 463‰, because hearths and population follow river farming (C76). Leaving the term out understated generated urban development relative to vanilla.

## Results (C76)

Estimated mean development (vanilla Americas: city 12.28, town 6.38, state capital 4.96, state member 4.41, tribe 1.26, unorganised 0.78):

| World | City | Town | Capital | Member | Tribe | Unorganised | `full` city / town / state land |
|---|---|---|---|---|---|---|---|
| continents 3706823338 | 12.07 | 6.40 | 4.38 | 4.72 | 0.12 | 0.13 | 250 / 880 / 785 |
| archipelago 5 | 12.20 | 6.37 | 4.81 | 4.61 | 0.36 | 0.38 | 725 / 890 / 1175 |
| continents 3717486232 | 12.29 | 6.29 | 4.60 | 4.66 | 0.18 | 0.20 | 745 / 1100 / 1320 |

The rank correlation of term and population is 657, 628 and 573‰ (vanilla 507‰). Of the land a hearth reaches, 912–933‰ gets a term (`coverage_permille`); that land is 229–295‰ of all land (`civilised_permille`), depending on whether a world has 3 or 4 hearths. Two builds of seed 3717486232 are byte-identical (715 files). Harbour values and market villages reproduce the vanilla distribution and share.

## Measured differences that are not fitted

Tribes and unorganised land stay below vanilla (0.1–0.4 against 1.26 and 0.78, C76). The physical part over all generated land equals vanilla's (−4.0 to −4.5 against −4.26), but the generator puts civilisations on the best land (state capitals −1.3 to −2.0 against −6.2 for vanilla capitals in jungles and highlands), so generated tribal land is poorer than vanilla's (−4.3 to −4.6 against −3.25). Vanilla also gives land outside states authored regional bonuses (Great Plains +5, tribes inside Mesoamerica +12). A fit for tribes would need the full civilisation term on all tribal land with complexity above 0.25 and still stays below vanilla (0.6–1.1), so it is not made: tribal land earns development only from hearth complexity and its own land.

## Settings

None. Presets (R8) will own a development control.

## Checks

- Synthetic tests (`tests/test_development.py`): decimals and signs; templates with nested blocks; calibration on a small setup; terms, harbour quantiles, shelter geometry (including the map wrap), village choice, rank correlation; line insertion; `drop_block_entries`; `verify_development` accepts the plan and rejects a kept New World entry, a repeated key, a sea key, a value above `B`, a harbour on a location without a port and a village outside its capital.
- Export invariants (`verify_development`): the checks above on the final texts, plus every Old World development entry identical to vanilla.
- `tests/test_local_install.py` reads the vanilla calibration (`B = 12`, 1,092 harbour values, 393‰).
- `report.json` section `development` holds `B`, the fitted `full` per class, the entry count, the share of land with a positive term, the share reached by a hearth and its coverage, the rank correlation of term and population, harbour histograms, village counts and the estimated mean development per class for the generated world and for vanilla. The estimate is a clamp-at-zero sum of every rule, with river size inferred from `rivers.png`.

## Raw materials (0.9.14, C119)

Each generated land location draws its raw material from the vanilla frequencies of similar locations: the same climate, vegetation, topography and coast, falling back to fewer of them. Up to 0.9.13 those frequencies were the Old World's, so a generated America had elephants (55 locations of one world), horses (87), wheat (261), rice (225), millet (215), silk (36), tea (25) and camels (17) and none of maize, potatoes, cocoa, tobacco or chili, which in vanilla only America has. They are now the vanilla New World's: in the continents world of seed 42 no Old-World-only material is left and maize holds 380 locations, chili 86, cocoa 73, potatoes 44, tobacco 15. `new_world.precious_permille` weighs gold, silver, gems and pearls against the rest (1000: their vanilla share; the window offers 0 to 3 times); a class whose only materials it removes falls back to a coarser class.

## Open work

- Institutions, roads and other buildings (terraces, walls, culture buildings).
- The engine's river size (experiment 012) and the effect of `development` on pops after the start.
- Technology per society (R7b) and great empires with explicit causes and weaknesses (R7c) are implemented offline ([natives](natives.md), C159, C160; design [R7b and R7c design](r7-technology-and-empires.md)); their in-game test is [experiment 028](../experiments/028-technology-and-empires/README.md). Institutions need no setup: the vanilla 1337 Americas have none and they spread in game (C155). Ordinary roads, rivals and other buildings need nothing either: the vanilla Americas have none (C155).
- Whether the engine honours entries for new keys (experiment 012).
