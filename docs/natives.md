# Native societies (phase R6)

**Status:** R6a implemented on 2026-10-19 (generator 0.8.0, C67–C68). The owner's first run loads it and shows the states with names, flags and rulers (C69); the rest is untested in game. R6b (generator 0.9.0–0.9.1, C70–C72) adds place names in local languages, vassals and coastal seas known to natives, and fixes unbent location borders; in-game test pending (experiment 011). The generated New World is no longer empty in 1337: it has native pops, states, tribes, towns, markets and holy sites, derived from the same physical model as the terrain.

## Goal of the first slice

Each seed should give a plausible native New World: dense farming civilisations in a few fertile regions, chiefdoms and tribes around them, thinly peopled or unorganised land elsewhere. Strength must come from population and land, not from flat modifiers ([product spec](product-spec.md)). R6a reuses the vanilla American cultures, religions, country templates and town setups, which are read from the local installation. Names, graphics, units and religious mechanics therefore already exist. Countries get new tags.

## How vanilla 1.4.1 sets up the Americas

Read-only survey of `main_menu/setup/1337`, `in_game/setup/countries` and `main_menu/setup/templates` [V-LOCAL/V-EXEC C67]:

- **Pops.** `06_pops.txt` lists `define_pop = { type size culture religion }` per location. The vanilla Americas have 4,434 land locations, 4,404 of them with pops, 30,113 pop units in total: 82% tribesmen and 17% peasants, with a few clergy, nobles, burghers and slaves.
- **Countries.** `10_countries.txt` sets up 544 American countries:
  - 223 *landed* countries (`own_control_core`, `capital`, `include = "<template>"`, `government = { ruler = random }`) own 493 locations (11%).
  - 321 *pop* countries (`type = pop`, `add_pops_from_locations`) hold the pops of 1,862 locations without owning them.
  - 2,088 locations belong to neither.
  - Landed countries hold a median of 1 location (maximum 23); pop countries a median of 4 (maximum 64).
- **Tags.** Each tag is defined in `in_game/setup/countries/*.txt` (`color`, `color2`, `culture_definition`, `religion_definition`). Its name comes from `country_names_l_<language>.yml` (`TAG`, `TAG_ADJ`). 635 of the 2,351 setup tags have no scripted coat of arms; the engine draws those from culture-keyed templates.
- **Templates.** `main_menu/setup/templates/*.txt` set the government type, laws and privileges. Some have coastal and `_no_coast` variants; the `expl_*` templates list discovered regions and areas.
- **Towns and markets.** 25 American locations have a rank: 9 cities and 16 towns, using `town_setup` values such as `mexican_city`, `andes_town` or `south_east_woodlands_town`. 12 of them are market centres (`03_markets.txt`). Development follows rules on location attributes (`14_development.txt`), with a few overrides.
- **Cultures and religions.** 730 cultures and 70 religions appear in American pops. Holy sites (`in_game/common/holy_sites`) name one location each.
- **Density.** Locations outside states hold 2.47 pop units per 1,000 location pixels. State locations hold 42.2, and a median of 10 times what a tribal climate fit predicts. Peasants are a median 39% of pops in state locations. Capital elites are small (nobles 0.012–0.085, clergy 0.03–0.34).

## Algorithm (implemented)

| Stage | Module | Method |
|---|---|---|
| 1. Land graph | `eu5_natives.land_graph` | Generated land locations with their land contacts, plus sea links between coasts on the same sea or lake zone (cost 4 steps). Each location gets three values. *Tribal capacity*: pixels × vanilla tribal density of its climate × a topography factor × 1.2 near water. *Farming potential* (permille): climate × vegetation × topography, with tropical highlands farming like lowlands, a lift from rivers and coasts, and a growing-season factor from full at 40° to none at 65°. *Travel cost*: by topography and vegetation. |
| 2. Hearths | `societies._food`, `_hearths` | Score above-median locations by the farming potential summed within half a hearth's reach. Take the best ones at least 1.5 reaches apart and above half the best score, with seeded jitter. About 6 hearths per 10,000 locations. |
| 3. Complexity | `societies._complexity` | Falls linearly with travel cost from each hearth (the first at full strength, others at 70–100%), damped on poor land (`0.4 + 0.6 × potential`). |
| 4. Population | `societies._population` | Capacity × (1 + 11 × complexity) × seeded noise of 0.6–1.5, scaled to the vanilla population per land location times the generated location count. The peasant share is 60% × complexity. |
| 5. Zones | `societies._zones` | Religion zones (about 80 locations) grow from spaced seeds by weighted travel cost over the whole graph, so every island gets one. Culture zones (about 10 locations) grow inside each religion zone; complex seeds grow larger. Every zone is connected. |
| 6. Identity | `eu5_natives.match_homelands` | Each zone has a homeland vector: pop-weighted climate (counted twice), vegetation and topography shares, share in states, latitude and coast. Vanilla cultures and religions have the same vector from their 1337 homelands. Zones pick in order of population. Each takes the best unused religion, or a culture of its religion, unless reusing the best one fits better by more than a slack; a small seeded noise varies the choice. |
| 7. Polities | `societies._state_land`, `_states`, `_tribes` | The most complex 11% of inhabited land becomes state land. Its capitals, the most populous spaced locations, take territories by weighted growth (larger capitals reach farther). In 45% of culture zones the tribal land splits into pop-type tribes of about 6 locations; the rest stays unorganised. |
| 8. Ranks and markets | `societies._ranks` | The most populous 4% of states have a city capital and the next 11% a town capital. Every city, and the largest state near each hearth, is a market centre. |
| 8b. Vassals | `eu5_natives._vassals` | The most populous 5% of states take up to three bordering states of their religion with under a third of their population as vassals (`12_diplomacy.txt`, `subject_type = vassal`). Vanilla has 4 American vassals (C70); generated worlds get 8–19. Both countries of a pair set their rank (`country_rank = rank_duchy` for the overlord, `rank_county` for the vassal, a combination vanilla uses 7 times), because `vassal` requires the overlord's rank level to be at least the subject's and nine default-rank pairs were logged as invalid (C95). |
| 8c. Names | `names.MarkovNames`, `eu5_natives.PlaceNamer` | A character Markov chain (order 3) per corpus of vanilla American place names, chosen by the culture's language, else its family, else its religion, else all Americas (at least 40 names). Land locations take their culture's language; wastelands that of their land neighbours (with "Highlands"); provinces and areas that of most of their locations; states their capital's name and tribes a name of their culture. Names copy no vanilla name (accents ignored) and never repeat. Seas and lakes keep syllable names. |
| 8d. Diaspora | `eu5_natives.diaspora` | Vanilla has pops of all its American cultures and religions and the engine logs each enabled one without a pop (473 cultures and 28 religions, C95). Every culture and religion no zone took gets one small pop (50 people, tribesmen or peasants) at a seeded location of the culture zone whose homeland fits it best; an unused religion takes the culture of its location. |
| 9. Serialisation | `eu5_natives`, `eu5_nw_export` | Writes the following. `06_pops.txt`: elites in state capitals, burghers in towns, peasants and tribesmen. `10_countries.txt`: landed countries with `own_control_core` and pop countries with `add_pops_from_locations`; the include template is the one the culture used in vanilla (else a generic American monarchy or tribe, with the right coast variant); `discovered_areas` covers the religion zone and the seas along its coasts; `ruler = random`. `in_game/setup/countries/rnw_natives.txt` holds colours that differ from neighbours, culture and religion. Localization gives the capital's name to a state and a generated name to a tribe. `07_cities_and_buildings.txt` gets ranks with the culture's vanilla town setup (else `mexican_city` or `south_east_woodlands_town`), and `03_markets.txt` gets markets. Holy sites of placed religions move to their most populous zone locations. |

Choices marked [INFERRED design]: the farming table, the topography density factors (the vanilla fit gives mountains 3.0 only because of the Andes), travel costs, the growing-season band, the gain and peasant curves, and the matching weights.

## Settings (`natives` section)

| Setting | Continents | Archipelago | Meaning |
|---|---|---|---|
| `population_permille` | 1000 | 1000 | Total relative to the vanilla population per land location |
| `hearths_per_10k` | 6 | 8 | Expected hearths per 10,000 land locations |
| `hearth_reach_steps` | 16 | 16 | Reach of a hearth in ordinary steps |
| `state_share_permille` | 110 | 110 | Share of inhabited land in states (vanilla 11%) |
| `state_locations` | 3 | 3 | Mean locations per state |
| `culture_locations` | 10 | 10 | Mean locations per culture zone |
| `religion_locations` | 80 | 60 | Mean locations per religion zone |
| `tribe_locations` | 6 | 6 | Mean locations per tribe |
| `organized_permille` | 450 | 450 | Share of culture zones organised into tribes |

## Checks

- Synthetic tests (`tests/test_societies.py`, `tests/test_natives_eu5.py`): determinism and seed dependence; population total; state share; the fertile hearth; connected, nested zones; disjoint, connected polities with their capitals; country texts parse; tags avoid reserved words; generated pops replace removed ones.
- Export invariants (`_verify_natives`): unique fresh three-letter tags; every country holds generated land only, with its capital, and no location twice; pops and ranks lie on generated land.
- Removed vanilla tags (`country_definition_outputs`, `verify_country_tags`): vanilla defines a tag only together with its 1337 setup entry, and the engine creates every defined tag as a country, so the removed American tags also leave the definition files in `in_game/setup/countries/` (C86). The export fails if the tags defined without a setup entry, or set up without a definition, differ from vanilla's (only `DUMMY`, `MER` and `PIR` are defined without a setup entry). Vanilla scripts keep their references to removed tags, as they reference formable tags without a definition (C89).
- Government types (`template_governments`): a generated country writes the government type and heir selection that the vanilla countries with its template write most often (a template may leave the type open, or set a heir selection all its users override, C91, C94); a chosen template that gives no type, itself, through its includes or through its users, fails the export.
- Localization keys (`rnw.loc_keys`, `verify_localization`): the engine hashes keys with MurmurHash3, so every generated key (locations, provinces, areas, tags and adjectives) is claimed against the hashes of all vanilla keys of the installation, and a serial or tag whose hash is taken is skipped (C89).
- Colours (`vanilla_colors`, `map_colors`): generated country colours repeat no vanilla definition (named colours resolved, HSV approximated) and no other generated colour, since the engine logs equal colours (`SWN` = `GTO`, C95).
- Script rewrites (`remap_scripts`, `retire_events`): holy sites, scripted geographies, formables, city graphics and the `map_id` list of the volcano object are rewritten in the base game's and in every DLC's files, province lists included and without repeats; a removed `map_id` entry is dropped, since its object needs a locator. Dynamic historical events whose tags are all removed leave their files (53 events of five files, C95); the historical base values only removed locations used leave `location_historical_base_values.txt`. A DLC file at the path of a base game file stops the export.
- Land that reaches no port (`unported_cells`, `seal_pockets`): a land cell that no coast reaches without crossing wasteland becomes wasteland, and the export fails if any remains (3 locations of seed 319218363 were logged as isolated, C95).
- `tests/test_local_install.py` reads the vanilla calibration.

## In-game questions (experiment 010)

Whether EU5 1.4.1 accepts the new tags, pop-type tribes on generated locations and engine-drawn coats of arms; whether rulers and dynasties are generated; how the political map, diplomacy and AI behave; colonisation of land with native pops; and `error.log`.

## Open work

- Alliances and rivalries between states; mixed-culture border locations; a rare-civilisation preset; tribes are invisible on the political map because pop-type countries own no land (as in vanilla).
- Religions with special mechanics (for example Nahuatl or Inti situations and generic actions) may expect vanilla geography; scripts were only remapped to the nearest generated location.
- Generated cultures and religions (instead of vanilla ones) for the alternative-history presets.

## Terra incognita edge

The terra incognita shader blends visibility over one location pixel, so its edge follows the pixel steps of the location raster in vanilla and generated land alike (C69). A shader patch tried in R6b is removed at the owner's request (C72). The generated map itself is fixed instead: borders are bent again where one cell used to undo the bending everywhere (C71), natives know their coastal seas, and the terrain coastline follows the raster as closely as in vanilla (C72).
