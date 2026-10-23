# Offline audit of N0–N4 (content plan, F1 and F2)

**Date:** 2026-10-23. **Generator:** 0.10.10 audited, 0.10.11 (epoch 21) carries the repairs. **Game:** EU5 1.4.3 data, executable 1.4.4 (Steam build 26142040). **Status:** offline; no game launch. The runtime verdict of N4 stays NOT-RUN (F3); of N0 to N3 it is the owner's sittings 036 to 038 (C199–C211), re-read here.

The audit reads, and does not repeat, checks that were already made: the 1,141 tests, the read-only local tests, the reference world of epoch 20, and the logs of the sittings the owner played anyway. What it adds is a different question asked of the same material: *what does the finished world hold, object by object, against what the game ships, and against what the engine said of it?* Evidence labels as in [AGENTS](../../AGENTS.md); numbers are [V-EXEC] unless marked.

## Method

1. **Worlds.** The reference world (`RNW1-0426C-SYW6B-MW73Y-C0050-M00ZJ-9C0`, epoch 20) made with `PYTHONHASHSEED` 1 and 7; the same code with the peoples rolled once and with the resources rolled once; after the repairs the reference world of epoch 21 (`...-P001G-B20`) and the layer test again (C229, C230).
2. **Object-level reconciliation (F1).** Every top-level script object of the 2,467 script files the export may rewrite (the game's and its three DLCs'; 52 of them are rewritten), tokenised and compared with the mod's copy; each difference classified as a location-key substitution, a closed gate (`always = no`), a rebinding, or an absence, and the result laid against the decision of the table (C225). Setup files, country definitions, localization and the map were compared separately (C227).
3. **Residual references.** Every object of the finished scripts searched, with the inventory's own reader, for American keys that the generated world does not have (C223).
4. **The engine's verdict.** `error.log` of sitting 038 (the last in game, 0.10.7) read line by line against the stored vanilla baselines of 1.4.1 and 1.4.2 and against what each message names (C222, C224).
5. **Review (F2).** The N0–N4 modules read for quality; searched for lint escapes, unsorted file-system iteration, clocks, randomness and broad `except`; determinism, layer ownership and Old World preservation proved from the worlds above.

## F1. The inventory against what the export does

### Counts (636 consumers)

Since 0.10.6 the inventory scans `gfx/images` as well, so the N0 count of 634 is now **636 consumers: keep 391, rebind 6, neutralize 86, replace 153**. By reason: keep 264 inert (243 coats of arms of retired tags and 21 objects gated by them), 68 positional, 39 generic, 18 homeland, 2 name; rebind 6 culture; neutralize 49 identity, 28 inert, 7 canal, 2 illustration; replace 102 retired, 45 identity, 5 inert, 1 lost.

### What the finished world holds (reference world of epoch 21; epoch 20 differs in the five province remaps of F1-1)

| Decision / reason | Objects | Observed in the mod |
| --- | --- | --- |
| keep / generic | 39 | changed only by location keys (38 remapped, sea zones included; one with a dropped `map_id` entry) |
| keep / homeland | 18 | the holy sites: placed by the peoples where the religion lives, else by the nearest generated cell |
| keep / positional | 68 | 2 remapped, 66 unchanged (the keys they name exist: 153 of the 154 American areas, all 14 regions and both subcontinents are kept; `moqoit_area` is dropped and no object names it) |
| keep / inert, name | 266 | unchanged (every inert row that has a gate names a retired tag in it: 27 of 27) |
| rebind / culture | 6 | `INC_f` rebound to 101 places of its culture, `AZT_f`, `IRO_f`, `MAY_f`, `PUE_f` too thin and closed, the Huitzilopochtli start effect closed (no seat) |
| neutralize / identity, canal | 56 | gate closed in all 49 identities and the 4 canal objects that have one; the 3 ungated canal objects (a footprint, a map object, an achievement) are unreachable behind them |
| neutralize / illustration | 2 | the two DLC pictures dropped |
| replace / identity | 45 | gate closed in all |
| replace / retired | 102 | absent: exactly the 58 events and 44 modifiers the exporter retires |
| replace / inert, lost | 6 | untouched but one remapped; unreachable (a retired tag in the gate or in `country_potential`, or a variable only retired events set) |

No object of the game's scripts changed that is not in this table, except two templates and a comment: the two DLC `city_data` templates (F1-2, now dropped with their places) and a commented-out line of `situation_effects.txt` (the remap rewrites comments too; harmless). Every difference of every object was classified: a location key replaced by a generated one, a gate closed, the two rebindings, a dropped picture or model, or an absence; none is left over. No object vanished that the exporter does not retire. The 82 guarded events of the export's report are 49 + 33 of the table.

### Findings

**F1-1. The remap missed `province_definition:KEY` (C223) — repaired.** `eu5_remap.SCOPE` read `location:` and `province:` and not `province_definition:`, the scope the game writes for a province in a trigger. Five objects kept a removed province: one live event (`exploration_monthly.39`, keep/generic: five provinces round James Bay) and four whose gate is closed (`flavor_iro.31`, `flavor_iro.63`, `flavor_eng.235`, two scripted country names). The engine checks the key when it loads the scripts, whatever the gate: the owner's own `error.log` of sitting 038 has **18 lines** `Invalid province_definition key!` for these 11 keys (none in either vanilla baseline), and C211's "the rest is the vanilla baseline" was wrong. 0.10.11 remaps the scope; the file of `exploration_monthly.39` is now written (793 files).

**F1-2. Two DLC monuments were moved to random places (C226) — repaired.** The packs of ancient monuments and of sacred sites each carry the 3D model of one American pyramid as a *unique building* of one location (`only_in_location = tehotihuacan`, `= cholollan`). The inventory's reader sees keyed top-level objects only, and these entries sit inside a `template` block of raw code, so no table row decided them and the remap moved each to the nearest generated cell (`rnw_loc_03274`, `rnw_loc_03356`) with its tooltips linking the retired holy site and work of art; the pictures of the same two places were already dropped (a picture shows its place). 0.10.11 drops the entries with the places (`drop_monuments`, beside `drop_illustrations`); the mesh lists stay and nothing names them. That the engine takes an unused mesh list is [UNKNOWN] and expected (the game has the same state whenever a DLC is not owned).

**F1-3. A reason that no code backed (C228) — repaired.** The temple of Tenochtitlan was decided `replace/retired`, a reason that means "retired by the exporter"; nothing retires a building. It is inert: `country_potential = { has_or_had_tag = TNC }`. Now `replace/inert`.

**F1-4. The stage markers were intentions, not carriers (C228) — made checkable.** N0 gave each replaced object the stage that was to carry its purpose, and C185 already said the markers are no equivalences. Nothing said what in the generated world carries what. `content_decisions.CARRIERS` now does, for all 153: the family (story, formable, places, colonial names) that tells a story of the same kind, or a note beginning `none:` with the reason. **131 are carried by 11 families; 22 are carried by none**, each with a reason:

| Chain | Objects | Carrier |
| --- | --- | --- |
| Potosí and the silver chain; the five natural bonuses | 4 events, 5 modifiers | exceptional places (the deposits; the mita and discoverer events have no story) |
| Cahokia (river city) | 23 events, 22 modifiers | river centre |
| pilgrimage, the temple, the Hurin Qusqu privilege | 4 | sacred centre |
| Aztec: pyramid, famine year, triple alliance, temple, lake, tzompantli, Moctezuma | 7 events | sacred centre, harvest, great alliance, empire and periphery |
| Aztec: a ruler, a legal reform, a dynasty; diseases; the 52-year cycle; its 4 modifiers | 3 + 3 + 3 events, 4 modifiers | **none** (persons; the game has diseases of its own; a calendar of one people) |
| Inca succession and conquest (`flavor_csu`) | 7 events | **none** (named persons) |
| Iroquois council, harvest, modifiers, decision | 7 events, 6 modifiers, 1 decision | great alliance, harvest |
| Iroquois interactions (form closer bond, merge tribe) | 2 | **none** |
| Pueblo roads, irrigation, seats, a reunited people | 6 events, 7 modifiers | route and market, harvest, cultural union |
| Colonial rebellion and independence | 7 events | colony |
| `USA_f`, `CAN_f`, `MEX_f`; the founding of a federation (21 events) | 3 formables, 21 events | postcolonial federation (and the colony story); the founding steps, buildings and persons have no counterpart |
| the eight scripted country names | 8 | colonial names |

A carrier is a design relation [INFERRED], never an equivalence; the table is the place to disagree. `tests/test_content_inventory.py` fails if a replaced object has no carrier or a stale one, if a family named does not exist, if `none:` and an empty list disagree, and if the stage of a replacement is not the stage of one of its carriers; the local drift test repeats it on the installation and `rnw content-inventory` reports it.

### Accepted residue (not repaired, recorded)

- **Three "never set" notices** (`chk_no_more_plight_events`, `enable_hurin_qusqu_privilege_variable`, `unlocked_building_great_temple_of_tenochtitlan`): the engine says a variable is read and never set, because the events that set them are retired. The readers are inert; removing a privilege and a building that other retired objects name would leave dangling references, which is worse than a notice. They are the 3 lines that `error.log` of 038 has beside the baseline's 16.
- **The mislabelled "baseline".** C208 and C211 called the rest of the log vanilla. It is not all: see below.

### Setup, localization and map

- The 11 American country files lose exactly the **544 retired tags** (every tag they define; none of the Old World files changes) and no retired tag is defined elsewhere.
- Of the ~7,300 setup records the export deletes (`main_menu/setup/1337`), each names a removed key or a retired tag or is keyed by one; the exception is the 14 vanilla development values of the American regions, which the start development of R7a replaces. **No Old World record is deleted**, and none of the Old World countries' records changes.
- The mod's `replace/` localization overrides 167 keys, all of them American areas and regions; no Old World text is overridden.
- `outside_canvas_identical` and `old_world_contacts_lost = 0` hold in the report of every world made.

## The engine's verdict on sitting 038 (C224)

`error.log` of sitting 038 (0.10.7 world, probe 0.3.0, EU5 1.4.4): 775 lines. The baselines stored are 1.4.1 and 1.4.2; there is none of 1.4.3 or 1.4.4 without the mod, so what is not ours is vanilla by elimination [INFERRED]; what is ours is shown by its names.

| Lines | What | Ours? | Now |
| --- | --- | --- | --- |
| 18 | `Invalid province_definition key!` (11 keys, 4 objects) | yes, F1-1 | repaired in 0.10.11 |
| 18 | `Event #rnw_… is missing a title` (8 events of the mod, 2 of the probe) | yes: the engine wants a title of a hidden event too, and the game's own hidden events carry `title = empty_text`, `desc = empty_text`, `outcome = neutral` | repaired in 0.10.11 (the probe's `rnw_probe.3` is left) |
| 3 | variable read but never set | yes, retired setters | accepted |
| 96 (48 sea zones) | `Coastal Seazone 'rnw_sea_…' has no ports connected to it` | yes, the generated sea (C211 saw them) | not N0–N4; open for the geography phase |
| 4 | `Location 'bermuda' / 'st_helena' … is coastal but has no port setup` | yes [INFERRED]: vanilla `ports.csv` links them to `bermuda_island` and `st_helena_coast_2`, sea zones the canvas replaced, and the two locations stayed | not N0–N4; open for the geography phase |
| 1 | `Culture has no pops in the setup: tzeltal_culture` | unknown (not in the older baselines) | [UNKNOWN] |
| the rest (~600) | tributary, cabinet actions, `gc_*` effects, absent situations and laws, DLC `d009` and others | no: vanilla 1.4.3 data | — |

So the claim of C208 and C211 stands for the faults of 036 and for the probe, and was wrong as a statement about the whole log.

## F2. Code, determinism, layers, the Old World

### Code quality

`ruff`, `basedpyright` and `clippy` pass; 1,152 Python and 23 Rust tests pass. In the 19 modules of N0–N4 there are 7 lint escapes, each with its reason (five `PLR0913`, one with `PLR0917`, for a parameter list that names its inputs; one `PLR2004`; one `S101` for a narrowing assert), one `pragma: no cover` for an unreachable branch, no TODO, no clock, no randomness outside `derive_seed` streams, no broad `except`, and every directory listing that decides an output sorted. The planner (`content.py`) reads as its docstring says: each draw from a stream named by family and object, the order of the inputs never decides, a family without a bearer is a recorded reason. Findings: `eu5_probe._anywhere` listed files in file-system order, so the error message could differ between machines (sorted now; the probe makes no world); the exporter had no check that its outputs keep what the table decides, which is how F1-1 passed 1,141 tests (below).

### What the export now refuses (`content_check.check_outcomes`, C223)

After the decisions are carried out, the export stops unless (a) every object of the game's scripts is still there or is one the exporter retires, and (b) no object, whatever its gate, names an American location, province, area, region or subcontinent that the generated world lacks (a word the table calls a given name is no reference). On the reference world it checks 43,323 objects in 52 rewritten files. It repairs nothing; it would have stopped 0.10.10 on F1-1.

### Determinism (C229)

The reference world of epoch 20 made with `PYTHONHASHSEED` 1 and 7 and in the local test (a random seed): the same digest `6589711d…`, 792 files; the two full exports differ in nothing but the mod's own id in `.metadata/metadata.json`. The reference world of epoch 21 made with seed 11 and in the local test: `88e1d8d8…`, 793 files. The planner's tests include the order of the inputs and the non-interference of families.

### Layer ownership (C230)

Compared file by file, all of them, on three worlds of one land (the old test compared six):

- **Resources rolled:** exactly one file changes, `in_game/map_data/location_templates.txt` (the raw material and the exceptional places). The stories, the formables, the countries and the texts are byte-identical.
- **Peoples rolled:** 49 files change besides `.metadata` (33 of them localization, 16 the start's countries, pops, cities, markets, development, opinions and diplomacy, the natives' definitions, the `inti` holy sites, the formables with their flags, arms and colours, the story events and modifiers) and three files go (the sacred centre's events and privilege, the roads: this world has no holy place in a state of its own faith and no empire). No file of `in_game/map_data`, `in_game/gfx` or `main_menu/gfx` changes, the resources' file does not, and the colonial names (a function of the land's regions) do not.

`test_local_layers_keep_to_themselves` now asserts exactly this (resources: one file; peoples: only the directories of the start, the countries, the common scripts, the events and the texts).

### The Old World

Held by the checks above: the map (`outside_canvas_identical`, no contact lost), the 544 tags (no Old World definition changes), ~7,300 setup deletions (no Old World record among them), the scripts (every changed object is in the table and only by location key, gate or rebinding; no Old World object vanished), the localization (167 American keys), the new refusal of residue. The two Old World islands that lost their ports (Bermuda, St Helena) are a geography fault, not a content one (above).

## What changed in 0.10.11 (epoch 21)

`province_definition:` remapped; DLC monuments dropped with their places; hidden events written as the game's are; `check_outcomes`; `CARRIERS` and its checks; the layer test over all files; two reasons of the table (the temple). The reference world has 793 files (one more: the exploration event's file is written) and differs from epoch 20's in 14 files exactly: 9 story-event files (the hidden heads), 2 scripted-name and event files (the provinces), the exploration events, the 2 monument templates. Installed as `rnw_exp_world_t3htedmcwr` ([INSTALLED](../../experiments/INSTALLED.md)).

## Open (nothing here blocks the plan)

- [UNKNOWN] whether `error.log` is free of the lines above after 0.10.11, and what the engine says of N4 at all (F3: NOT-RUN).
- The geography faults of the log (the coastal sea zones, the ports of two islands) belong to the geography phase.
- The 22 objects with no carrier are documented losses, not defects; the owner may want one of them told (the Inca or the Aztec succession is the likeliest) and that is a content decision for N5's company.
