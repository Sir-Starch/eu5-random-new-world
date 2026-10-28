# Native societies (phase R6)

**Status:** R6a implemented on 2026-10-19 (generator 0.8.0, C67–C68). The owner's first run loads it and shows the states with names, flags and rulers (C69); the rest is untested in game. R6b (generator 0.9.0–0.9.1, C70–C72) adds place names in local languages, vassals and coastal seas known to natives, and fixes unbent location borders; in-game test pending (experiment 011). **R7b (generator 0.9.28, C159)** gives every state a technology level from its capital's complexity and makes cultures follow the regional family of their land (below), and **R7c (0.9.29, C160)** gives great empires explicit causes and weaknesses; in-game test pending (experiment 028). **R7d (societies, 0.11.2, C251-C253)** adds a sea league, a highland confederation, a fractured realm and a sacred centre ([below](#more-varied-societies-r7d-societies)); in-game test pending (experiment 045). The generated New World is no longer empty in 1337: it has native pops, states, tribes, towns, markets and holy sites, derived from the same physical model as the terrain.

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
| 4. Population (after state-site planning) | `societies._population` | Capacity × (1 + 11 × complexity) × seeded noise of 0.6–1.5, scaled to the vanilla population per land location times the generated location count. The peasant share is 60% × complexity. |
| 5. Zones | `societies._zones` | Religion zones (about 80 locations) grow from spaced seeds by weighted travel cost over the whole graph, so every island gets one. Culture zones (about 10 locations) grow inside each religion zone; complex seeds grow larger. Every zone is connected. |
| 6. Identity | `eu5_natives.match_homelands` | Each zone has a homeland vector: pop-weighted climate (counted twice), vegetation and topography shares, share in states, latitude, coast and, since 0.9.28, the shares of the three regional families (Mesoamerica, South America, North America; counted twice like climate). Vanilla cultures and religions have the same vector from their 1337 homelands. Zones pick in order of population. Each takes the best unused religion, or a culture of its religion, unless reusing the best one fits better by more than a slack; a small seeded noise varies the choice. |
| 7. Polities | `societies._state_land`, `_states`, `_tribes` | State sites are planned before population: complex core land and farmable remote pockets, within the configured land budget. Only capitals meeting the vanilla agrarian baseline form landed states. Their capitals, the most populous spaced locations, take territories by weighted growth (larger capitals reach farther). In 45% of culture zones the tribal land splits into pop-type tribes of about 6 locations; the rest stays unorganised. |
| 8. Ranks and markets | `societies._ranks`, `regional_markets` | The most populous 4% of states have a city capital and the next 11% a town capital. Every city, and the largest state near each hearth, is a market centre. Every disconnected landed group without one gets a local market in its most populous capital; all market centres have at least town rank. |
| 8b. Vassals | `eu5_natives._vassals` | The most populous 5% of states take up to three bordering states of their religion with under a third of their population as vassals (`12_diplomacy.txt`, `subject_type = vassal`). Vanilla has 4 American vassals (C70); generated worlds get 8–19. Overlords come only from states whose template sets a starting technology level of at least the lowest of vanilla's lords (2), and (since 0.9.28) whose written level is at least that too: all 18 pairs of tech-0 lords (`amerindian_monarchy`, tribes) were logged as invalid at the start in two worlds, none of the 23 pairs of tech-2 lords (C99). |
| 8c. Names | `names.MarkovNames`, `eu5_natives.PlaceNamer` | A character Markov chain (order 3) per corpus of vanilla American place names, chosen by the culture's language, else its family, else its religion, else all Americas (at least 40 names). Land locations take their culture's language; wastelands that of their land neighbours (with "Highlands"); provinces and areas that of most of their locations; states their capital's name and tribes a name of their culture. Names copy no vanilla name (accents ignored) and never repeat. Seas and lakes keep syllable names. |
| 8d. Diaspora | `eu5_natives.diaspora` | Vanilla has pops of all its American cultures and religions and the engine logs each enabled one without a pop (473 cultures and 28 religions, C95). Every culture and religion no zone took gets one small pop (50 people, tribesmen or peasants) at a seeded location of the culture zone whose homeland fits it best; an unused religion takes the culture of its location. |
| 9. Serialisation | `eu5_natives`, `eu5_nw_export` | Writes the following. `06_pops.txt`: elites in state capitals, burghers in towns, peasants and tribesmen. `10_countries.txt`: landed countries with `own_control_core` and pop countries with `add_pops_from_locations`; a state also writes `starting_technology_level` after its include (R7b), and its template is the culture's own vanilla one when that is within one level of it, else the advanced or the plain American monarchy; a tribe's template is the one its culture used in vanilla (else a generic tribe), with the right coast variant; `discovered_areas` covers the religion zone and the seas along its coasts; `ruler = random`. `in_game/setup/countries/rnw_natives.txt` holds colours that differ from neighbours, culture and religion. Localization gives the capital's name to a state and a generated name to a tribe. `07_cities_and_buildings.txt` gets ranks with the culture's vanilla town setup (else `mexican_city` or `south_east_woodlands_town`), and `03_markets.txt` gets markets. Holy sites of placed religions move to their most populous zone locations. |

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
| `state_spread_permille` | 150 | 150 | Share of the state land in small pockets of states away from the hearths' core (0.9.14) |
| `empire_permille` | 250 | 250 | Chance, per cultural hearth, that a great empire rises around it (0.9.15); 0: none |

**Remote states (0.13.17, C410; supersedes the 0.9.14 placement in C117).**
[V-LOCAL / V-EXEC] All 223 landed countries in the installed vanilla 1337 Americas
have peasants: the least country total is 338 milli-pops and the least country share
is 122‰. The former generator placed outlying state land after allocating population,
including land outside all hearths with zero complexity and therefore zero peasants.
The previous reference world has 73 such states out of 310. On the same seed/settings,
0.13.17 has 307 states with none lacking peasants; direct contacts in the written
location raster show 5 isolated states instead of 11. All five have farming populations;
the underlying model minimum is 2,797 milli-pops (vanilla country floor: 338). The
written location raster remains byte-identical to 0.13.16.

[INFERRED design / V-EXEC] State placement now precedes population allocation. The
core uses sufficiently complex land; remote pockets select farmable land and establish
local complexity, falling with travel cost from their farming centre. The resulting
complexity drives population, peasant share, development and technology together.
The same global population budget is redistributed once, with no population grants,
flat income bonuses or changes to vanilla expansion rules. Capitals need the calibrated
peasant population and share; unsupported components stay available to tribes. The
configured state-land share is a placement budget, not a demand to create unsupported
states. Empires must meet the same country-wide baseline, and tribes without it cannot
become landed through a confederation. The exporter rejects a landed country below it.

[V-LOCAL / INFERRED design / V-EXEC] All twelve vanilla American market centres are
towns or cities. Generated groups of landed countries connected through their own land
or shared coastal waters reuse existing markets; an unserved group establishes a market
in its most populous country's capital, with at least town rank. Newly landed confederates
use the same settlement planning. This graph coverage does not estimate the engine's
market access: distant parts of a connected group may still have poor access.

[UNKNOWN] Positive demographic support and a regional market are input guarantees,
not a proof of positive engine income, an affordable development action or later AI growth.
No new game run or campaign is claimed. `report.json` → `natives.state_economy` records
the calibrated floors, actual minima, isolated countries and countries without peasants.
Synthetic tests cover poor islands, scarce population, remote farming, connected ownership,
market sharing, confederate eligibility and loud rejection of unsupported landed countries.

**Great empires (0.9.15, C125).** EU4's random New World had a *Fantasy Random New World* setting (never, seldom, sometimes, often) for the chance of fantasy scenarios such as highly advanced native empires (C122). The generator's counterpart is `empire_permille`: each cultural hearth, in the order they were found, rises into a great empire with that chance (the window offers 0, 25, 50 and 80 %; Seldom is the default). A stream of its own draws the chance and the size for every hearth, so a chance of 0 leaves every byte of 0.9.14 and a higher chance raises the same hearths and more. The empire takes the nearest inhabited locations by travel cost around the most populous location near its hearth, 8-16 permille of the land locations (at least 12; vanilla's largest native state, the Aztec empire, holds 23 of 4,434), and never land another empire holds; the ordinary states and tribes are made on what is left. It has the largest population of its world and so a city for a capital and the first pick of vassals. Strength comes from land and population and, since 0.9.29, from the causes in the table below, never from a flat modifier; each has a weakness beside it. In game: untested.

**Great empires: causes and weaknesses (0.9.29, C160).** A great empire is strong for reasons a player can see in game and weak for reasons a player can see in game, each through a mechanism the vanilla 1337 setup already uses, in the Americas or, for roads, in the Old World (C158). R7c draws no random number: empires, vassals and neighbours exist when it runs, so no stream of the peoples layer moves, and a world without empires is byte-identical to R7b's. The technology of the Western powers is a `starting_technology_level`, not a template (the earlier note that the generator could not make it was true of templates only). Not generated, and out of scope: the maritime, commercial and fractured archetypes of the [product spec](product-spec.md), tributaries (the `tributary` subject type needs a tribal or horde overlord, which no American advance gives, C158), rivals and stability.

| | What | Written | Vanilla precedent [V-LOCAL C158] |
|---|---|---|---|
| **Cause: technology** | The level is `min(T, S + 1)`, `T` the highest level any vanilla template or 1337 country entry gives (3) and `S` the highest vanilla American state level (2): 3, the level of 915 Old World countries. The empire starts with the level-3 advances of the age of traditions (alchemy, cultural acceptance with +1 cultures capacity, merchants, trade, castles, the cog) [INFERRED]. The template of R7b is the culture's own or the advanced monarchy, both level 2, one below the level as in vanilla. | `starting_technology_level = 3` | 915 of 983 Old World entries that write a level write 3. |
| **Cause: rank** | The highest rank any vanilla American landed country starts with, read from `country_ranks` and the setup: `rank_duchy` (+1 diplomatic capacity, +0.5 cultures capacity, two rivals and prestige). Fails the build if no American country has a rank. | `country_rank = rank_duchy` after the level | The Tarascans and the Itza. |
| **Cause: royal roads** | Shortest paths over land contacts only (`societies.land_routes`, `trunk_roads`: the cost of the location entered, ties by index, never the sea links) from the capital, through the locations of the empire and its vassals, to the capital of each vassal, each ranked and market location of the empire and, in each area it holds, its most populous location. A target no land path reaches stays unlinked and is counted. The pairs are the union of the paths. | `<a> = <b>` lines in `road_network` of `09_roads.txt` | All 1,646 vanilla pairs join locations in pixel contact; the 90th percentile of pairs per owned location is 1.0, the road bound. |
| **Weakness: fear** | Every independent generated state in land contact with the empire, but not its vassals, holds `opinion_threatens_conquest` (−50 for 300 months) of it, and it holds `opinion_prey_to_conquest` (−25 for 300 months) of them. From 0.9.33 the holder of every generated opinion, fear and resentment alike, has discovered the area of its partner's capital (`discovered_areas`; C170, C171). | `opinion` records in `diplomacy_manager` of `18_opinions.txt`, and `discovered_areas` of the holder's record | The Andes block: CSU and AYA hold the first of URC, URC the second of CSU; every Andean country has the whole region discovered through `expl_andean`, so the game never finds an opinion toward an undiscovered capital in vanilla. |
| **Weakness: resentment** | Every vassal holds `opinion_tyrant_overlord` (−50) of the empire, and it holds `opinion_irritated` (−10) of them. | The same | Mayapan: XIU and HEL, vassals of COC. |
| **Weakness: diversity** | Nothing is written: the pops keep the cultures and religions of the zones the empire spans, which make such pops less loyal [INFERRED; in-game check]. | Reported as foreign culture and religion shares | |
| **Weakness: reach** | Nothing is written: control falls with distance from the capital [INFERRED; in-game check]. | Reported as the median travel steps and the share of locations off the roads | |

That `first` holds the opinion of `second` is inferred from the vassals holding `opinion_tyrant_overlord` of their lord [INFERRED]. The four bias keys are constants and the build fails if one is not defined in `in_game/common/biases/`. The AI picks its rivals; none are written, as the vanilla Americas have none.

**Known defect (C161).** The game draws and routes roads along strips between road anchors that `in_game/gfx/map/spline_network/spline_network.splnet` holds for vanilla locations only, so each generated road pair, and each road built in play between generated locations, logs `Could not find spline network strip of type 0 between anchors a and b` over and over (125,820 lines in a 13-minute session, 83 of the 97 pairs of one world) [V-GAME owner / V-LOCAL; cause INFERRED]. Since 0.9.30 the generator makes the strips: every land contact of a generated location gets one, in a spline network written from the game's (`rnw.splnet`, `rnw.eu5_splines`, [interoperability register](research/interoperability.md) R-001, C162, C163); the game tests loaded the file without any strip error, a road network draws in the Roads lens (C166, probably 0.9.31, which keeps vanilla's order and numbering as a precaution, C165) and a 5.7-minute run at speed logged no strip error (C167); roads built in play and the empires' roads as lines are still to be confirmed ([experiment 029](../experiments/029-spline-strips/README.md)). An early report that 0.9.30 drew no road was an observation error: the owner's screen recording shows the wrong lens (proximity, not Roads) and roads drawn on the map at zoom (C168).

**Report.** `report.json` section `extraordinary`: the calibration (level, rank, the four opinion types, the road bound in permille), one record per empire (tag, name, capital, locations and vassals, population and its share of the New World, level, rank, road targets, pairs and pairs per location, unlinked targets, feared neighbours, resentful vassals, the weaknesses left unwritten and why, foreign culture and religion shares of its own locations, median travel steps, share of its locations off the roads) and the five vanilla American states with most locations for comparison (CHK 23, TAR 19, COC 12, KKA 11, CYA 10 locations; foreign culture 323, 0, 0, 0 and 0 permille).

**Checks.** `verify_empires` (export): every empire writes the calibrated level and rank and no other country writes a rank; every road pair joins two generated land locations in contact, held by one empire or its vassals, once, and the roads of each empire reach its capital; every opinion line joins an empire to a state in the required relation (contact or vassalage), once, and equals the plan; nothing names a vanilla tag or location; the Old World entries of `09_roads.txt` and `18_opinions.txt` are vanilla's (the opinions of removed American tags excepted). A file an export leaves unchanged is vanilla's. Tests: `tests/test_empires.py`, `tests/test_societies.py` (`trunk_roads`) and the optional local test (level 3, `rank_duchy`, road bound 900–1100 permille, the four bias keys).

**Results (C160).** Five offline builds, none of the invariants broken, each empire at level 3 with `rank_duchy`: continents 3706823338 with its one empire (71 locations, 3 vassals, 27 road pairs against a bound of 86, 10 feared neighbours); small_continents 7379108625698230220 with its (ERY, 58 locations, 3 vassals, 19 pairs, 7 feared neighbours); continents 3706823338 with `empire_permille` 1000, four empires of 59–89 locations with 3 vassals each and 16–28 pairs; and the two worlds without empires (archipelago 5, small_continents with `empire_permille` 0), which are byte-identical to the R7b builds but for `.metadata`. A road pair per location is 0.24–0.31 of its locations and vassals', against the bound 1.0; no target was unlinked. 69–76% of an empire's locations lie off the roads (the targets are its capital, its vassals' capitals and the most populous location of each area), the median travel from the capital is 3–5 steps. The foreign culture share of an empire's own locations is 13–79%, against at most 32% in the five largest vanilla American states.

## More varied societies (R7d, societies)

**Status:** implemented on 2026-10-24 (generator 0.11.2, algorithm epoch 26, C251-C253); NOT GAME VALIDATED. The name R7d is shared with the spline network of 2026-10-22 (0.9.30, C162-C163, below); this is the *more varied societies* of the [content plan](content-plan.md), gap G7. No separate design document preceded it; the design is this section and the claims it cites.

**Goal.** Four more combinations of real traits besides the great empire: a maritime trade network, a highland confederation, a fragmented region with several centres, a sacred centre with political competitors. An archetype follows geography and social structure; randomness only chooses among suitable combinations. Strength comes from population, ports and organization, weakness from separation, autonomy and rivalry; nothing is a flat bonus and no label grants power. The new files change no engine, define or interface file, and no binary format is read or written ([interoperability register](research/interoperability.md): nothing to record).

**Frequency.** The one rare-empire control (`natives.empire_permille`, the window's *Extraordinary peoples*) decides: once for every hearth's domain (the locations nearer to that hearth by travel cost, sea links included; the land no hearth reaches is one domain more) a stream of its own (`archetypes`, three draws a domain) says whether the domain has an extraordinary society, which kind of those it allows and which group of that kind. A chance of 0 chooses nothing, a higher one chooses in the same domains and more, and a world without them keeps every byte of the generated land, countries and files of 0.11.1 (but `.metadata` and `inputs.json`, which lists the three game directories now read). The great empire keeps its own draws (C125); a group never takes an empire, a vassal or a lord.

| | Sea league (maritime trade network) | Highland confederation | Fractured realm | Sacred centre |
|---|---|---|---|---|
| **Structure** | 3 to 5 free states of level 2 or more with a port on one sea zone, at least two of them parted by land | 3 to 6 touching tribes of one religion zone, at least 600 permille of their locations on hills, mountains or plateau, as populous per location as vanilla's confederates (1,641 milli-pops) | 3 or 4 touching free states of one religion zone, capitals of complexity 500 or more, none more than 3 times as populous as the biggest, together holding at least 12 locations (an empire's floor) | the free state that holds the most populous location of a religion zone, among the most populous quarter of the states, with 2 or 3 touching free states of its faith |
| **Precedent** [V-LOCAL C251] | Tlaxcala, the one American republic; 22 `scripted_mutual` alliances of the Old World | The Haudenosaunee: 5 landed tribes of 3 to 11 locations in one `tribal_confederation` | The Burke feud of Connacht: four countries, each the rival of the others (`20_rivals.txt`) | Tibet and Venda, the theocracies of faiths that are not Christian |
| **Cause** | republic government (`amerindian_advanced_republic_not_nahuatl_no_coast`, `oligarchic_elective`); `land_vs_naval` at the naval end vanilla's American templates reach (60), with its sea-trade bonus; a port town for every member, a city and a market at the hub's port | landed tribes (own their land, the tribes' government), membership of one `tribal_confederation` (mutual defence law, tribal cohesion), the confederates' `currency_data` | one faith and one people in a dense, complex region | `theocracy` with `theocratic_elective`; `spiritualist_vs_humanist` and `traditionalist_vs_innovative` at the ends vanilla's American templates reach (-90); the faith's most populous place |
| **Weakness** | allies, not subjects (a ring: every member holds two alliances, none leads); separated by water; `land_vs_naval` costs land trade | no leader country; tribal technology; highland travel costs; the report counts the pairs parted by land | every centre is the rival of the centres it touches (mutual `rival`) | the competitors of its faith are its rivals (mutual `rival`); the axes cost tolerance and innovation |
| **Written** | `10_countries` (template, `type`, `heir_selection`, position), `12_diplomacy` (`scripted_mutual`), `07_cities_and_buildings`, `03_markets` | `10_countries` (`own_control_core`, `capital`, `currency_data`), `15_international_organizations` | `20_rivals` | `10_countries` (government), `20_rivals` |

The societal values are the game's own two-sided axes (`in_game/common/societal_values`): each pole has a modifier and a cost (`land_vs_naval`: naval gains sea-trade efficiency and loses land-trade efficiency). The axes whose definitions hold an age (`mercantilism_vs_free_trade`, `outward_vs_inward`) and `aristocracy_vs_plutocracy` (the republic template already holds vanilla's American extreme of it) are left alone. `alliance_can_exist` needs opinion 0 or more both ways and no rivalry or subjecthood, which the groups' rules keep: members are free, groups are disjoint, and an alliance joins members of one league only. The holder of every generated relation (alliance, rivalry, confederation) has discovered the area of its partner's capital, as for the opinions (C170, C171).

**Code.** `rnw/archetypes.py` (game-independent: `Structure`, the four selections, `plan_archetypes`, `alliance_pairs`, `rival_pairs`), `rnw/eu5_archetypes.py` (the calibration from the installation, the lines, the written readers, `archetype_problems`), `societies.hearth_domains` and `travel_from`, `Polity.landed`, `Country.landed`, `currency` and `archetype`, `eu5_natives._archetypes` (applies a group), `eu5_nw_export.verify_archetypes`, report section `archetypes`.

**Results (C252).** Exports at 1000 permille (a group in every domain that allows one), none of the invariants broken:

| World | Groups | Notes |
|---|---|---|
| continents 3706823338 | a fractured realm (3 centres, 12 locations, 6 rivalries) and four confederations (6, 4, 3 and 6 tribes, 10 to 39 locations) beside 4 empires | 0 to 8 permille of the world's people per group |
| small continents 7379108625698230220 | a realm (4 centres, 20 locations, 10 rivalries) and three confederations (5, 3 and 5 tribes) beside 3 empires | |
| archipelago 5 | a sea league (3 states, 12 locations, 3 alliances, 3 median steps to the hub, one pair without land contact) and two confederations (6 and 3 tribes) beside 3 empires | the league holds 17 permille of the people |
| continents 208, installed | one of each kind: a realm of 4 centres (18 locations, 8 rivalries), a confederation of 3 tribes (16 locations), a league of 3 states (5 locations) and a sacred centre of 3 states (11 locations, 4 rivalries) | the one world of 31 searched that held all four |
| small continents at 0 permille | none | byte-identical to the 0.11.1 export but for the two `.metadata` files (818 files) |
| the reference world, 250 permille | two confederations of 3 tribes | offers every story family; digest `7113a7f6…0662` (792 files) under hash seeds 1 and 7 |

Over 31 searched worlds (the peoples stage alone, at 1000 permille) the options per world were 0 to 8 leagues, 4 to 24 confederations, 0 to 19 realms and 0 to 4 centres; 2 to 5 groups were chosen. A world with the default chance of 250 permille therefore holds one or two. The groups are small in the land, as vanilla's confederation is (0.7 permille of its people): a confederation holds 0 to 8 permille, a league 17.

**Checks.** `archetype_problems` (export, `verify_archetypes`): every generated country writes the template, government fields, currency and holding it was planned with; groups are disjoint, of free countries, and of one kind; a league is a ring of republics (every member two alliances) and an alliance joins members of one league; a confederation is made of landed tribes that write the confederates' currency and is one organization of the setup; a realm's rivalries and a centre's are returned and join members of one group; the alliances, rivalries and organizations of the setup files are the plan's, once each, beside vanilla's Old World entries; and the holder of every relation has discovered the area of its partner's capital. Tests: `tests/test_archetypes.py`, `test_eu5_archetypes.py`, `test_archetype_world.py`, `test_archetype_export.py`.

**Open.** Whether the engine takes these records is untested (C253): a theocracy over a monarchy-derived template, tribes of the plain template in a confederation, alliances at the start and rivals beyond a rank's number have no American precedent. The effect of the positions on the axes is the game's. Not generated: tributaries (still C158), a leader for a confederation, a head for a league, alliances between leagues and empires, and varied societies of other kinds (a commercial network on land, a successor realm that has a name). Seed 210 of the continents preset fails in `plan_identities`, a land-layer fault that is not R7d's.

## Technology and regional families (R7b)

**Status:** implemented on 2026-10-22 (generator 0.9.28, algorithm epoch 4, C159); NOT GAME VALIDATED, in-game test pending (see the experiment of R7c). Designed in [R7b and R7c design](r7-technology-and-empires.md), claims C155–C157.

**Why.** An age-of-traditions advance above a country's `starting_technology_level` starts unresearched, so a higher level starts a country with more advances (C155). Vanilla gives 191 of its 223 American states level 2, 17 level 1 and 11 level 0. Up to 0.9.27 the generator wrote no level, so a state took its culture's template level or one complexity threshold: 109 of 131 states started at level 0 (C156). Advances and units of the Americas follow three regional families chosen by the capital's region or area (`is_capital_mesoamerica`, `is_capital_in_south_america_or_carribean`); the culture followed only the climate, so a Mixtec state could get the woodland advances (C157).

| Rule | Method (module `eu5_technology`, `eu5_natives`) |
|---|---|
| Calibration | `vanilla_state_levels`: for every vanilla American landed country the level its entry writes, else the highest among its includes; a country with neither is left out (4 on 1.4.3). The sorted result is 11 × 0, 17 × 1 and 191 × 2. |
| Level of a state | The ordinary states rise by capital complexity, then capital population, then tag. The state at 0-based rank `i` of `n` takes the vanilla level at index `(2i + 1) m // (2n)` of the `m` levels (`quantile_levels`, the rule of the harbours). The vanilla distribution is reproduced on any world and complexity only sets the order; the pockets of state land away from the hearths therefore take vanilla's 0 and 1 [INFERRED design]. |
| Great empires | The highest vanilla state level (2), as they lead vassals (C99). R7c raises it. |
| Tribes | No level; their templates already match vanilla. |
| Template | `template_for_level`: the culture's own vanilla state template (with its coast variant) stays while `L(own) ≤ level ≤ L(own) + 1`, where `L` is the template's level (none counts as 0), as vanilla pairs them; otherwise the advanced monarchy for a level it reaches and the plain one for the rest. This replaces the old complexity threshold of 700‰ (`ADVANCED_PERMILLE`). |
| Family | `families` reads the two triggers of `in_game/common/scripted_triggers/location_triggers.txt`: a location is Mesoamerican if its area or region is listed by the first trigger, South American if listed by the second, else North American. Missing or empty triggers and keys that are no American region or area fail the build. |
| Homeland | The vector of a culture, a religion or a zone gains the three family shares, weighted by population and counted twice like climate (`FAMILY_WEIGHT = 2`, the one free constant). A vanilla culture takes them from the locations of its 1337 pops and a generated zone from the region and area of its cells in the plan. Religion matching, culture matching and the diaspora all read the vector; noise, slack and preferred lists are as before. |
| Why the culture follows the family | Region keys carry many vanilla scripts besides the advances (units, unique buildings, names, situations, colonial content), and the hierarchy places them at the vanilla positions; choosing region keys by content would change the hierarchy and is out of scope. |

### Results (C159)

Four builds of the offline acceptance, each against the same world built before the change (base builds on 0.9.27):

| World | States | Levels 0 / 1 / 2 | Agreement ‰ states / tribes / population | Homeland distance with / without families | Templates replaced | Vassals (before → after) |
|---|---|---|---|---|---|---|
| continents 3706823338 | 185 | 9 / 15 / 161 | 924 / 933 / 943 | 3258 / 3071 (×1.061) | 18 | 15 → 20 |
| archipelago 5 | 107 | 5 / 9 / 93 | 990 / 976 / 991 | 2689 / 2463 (×1.092) | 0 | 13 → 14 |
| small_continents 7379108625698230220 | 131 | 7 / 10 / 114 | 1000 / 950 / 996 | 3610 / 3476 (×1.039) | 0 | 9 → 10 |
| the same, `empire_permille` 0 | 140 | 7 / 11 / 122 | 1000 / 949 / 996 | 3600 / 3465 (×1.039) | 0 | 6 → 10 |

Vanilla is 11 / 17 / 191 of 219, so the level histograms are the vanilla quantiles to within one state. On the world of C156 the states at level 0 fall from 109 to 7, and the agreement of states with their culture's family from 427‰ and of the population from 404‰ to 1000‰ and 996‰. `FAMILY_WEIGHT = 2` met every criterion at the first attempt (agreement of states and population at least 900‰, homeland distance at most 1.15 times that without the families), so it was not tuned. `in_game/map_data`, `in_game/gfx`, `14_development.txt` and `03_markets.txt` are byte-identical to the base build in all four worlds: land, development and markets do not depend on cultures or levels. Few templates are replaced because only 62 of the 730 vanilla cultures led a state in vanilla (their templates are level 2 for 46, level 1 for 7 and level 0 for 9); every other culture has no own template, so the level alone chooses.

**Report.** `report.json` section `technology`: histogram of the levels of the generated states and of vanilla with the tags at each generated level, the template levels of the tribes, templates replaced, `family_agreement_permille` for states, tribes and population (a pop agrees when its culture's vanilla family, the family of most of its 1337 pops, is the family of its location; the diaspora's 50-person pops are left out), `homeland_distance` (population-weighted mean L1 distance of each culture zone to its culture, family entries left out, for the cultures chosen and for those a second matching with a family weight of 0 chooses) and the number of vassals.

**Checks.** `verify_technology` (export): every generated state writes one level of the vanilla set and a tribe none; levels do not fall along the rising complexity of the capitals (great empires apart); every state has `L(template) ≤ level ≤ L(template) + 1`; every vassal lord has `level ≥ overlord_level` and `L(template) ≥ overlord_level`. Tests: `tests/test_technology.py` (families, calibration, quantiles, template rule, records, report helpers, rejections) and the optional local test of `tests/test_local_install.py` (11/17/191, the family lists and 380 / 276 / 74 cultures by family).

**Open.** Whether the engine honours a written `starting_technology_level` for new tags and researches the advances of the level, and whether the written level alone makes a lord's vassals valid (the log pattern of C99), are in-game questions.

## Checks

- Synthetic tests (`tests/test_societies.py`, `tests/test_natives_eu5.py`): determinism and seed dependence; population total; state share; the fertile hearth; connected, nested zones; disjoint, connected polities with their capitals; country texts parse; tags avoid reserved words; generated pops replace removed ones.
- Export invariants (`_verify_natives`): unique fresh three-letter tags; every country holds generated land only, with its capital, and no location twice; pops and ranks lie on generated land.
- Removed vanilla tags (`country_definition_outputs`, `verify_country_tags`): vanilla defines a tag only together with its 1337 setup entry, and the engine creates every defined tag as a country, so the removed American tags also leave the definition files in `in_game/setup/countries/` (C86). The export fails if the tags defined without a setup entry, or set up without a definition, differ from vanilla's (only `DUMMY`, `MER` and `PIR` are defined without a setup entry). Vanilla scripts keep their references to removed tags, as they reference formable tags without a definition (C89).
- Government types (`template_governments`): a generated country writes the government type and heir selection that the vanilla countries with its template write most often (a template may leave the type open, or set a heir selection all its users override, C91, C94); a chosen template that gives no type, itself, through its includes or through its users, fails the export.
- Localization keys (`rnw.loc_keys`, `verify_localization`): the engine hashes keys with MurmurHash3, so every generated key (locations, provinces, areas, tags and adjectives) is claimed against the hashes of all vanilla keys of the installation, and a serial or tag whose hash is taken is skipped (C89).
- Colours (`vanilla_colors`, `map_colors`): generated country colours repeat no vanilla definition (named colours resolved, HSV approximated) and no other generated colour, since the engine logs equal colours (`SWN` = `GTO`, C95).
- Script rewrites (`remap_scripts`, `retire_events`): holy sites, scripted geographies, formables, city graphics and the `map_id` list of the volcano object are rewritten in the base game's and in every DLC's files, province lists included and without repeats; a removed `map_id` entry is dropped, since its object needs a locator. Dynamic historical events whose tags are all removed leave their files, with the follow-ups only they fired and the static modifiers only they applied (58 events of five files and 39 modifiers, C95, C97, C100); the historical base values only removed locations used leave `location_historical_base_values.txt`. A DLC file at the path of a base game file stops the export.
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

## TR46 long-run expansion follow-up (2026-10-25)

[V-LOCAL / V-EXEC C325–C328] In the archived 0.12.3 observer campaign, the saved
vanilla default `western_colonisation_only` rule excludes American capitals
from ordinary AI colonial charters. This does not prevent the observed conquest
and consolidation: the two empires grow 53→121 and 86→142 locations, and a
fractured-realm member grows 7→149 while forming LIA. The sea league loses all
owned land by the first preserved checkpoint, 1497.4.1. Frontier settlement is
a distinct geographically gated cabinet action, with no active use globally at
either preserved checkpoint; its exact AI selection boundary remains unknown.
No rule override, AI bonus or claim of vanilla-normal growth follows from this
one run. See [the complete findings](research/tr46-native-expansion.md) and
[experiment 059](../experiments/059-native-expansion/README.md) for every actual
extraordinary society's land/subjects, ordinary/pop cohorts, successor handling,
conditional league-capacity warning and the limits of saved histories.
