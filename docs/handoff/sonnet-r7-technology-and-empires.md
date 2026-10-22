# R7b and R7c: technology and great empires from the societies (Sonnet tasks)

**Designed by Opus 5.5 on 2026-10-22 for Sonnet 5.5 to implement.** There are two tasks with two commits: R7b (S09) first, then R7c (S10) on top of it. Together they finish roadmap phase R7 offline, after [R7a](sonnet-r7a-development.md). Both change generated output and are NOT GAME VALIDATED. Do not launch the game; the owner batches the in-game test (experiment below).

**Status, 2026-10-22: implemented.** R7b is generator 0.9.28 (C159) and R7c 0.9.29 (C160); see [natives](../natives.md) and [experiment 028](../../experiments/028-technology-and-empires/README.md) (NOT-RUN, installed as `rnw_exp_world_canszr3phf`). The in-game gate remains the owner's.

Before you start, read [AGENTS.md](../../AGENTS.md), [natives](../natives.md), [economy](../economy.md), section A of [ADR 0010](../adr/0010-layered-worlds-and-a-generator-of-its-own.md) (the peoples layer), claims C155–C158 and this page. Start on a clean working tree. If the 0.9.27 cover candidate is still uncommitted, stop and ask the owner.

## Where R7 stands

The roadmap gate for R7 has two parts. A generated region must play through exploration, colonisation and conquest without broken logs. Extraordinary strength must have explicit causes and weaknesses.

| Part of R7 | State |
|---|---|
| Pops, markets, ranks | Done in R6 ([natives](../natives.md)). |
| Development, harbours, market villages | Done in R7a ([economy](../economy.md)). |
| Institutions | Nothing to do: `08_institutions.txt` names no American location, and institutions spread in game [V-EXEC C155]. |
| Roads of ordinary states, rivals | Nothing to do: the vanilla 1337 Americas have none (`09_roads.txt`, `20_rivals.txt`) [V-EXEC C155]. |
| Technology | **R7b** |
| Extraordinary societies | Their frequency exists (`natives.empire_permille`, 0.9.15). Their causes and weaknesses are **R7c**. |

## Problem

### Technology does not follow the societies

In EU5 1.4.3 an age-of-traditions advance whose `starting_technology_level` is higher than the country's own level starts unresearched. The comment at the top of `in_game/common/advances/0_age_of_traditions.txt` says so [V-LOCAL C155], so a higher level starts a country with more advances [INFERRED]. Twenty-five advances carry a level from 1 to 4. A country gets its level from its template or from its own entry in `10_countries.txt`. Of the 983 Old World entries that write the level themselves, 915 write 3.

The levels of the vanilla American landed countries come from their own entry, else from the highest level among their templates [V-EXEC C155]:

| Level | 0 | 1 | 2 | none |
|---|---|---|---|---|
| Vanilla American states | 11 | 17 | 191 | 4 |
| Generated states, world of C156 | 109 | 0 | 22 | 0 |

The vanilla states below level 2 are Cahokia, the Haudenosaunee nations, Colombian chiefdoms and smaller Mesoamerican polities with the plain monarchy or tribe template. Twenty-eight American entries write their own level. Twenty-three of them write their template's level or one more. The five Haudenosaunee nations write 0 under a level-1 template.

The generator writes no level. A state takes the level of its culture's vanilla template. Without one, it takes the advanced template when its capital's complexity is 700‰ or more and the plain `amerindian_monarchy` (level 0) otherwise. On the world of C156, 83% of the states start at level 0, against 5% in vanilla. The mean society development term (R7a) at the capital is 3.43 for level-0 states and 6.32 for level-2 states. The society model therefore reaches technology only through one threshold and through the culture's vanilla template.

### Regional advances and units follow the region key, the culture follows the climate

Vanilla gives the Americas three regional families [V-LOCAL C157]:

- **Mesoamerica** has the tributary tree (`system_of_tributaries`, pyramids, ball game).
- **South America** has the valley tree (`valley_irrigation`, terraces, mountain roads, llama farming).
- **North America** has the advances of the northern regions and the units of `unit_types/a_north_american.txt`.

Two scripted triggers select a family from the capital's region or area: `is_capital_mesoamerica` and `is_capital_in_south_america_or_carribean`. A capital that neither trigger matches is North American.

Generated regions keep the vanilla keys and take the part nearest each key's vanilla centre (`eu5_newworld._land_areas`). The culture of a zone is matched by climate, vegetation, topography, state share, latitude and coast. Vanilla cultures and religions are almost unmixed by family: on average a culture has 99.9% of its 1337 pops in one family, and a religion 99.8% [V-EXEC C157]. On the world of C156, however, only 56 of 131 states and 173 of 320 tribes have their capital in their culture's family. Only 40.4% of the population lives in its culture's family. A Mixtec state can therefore get the woodland advances and units, and a Mississippian one the terraces.

### A great empire is only large

The one great empire of that world (ERY) has 58 locations and 1,425 pop units. Vanilla's largest American states are Mayapan (COC, 892) and the Tarascans (TAR, 535). ERY has three vassals and level 2, like 191 vanilla states. It has no rank, no roads, and no diplomatic weakness [V-EXEC C156]. Its culture, Atakapa, belongs to the north family, but its capital lies in the south family. The product spec asks for strength from technology, infrastructure and organisation, with weaknesses such as logistical strain and factionalism ([product spec](../product-spec.md)). The natives page records that the generator "cannot make the technology of the Western powers". This was true of templates. It is not true of `starting_technology_level`.

## R7b: technology from the societies (task S09)

### Goal

A state's technology level comes from the same complexity as its development. The template follows the level, as in vanilla. A culture belongs to the regional family of the land it lives on, so its advances, units and identity agree. There are no new settings. The vanilla engine and interface files do not change.

### A. Level by complexity

1. **Calibration (build time).** For every vanilla American landed country (the set `vanilla_natives` already reads), take its own `starting_technology_level` when it writes one. Otherwise take the highest level among its includes; `template_levels` already resolves includes. Leave out a country that has neither. Keep the sorted levels. On 1.4.3 these are 11 × 0, 17 × 1 and 191 × 2 [V-EXEC C155].
2. **Order.** Sort the generated landed countries, great empires excepted, by capital complexity, then capital population, then tag.
3. **Quantile.** The country at 0-based rank `i` of `n` gets the vanilla level at index `(2i + 1) × m // (2n)` of the `m` sorted levels. This is R7a's harbour rule: it reproduces the vanilla distribution on any world, and complexity only sets the order. State pockets away from the hearths (`state_spread_permille`) have the lowest complexity, so they take vanilla's 0 and 1 [INFERRED].
4. **Great empires** take the highest vanilla state level (2). They lead vassals, which needs at least `overlord_level` (C99). R7c raises them.
5. **Output.** Each landed country record writes `starting_technology_level = <n>` right after its `include` lines, as vanilla does (`ZAP`).
6. **Tribes** (pop countries) write no level. Their templates already match vanilla: vanilla has 127 at 0, 1 at 1 and 193 without a level; the generated world has 25 at 0 and 295 without one [V-EXEC C155, C156].

### B. Template follows the level

Vanilla never pairs an advanced template with a lower level: every American state with a level-2 template has level 2. Written levels are the template's level or one more (`amerindian_monarchy` + 1; tribe templates without a level + 0 or + 1). The one exception is the Haudenosaunee, who write 0 under a level-1 template [V-EXEC C155]. A template's laws and reforms (`calpixque_system_policy`, the `altepetl` reform) may also need advances, so the rule below never goes under the template's level and is stricter than vanilla. Let `L(t)` be the level of template `t`, with no level counting as 0. Replace the `advanced` threshold of `_include` with this rule:

- Keep the culture's own vanilla state template (with its coast variant, as today) when `L(own) ≤ level ≤ L(own) + 1`.
- Otherwise take `ADVANCED_STATE` when `level ≥ L(ADVANCED_STATE)`, else `DEFAULT_STATE`.

`ADVANCED_PERMILLE` goes. Keep the empire rule of `_include` as it is. Vassal lords must satisfy both `level ≥ overlord_level` and `L(template) ≥ overlord_level`. The template condition is the one C99 proved in game. The experiment shows whether the written level alone is enough.

### C. Regional family in the homeland

1. **Families (build time).** Parse `in_game/common/scripted_triggers/location_triggers.txt` with `rnw.pdx`. Inside `is_capital_mesoamerica` and inside `is_capital_in_south_america_or_carribean` (vanilla's spelling), every `region = region:<key>` and every `area = area:<key>` names a member. A location is `mesoamerica` if its area or region is listed under the first trigger, `south_america` if listed under the second, else `north_america`. On 1.4.3 the first trigger lists `mesoamerica_region`, `central_america_region`, `xalisco_area` and `zacatecas_area`; the second lists the Colombia, Andes, Brazil, Chaco, La Plata and Caribbean regions [V-LOCAL C157]. Fail loudly if a trigger is missing, if it lists nothing, or if it lists a key that is no American region or area of the vanilla hierarchy.
2. **Homeland vector.** `homeland` gains the family shares (permille, weighted by population), counted twice like climate: `FAMILY_WEIGHT = 2` [INFERRED design]. A vanilla culture or religion takes its shares from the locations of its 1337 pops. A generated zone takes them from the region and area of its cells in the plan. Religion matching, culture matching and the diaspora all read these vectors. Noise, slack and preferred lists stay as they are.
3. **Why the culture follows the family, not the other way.** Region keys carry many vanilla scripts besides the advances: units, unique buildings, country names, situations and colonial content. The hierarchy places them at the vanilla positions. Moving region keys by content would change the hierarchy (Opus work; see Out of scope).

### D. Report and invariants

Add a `technology` section to `report.json` with:

- the histogram of state levels, generated and vanilla, with the tags at each generated level, and the histogram of tribe template levels;
- the number of templates the level rule replaced;
- `family_agreement_permille` for states, for tribes and for population (a pop agrees when its culture's vanilla family is the family of its location);
- `homeland_distance`: the population-weighted mean L1 distance, without the family entries, between each culture zone and its culture. Give it twice: for the cultures chosen, and for the cultures that `_identities` chooses with `FAMILY_WEIGHT = 0`. Run `_identities` a second time for this; the matcher uses only hash noise, so the extra call changes nothing else.
- the number of vassals.

`verify_technology` raises `NewWorldExportError` (call it next to `_verify_natives`) if any of these fail:

- every generated landed country writes one level from the vanilla set, and no tribe writes one;
- levels do not decrease along the order of A.2;
- every landed country has `L(template) ≤ level ≤ L(template) + 1`;
- every vassal lord has `level ≥ overlord_level` and `L(template) ≥ overlord_level`.

### Code placement

| Where | What |
|---|---|
| `src/rnw/eu5_technology.py` (new) | `Families` (frozen: family by region and by area) and `families(text, regions, areas)`; `vanilla_state_levels(setup_text, levels, american)`; `quantile_levels(n, vanilla)`; `template_for_level(...)`; `verify_technology(...)`; the report helpers. Pure functions on texts and lists, like `eu5_development.py` |
| `src/rnw/eu5_natives.py` | `VanillaNatives` gains `families` and `state_levels`. `homeland` takes the family of each location, and `vanilla_natives` and `_zone_homelands` pass it. `Country` gains `level: int \| None`. `_countries_of` computes the levels first and passes the level to `_include` instead of `advanced`. `able` checks both levels. `country_records` writes the level |
| `src/rnw/eu5_nw_export.py` | `verify_technology` and the report section |
| `AGENTS.md` | `eu5_technology.py` in the code layout |

### Tests

Add `tests/test_technology.py` and update `tests/test_natives_eu5.py`, with synthetic fixtures only:

- `families` parses a small trigger text. A location in a listed area of an unlisted region is Mesoamerican. A missing trigger, an empty trigger and an unknown key each fail.
- Calibration: an own level overrides the template, includes are resolved, a country with neither is left out, and Old World countries are ignored.
- `quantile_levels`: `n == m` reproduces the vanilla multiset. Levels never decrease. Ties break by population, then by tag.
- Template rule: a culture's template is kept within one level. A level-2 state of a tribe culture takes `ADVANCED_STATE`. A level-1 state of an advanced culture takes `DEFAULT_STATE`. Coast variants still apply.
- `homeland`: the family entries count twice. A zone in a Mesoamerican region takes a Mesoamerican culture over a northern one whose climate fits better by less than the family gap.
- `country_records` writes the level after the includes, and the text parses. Tribes get no level.
- `verify_technology` rejects a missing level, a level outside the set, a level on a tribe, a template above the level, a template two below the level, and a vassal lord below `overlord_level`.
- Optional, in `tests/test_local_install.py`: on 1.4.3 the state levels are 11/17/191 with 4 left out, and the families are exactly the lists of C.1.

### Acceptance (offline)

1. `uv sync --locked --group dev && make check` passes, and so do the optional local tests.
2. Raise PATCH ([ADR 0003](../adr/0003-versioning.md)) and start a new algorithm epoch with a new reference world, as the last epoch commit did (`rnw/epoch.py`, `tests/test_epoch.py`, `tests/test_synth.py`, `tests/golden_world.json`; renew with `RNW_REPRODUCE=1 EU5_GAME_DIR=... uv run pytest tests/test_local_install.py -k reference`).
3. **Base builds first.** Before you change any code, build these worlds on the clean starting commit:
   - continents 3706823338;
   - archipelago 5;
   - small_continents 7379108625698230220 (the world of C156 and C157);
   - small_continents 7379108625698230220 again, with `{"schema": 1, "natives": {"empire_permille": 0}}` (R7c compares against it).

   Then build the same four with R7b. Build one world at a time, in the foreground, under `timeout 1200`, into `generated/rnw_exp_new_world --replace`. Copy `report.json` and `manifest.json` to gitignored `local_data/r7b/<label>/` before the next build. At the end, confirm with `pgrep -af rnw` that nothing is left running. On each R7b world:
   - every invariant passes;
   - the state level histogram equals the vanilla quantiles;
   - `family_agreement_permille` is at least 900 for states and for population (about 427 and 404 on the small_continents build of C157);
   - `homeland_distance` with families is at most 1.15 × the same without them;
   - every file under `in_game/map_data` and `in_game/gfx`, plus `14_development.txt` and `03_markets.txt`, is byte-identical to the base build. The land, development and markets do not depend on cultures or levels.

   If a criterion fails, change the model, not the threshold, and record why. `FAMILY_WEIGHT` is the one free constant. If no weight meets both family criteria and the distance bound, stop and report the numbers.
4. Documentation:
   - a section *Technology and regional families (R7b)* in `docs/natives.md`, and correct its sentence on Western technology;
   - the next free claim with the builds;
   - a [research log](../research/log.md) entry;
   - a status line on the roadmap R7 row;
   - S09 marked done in the [backlog](sonnet-5.5-backlog.md).
5. One commit.

## R7c: great empires with causes and weaknesses (task S10)

### Goal

A great empire is strong for reasons a player can see in game, and weak for reasons a player can see in game. Each reason uses a mechanism that the vanilla 1337 setup already uses: in the Americas, or for roads in the Old World. The empire keeps what it has (8–16‰ of the land, the largest population, a city capital, the first pick of vassals). Nothing is a flat modifier, and there are no new settings.

### A. Causes

1. **Technology.** The empire level is `min(T, S + 1)`. `T` is the highest level that any vanilla template or 1337 country entry gives (3). `S` is the highest vanilla American state level (2). On 1.4.3 that makes 3, the level of 915 Old World countries. The empire then starts with the level-3 advances of the age of traditions: alchemy, cultural acceptance (+1 cultures capacity), merchants, trade, castles and the cog [V-LOCAL C155; INFERRED]. The R7b template rule then gives a level-2 template (its own or `ADVANCED_STATE`), one below the level, as in vanilla.
2. **Rank.** Read the rank keys and levels from `in_game/common/country_ranks/`. The empire gets the highest rank that any vanilla American landed country starts with, as `country_rank = <key>` in its record. On 1.4.3 that is `rank_duchy`, held by the Tarascans and the Itza. It gives +1 diplomatic capacity, +0.5 cultures capacity, two rivals and prestige [V-LOCAL C158]. Fail loudly if no American country has a rank.
3. **Royal roads.** Targets are:
   - the capital of each vassal;
   - each ranked location and market centre of the empire;
   - in each area the empire holds, its most populous location there (ties by key).

   Take the shortest paths from the capital over land contacts only (`LandGraph.edges`, never the sea `links`), through the locations of the empire and its vassals. A move costs the travel cost of the location entered, as in `societies`, with ties by node index. The roads are the union of these paths as unordered pairs. A target that no land path reaches (another island) stays unlinked and is counted. Write `<a> = <b>` lines, sorted by key, into the `road_network` block of `09_roads.txt`. Vanilla's 1,646 road pairs all join locations in pixel contact, which is why only contacts may be used [V-EXEC C158].

### B. Weaknesses

| Weakness | Written | Vanilla precedent [V-LOCAL C158] |
|---|---|---|
| **Fear.** Every independent generated state in land contact with the empire, other than its vassals. | `opinion = { first = <neighbour> second = <empire> type = opinion_threatens_conquest }` and `opinion = { first = <empire> second = <neighbour> type = opinion_prey_to_conquest }` | The Andes block of `18_opinions.txt`: CSU and AYA hold `opinion_threatens_conquest` of URC, and URC holds `opinion_prey_to_conquest` of CSU. The biases are −50 and −25, each for 300 months. |
| **Resentment.** Every vassal of the empire. | `opinion = { first = <vassal> second = <empire> type = opinion_tyrant_overlord }` and `opinion = { first = <empire> second = <vassal> type = opinion_irritated }` | Mayapan: XIU and HEL, vassals of COC, hold `opinion_tyrant_overlord` of COC, and COC holds `opinion_irritated` of them. The biases are −50 and −10. |
| **Diversity.** Nothing is written. The empire's pops keep the cultures and religions of the zones it spans. | Report their shares. | Culture and religion rules make such pops less loyal [INFERRED; in-game check]. |
| **Reach.** Nothing is written. | Report the median travel steps from the capital and the share of locations off the roads. | Control falls with distance from the capital [INFERRED; in-game check]. |

That `first` holds the opinion of `second` is inferred from the vassal holding `opinion_tyrant_overlord` [INFERRED]. Insert the lines into the `diplomacy_manager` block of `18_opinions.txt`. The four bias keys are constants. The build fails if any of them is not defined in `in_game/common/biases/*.txt`. No rivals are written, because the vanilla Americas have none. The AI picks its rivals.

### C. Window

`quick.empires.about` and `control.natives.empire_permille.about` in `rnw/gui/text.py` should say this in one sentence: one state many times the size of the others, with an advanced government, the Old World's technology, a higher rank and royal roads, feared by its neighbours and resented by its vassals.

### D. Report and invariants

Add an `extraordinary` section to `report.json`:

- the calibration: the level, the rank, the four opinion types and the road bound (the 90th percentile of road pairs per owned location among vanilla countries with roads, 1.0 on 1.4.3, C158);
- one record per empire: tag, name, capital, locations, vassals, population and its share of the New World, level, rank, road pairs and pairs per location, unlinked targets, feared neighbours, resentful vassals, foreign culture and foreign religion shares, and median travel steps;
- the same location counts and foreign culture shares for the five largest vanilla American states, for comparison.

`verify_empires` raises `NewWorldExportError` if any of these fail:

- every empire writes the calibrated level and rank, and no other generated country writes a rank;
- every road pair joins two generated land locations in contact, both held by the empire or one of its vassals, and appears once; the road graph of each empire is connected and contains its capital;
- every opinion line joins an empire to a state in the required relation (contact or vassal), and each (first, second, type) appears once;
- no road or opinion line names a vanilla tag or location;
- the Old World entries of `09_roads.txt` and `18_opinions.txt` are identical to vanilla.

### Code placement

| Where | What |
|---|---|
| `src/rnw/societies.py` | `trunk_roads(graph, allowed, capital, targets) -> tuple[tuple[int, int], ...]`, game-independent: Dijkstra over land edges with predecessors, ties by index |
| `src/rnw/eu5_empires.py` (new) | `EmpireCalibration` (level, rank, road bound, checked opinion types) and its reader; `empire_roads`, `empire_opinions`, `road_lines`, `opinion_lines`; `verify_empires`; the report section |
| `src/rnw/eu5_natives.py` | `build_natives` calls the empire functions, since only it holds the land graph, the polities and the vassal pairs. `NativeWorld` gains `roads` and `opinions` as key tuples. `Country` gains `rank: str = ""`, and `country_records` writes `country_rank` after the level |
| `src/rnw/eu5_nw_export.py` | `SETUP_INSERTS["09_roads.txt"] = (("road_network",),)` and `SETUP_INSERTS["18_opinions.txt"] = (("diplomacy_manager",),)`, their additions, `verify_empires` and the report |
| `src/rnw/gui/text.py`, `AGENTS.md` | The two texts; `eu5_empires.py` in the code layout |

R7c draws no random numbers. Empires, vassals and neighbours already exist when it runs, so no stream of the peoples layer moves.

### Tests

Use synthetic fixtures only (new `tests/test_empires.py`, plus `tests/test_societies.py`):

- `trunk_roads`: a line graph gives its path. Of two routes of equal cost, the one with lower indices wins. A target on an island stays unlinked. Sea links are never used. The pairs are unique and sorted.
- Calibration: the level is `min(T, S + 1)` on small texts. The rank comes from a small ranks file and setup. A missing opinion type fails.
- Records and lines: `country_rank` and the level are written, and the texts parse with `rnw.pdx.parse`.
- Opinions: contact gives the fear pair and vassalage gives the resentment pair. A vassal is never a feared neighbour, and nothing repeats.
- `verify_empires` rejects a road pair out of contact, a pair outside the empire and its vassals, a repeated pair, a disconnected pair, an opinion with an unrelated state, a rank on an ordinary state, and a changed Old World road.
- Optional, local on 1.4.3: level 3, `rank_duchy`, a road bound of about 1.0, and all four bias keys defined.

### Acceptance (offline)

1. `make check` passes, and so do the optional local tests.
2. Raise PATCH, start a new epoch and renew the reference world, as in R7b.
3. Build these worlds the same way (one at a time, foreground, `timeout 1200`, reports to `local_data/r7c/`):
   - the three R7b worlds with default settings;
   - continents 3706823338 with `{"schema": 1, "natives": {"empire_permille": 1000}}`, so that every hearth raises an empire;
   - small_continents 7379108625698230220 with `empire_permille` 0.

   Criteria:
   - every invariant passes;
   - every empire has the calibrated level and rank;
   - an empire has at least one road pair when a target is reachable by land, and at most the road bound × (its locations + its vassals' locations) pairs;
   - every empire has at least one written weakness, or its report record says why not (no neighbour by land, no vassal);
   - the empire-free build is byte-identical, except `.metadata`, to the R7b build with the same settings (R7c adds nothing without empires).

   If a criterion fails, change the model, not the threshold, and record why.
4. Documentation:
   - the *Great empires* section of `docs/natives.md` becomes a table of causes and weaknesses;
   - the status and open work of `docs/economy.md`;
   - the next free claim;
   - a log entry;
   - the roadmap R7 row: offline complete, gate pending in game;
   - S10 marked done in the backlog;
   - an experiment record with status NOT-RUN, under the next free number.
5. Install for the owner, as [AGENTS.md](../../AGENTS.md) requires. Make the code with `rnw world-code --preset continents --seed 3706823338 --settings <the 1000 file>`, then run `rnw world CODE --install`. Record the folder and its removal in [INSTALLED](../../experiments/INSTALLED.md) and the code in the experiment record. The game stays closed, and nothing else in the profile changes.
6. One commit.

## Experiment (owner, one batched test for R7b and R7c)

**Hypothesis:** EU5 1.4.3 honours a written `starting_technology_level`, a `country_rank`, generated `road_network` pairs and `opinion` records for new tags and locations. A state's advances follow its level and its family. The empire shows its causes and weaknesses in the ordinary windows.

**Method**, on the installed world:

1. In the country window of a level-2 state, a level-0 or level-1 state (the report's `technology` section lists the tags) and the empire, check that the researched advances match the levels.
2. In the advances of one state of each family, check the regional tree: `system_of_tributaries` for Mesoamerica, `valley_irrigation` for South America, `three_sisters` and the northern advances for North America.
3. For the empire, check its rank title, its roads on the map from the capital to its towns and vassals, the fear of its neighbours and the resentment of its vassals in the diplomacy view, and whether its vassals are valid (the C99 log pattern).
4. Look for `error.log` lines that name `starting_technology_level`, `country_rank`, `road_network`, `opinion` or `rnw_`. Compare with the baseline using `rnw logdiff`.
5. Observe 1337–1400 at speed. Does the empire hold, grow or break? Do the colonisers meet it, and does the log stay clean? This is the R7 gate.

## Decisions the owner may veto

- Great empires start at the Old World's level 3, cog included. That is the EU4 fantasy of the *Great empires* setting (Seldom by default, C125). Lowering it is one constant (`S + 0`).
- Royal roads exist only for great empires. The vanilla Americas of 1337 have none.
- Cultures follow the regional family of the land, so they become partly positional, as latitude already makes them. The alternative, region keys chosen by content, belongs to the hierarchy and is out of scope.

## Out of scope

- The other extraordinary archetypes of the [product spec](../product-spec.md): the maritime culture, the commercial network and the fractured successor realm. They need their own Opus design after this experiment.
- Tributaries. The `tributary` subject type needs a tribal or horde overlord or `allow_tributary_subject`, and no American advance gives that (C158).
- Region keys chosen by content.
- Tribal confederations of generated tribes (vanilla's Haudenosaunee confederation joins landed tribes), alliances, stability or other `currency_data`, `tolerated_cultures`, court languages.
- Buildings other than market villages, institutions, presets and new settings.
- Any change to engine, define or interface files; launching the game.
