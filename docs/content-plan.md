# Random-first New World content: design and staged plan

**Status:** Proposed 2026-10-23 and revised the same day after a check against the installed game (C175–C180). The owner placed its whole scope, R7d included, in 1.0.0 and settled its languages (2026-10-23); N5 remains open. N0 is done offline (C181–C185); the stages after it are not implemented, and no game launch belongs to the plan.
**Baseline:** Generator 0.10.1, algorithm epoch 11; EU5 1.4.3 open beta, Steam build 26105915.
**Evidence:** Existing behaviour is labelled below. Every proposed behaviour is [INFERRED design]; whether the running game accepts it is [UNKNOWN] until observed.

## Design direction

Generate geography and societies first. Then find the opportunities that world holds: a crowded river city, a maritime network, a fragmented cultural region, a sacred centre, an exceptional deposit, a large state with a difficult periphery. Those opportunities carry stories and political goals without prescribing their outcome.

Vanilla supplies the mechanics: religions, buildings, technology, governments, estates, trade, colonization, country titles and established scripting patterns. The generator supplies places, participants, identities and combinations of conditions. Players and AI decide what happens in the campaign.

Randomness governs the world's structure and its opportunities. Causal eligibility governs who receives them. Random event timing replaces neither. A seed is never rerolled until it contains a preferred historical analogue.

The plan covers native and colonial play. Its work is architectural and runs in verified stages (N0–N5 below); no calendar estimate is given.

## What the output does today

| ID | Gap | Evidence | Stages |
| --- | --- | --- | --- |
| G1 | **Vanilla meaning sits on positionally chosen land.** Removed locations and provinces map to the nearest generated cell of their family; every vanilla region keeps its key and every vanilla area key is reused by the nearest generated area. 525 references to the 168 American region and area keys in 38 script files therefore keep their vanilla meaning on whatever land took the key. Part of this is intended: R7b's regional advances follow the region key. Part puts literal history on random land: eight American scripted country names (New Spain, Peru, New York and others) and historical formables such as the Aztecs over whatever generated region holds `mesoamerica_region`. | C179, C180; `build_remap`, `_land_areas` | N0, N1, N5 |
| G2 | **Lost access.** World 6DIV retires 58 events (AZT 16, CHK 22, CSU 7, IRO 7, PUE 6), 39 modifiers and five historical natural-resource bonuses. Retained rewards lose their path: `great_temple_of_tenochtitlan` needs `has_or_had_tag = TNC`, `hurin_qusqu_privilege` a variable that only a retired CSU event sets. | C95, C97, C100; [natives](natives.md) | N0, N1, N3 |
| G3 | **No original stories.** The generator emits no event chains; its event overrides add no event IDs. | `eu5_events.py` | N3, N4 |
| G4 | **No procedural formables.** Historical formables follow G1. | C175 | N3, N4 |
| G5 | **Exceptional resource places vanish** with the locations that held them. | `retired_base_modifiers` | N1 |
| G6 | **The eleventh language is missing.** The game has eleven official languages, Turkish among them with as many files as English; the export writes ten from a fixed list (`LANGUAGES`), so a language a patch adds would be missed as well. Every new text inherits the gap. | C178 | N1, L1 |
| G7 | **Few society archetypes.** Only R7c's great empire is generated; the maritime, commercial and fractured archetypes of the [product spec](product-spec.md) are out of R7c's scope. | [natives](natives.md) | R7d |

Not gaps, after the check against the installation:

- **Native adjective equal to the name** is the vanilla convention: 520 of the 544 American country definitions have it (C177). The generator follows it and keeps doing so.
- **Russian grammatical cases** need no inflection algorithm: vanilla's Russian custom localization falls back, for any tag without its own forms, to *державы X*, *державе X* and so on (C176). Whether the fallback reads as expected with a generated tag is [UNKNOWN runtime].
- **Political-form titles** come from vanilla: `country_flavor` picks the title by government, rank and subject type (a tribe is a *people*, a colonial nation a *viceroyalty*) [V-LOCAL EU5 1.4.3, `customizable_localization/country_ranks.txt`]. A native state that changes government changes its title without new content.
- **Target tags without a starting country** are vanilla practice: 95 of the 154 formable target tags have no country definition and no 1337 country (C175).

Invariants for every stage: the Old World is preserved, the world layers stay independent, and nothing reveals concealed geography.

## Evidence and implementation anchors

Project paths are relative to the repository; installed-game paths are relative to `game/` in the installation. Derived game text stays local.

- [V-EXEC inspection] `retire_events` in [eu5_events.py](../src/rnw/eu5_events.py) removes events of retired tags and the follow-ups only they fire. `build_remap` in [eu5_remap.py](../src/rnw/eu5_remap.py) maps removed locations to nearby generated cells and rewrites only location and province references. `_land_areas` in [eu5_newworld.py](../src/rnw/eu5_newworld.py) keeps region keys and reuses area keys by position (C179). None of this proves semantic accessibility.
- [V-LOCAL EU5 1.4.3] `scripted_country_names/00_default.txt` holds twelve entries, eight American, each a country trigger (overlord tag or language) with capital and location triggers on province, area, region or subcontinent keys (C180).
- [V-LOCAL EU5 1.4.3] `formable_countries/readme.txt` documents level, territorial fraction, potential and allow, form effect, name, adjective, tag, flag, colour and the territory lists. A formable-only target such as `ADU` consists of the formable entry, a flag definition, a coat of arms, a named colour and name and adjective keys (C175).
- [V-LOCAL EU5 1.4.3] `customizable_localization/countries.txt` varies a country's name by trigger (`ADU_arabic` under Muslim or Arabic-speaking rule); `ru_EU5_custom_loc.txt` holds the Russian cases with their default fallbacks (C176).
- [V-EXEC inspection] `new_tags`, `country_definitions` and `country_names` in [eu5_natives.py](../src/rnw/eu5_natives.py) generate native identities, flags and coats of arms; [loc_keys.py](../src/rnw/loc_keys.py) reserves localization hashes; `LANGUAGES` in [eu5_nw_export.py](../src/rnw/eu5_nw_export.py) lists the written languages (C178).
- [V-EXEC inspection] [layers.py](../src/rnw/layers.py), [rng.py](../src/rnw/rng.py) and `generate_societies` in [societies.py](../src/rnw/societies.py) establish layer ownership and named seed derivation. New features must not consume draws from the existing sequential native-society stream.
- [V-EXEC inspection] [ADR 0010](adr/0010-layered-worlds-and-a-generator-of-its-own.md), sections A and G, defines rerolls and reproducibility; names are not a separate layer. Any changed non-metadata output needs a new epoch and reference digest.
- [V-EXEC inspection] `check_no_game_files` in [packaging/hub.py](../packaging/hub.py): the hub mod carries no game files.
- [UNKNOWN runtime] Structural checks do not establish campaign accessibility. Agent game launches remain prohibited ([AGENTS.md](../AGENTS.md)); game checks are experiments the agent prepares and installs and the owner runs.

## Content model and vanilla adaptation

### Semantic opportunities

Before serialization, build a compact content model: stable IDs, role types, eligible locations and connected areas, cultural and religious associations, prerequisites, incompatibilities, identity keys, story families and consolidation goals. Compute it from existing graphs, fields, population and societies, without another full-raster pass.

An area may have several traits but does not receive every narrative role. There is no mandatory Aztec, Inca or Cahokia slot. No eligible bearer is a valid result, recorded with its reason. A selected role that misses a mandatory requirement is an export error. Never substitute an arbitrary country or repair a written mod in another pass.

### One decision for every vanilla consumer

Every consumer of an American tag, location, province, area, region or subcontinent key in the remap roots (`in_game/common`, `in_game/events`, `main_menu/common`) gets exactly one decision, recorded by vanilla ID in a committed table that holds identifiers only, no vanilla text. A consumer without a decision stops the export; a patch that adds consumers fails loudly until they are decided.

| Decision | When | Examples |
| --- | --- | --- |
| Keep | A general system, or a mechanic whose positional binding is acceptable | Diseases, Columbian exchange, colonial revolution, regional advances (R7b) |
| Rebind | A transferable mechanic gated by a tag or key, with generic text, or a historical formable whose vanilla culture lives in the generated world | A culture-gated formable bound to the territory that culture holds; candidates found by N0 |
| Neutralize | A literal historical identity on random land | The eight American scripted country names; formables gated only by positional region keys; a named ruler's chain |
| Replace | The gameplay purpose of a neutralized or retired item is worth keeping; original content carries it | River-city decline → River centre; Tenochtitlan's temple → a building of the Sacred centre |

R6 reuses vanilla American cultures by homeland, so a historical formable can stay meaningful when bound to its culture rather than to a region key; one bound only to positional keys cannot. The default for a tag-gated historical chain is to reuse its payload (modifiers, buildings, privileges, variables) from original events, not to rewrite its text: vanilla text names historical actors, and rewritten text would be new content anyway. Event count is not the measure of quality, and 58 direct replacements are not promised.

Adapt religious buildings and privileges only for suitable religions and political roles. Keep vanilla properties and costs where they fit, give them neutral original identities, and give each unlock a reachable path and a political cost. A generic empire does not inherit Tenochtitlan's temple.

Replace the historical natural-resource exceptions with rare suitable generated places: a major silver vein, a mercury deposit, a rich fishery. Their position follows generated geography and resources, not Potosí's former coordinates. Calibrate against installed vanilla local bonuses; no country gets a flat superpower modifier for its archetype.

### Region keys chosen by content (option N5)

The R7b design left "region keys chosen by content" out of scope ([R7 handoff](handoff/sonnet-r7-technology-and-empires.md)): region keys carry advances, units, unique buildings, country names, situations and colonial content, and the hierarchy places them at the vanilla positions. If chosen, the land layer gives each vanilla region and area key to the generated part most like its vanilla counterpart within the same subcontinent (climate, relief, coast, size), measured from the installed game's templates. Every *keep* consumer then becomes semantic at once, and R7b's families follow content instead of position. Costs: a land-layer change for every world (new epoch), a matching problem in `hierarchy`/`eu5_newworld`, and literal identities become more plausible doubles, so N1's neutralization stays mandatory. Decide after N0 has counted the positional mechanics.

## Where the content lives

- Story scripts and original localization are committed templates, copied unchanged into every world mod. The world-specific part is bindings only: start-state variables and flags on generated countries and locations, scripted triggers listing eligible locations, formable declarations, scripted country names and identity keys. Event text reads names through data functions such as `[ROOT.GetCountry.GetName]`, as vanilla's own fallback does (C176), rather than generated prose.
- The hub mod carries no game files and stays so. A world mod is self-contained: a generator update never changes a campaign already running, and a story fix reaches new worlds through a new epoch.
- **Languages (owner, 2026-10-23).** The mod and the generator use exactly the game's official languages, everywhere. The export takes them from the installed game (the languages it ships localization for), not from a fixed tuple, and writes every key in each. Authored text is written in English for now; until it is translated, the other languages carry the English text, so no raw key shows. Before 1.0.0 everything a player sees is translated into every official language ([roadmap](roadmap.md) L1): each translation records the hash of the English text it was made from, and the release check fails on a missing language or a stale translation.

## New local and colonial stories

The complete catalogue is eight families of three to five nodes, alternative branches included. This is an authoring budget, not a number of events per seed or campaign. The pilot (N3) builds the two marked families first.

| Family | Eligibility | Decision and consequence |
| --- | --- | --- |
| River centre (pilot) | Dense population, a river and an important settlement | Fund water and storage, extract more revenue or grant autonomy; economic and political consequences |
| Sacred centre (pilot) | Religious presence and a suitable holy site | Patronage, centralization or priestly privileges; tension with secular power and other faiths |
| Harvest and food supply | Suitable agriculture and actual food shortage or dependence | Trade, relief or changed obligations; expenditure against unrest and resilience |
| Route and market | Several populated centres with a real connection | Roads or trade agreements, tolls or elite concessions; upkeep and market access |
| Great alliance | Neighbouring societies with shared interests or an external threat | A council, submission or continued independence; relations and a path to consolidation |
| Empire and periphery | Distant or diverse holdings and actual subjects | Integration, concessions or coercion; control and loyalty without a predetermined collapse |
| Contact across the ocean | Actual contact with an outside power | Intermediaries, restrictions or defence; responses to the actual partner |
| Colony becomes a country | A developed colony, local interests and a metropolitan relationship | Representation, mixed identity or self-government; complements vanilla independence |

The pilot pair closes the two largest losses of G2 (CHK's river city, the AZT and CSU religious rewards), and both bearers can be conquered mid-chain, which tests ownership transitions early.

Events inspect the current owner and present conditions, not an immutable 1337 tag. When a participant is conquered or disappears, the chain is explicitly ended, suspended or transferred; an outcome never reaches an obsolete owner.

Initial pacing to test: at most two active original chains per country, at most one new chain start per country per year, and at least ten years between repeats of a repeatable family. Follow-ups and emergency consequences are counted separately. These are tuning values, not verified balance. Avoid synchronized starts in 1337 and any assumption of a fixed year of European arrival.

Choices need actual costs, different beneficiaries and lasting consequences. AI weighs affordability, war, relations and utility; unavailable options are not offered. Variables are namespaced and their lifecycle documented. Economic shocks use supported game effects, not simulations of weather or moving rivers the game does not support.

## Country identities

### Native countries

The generated name of a tag is its stable identity; its adjective stays equal to it, as in vanilla (C177). Titles follow government, rank and subject type through vanilla (above). A capital move, a new ruler or an occupation renames nothing. A real change of identity is a formable (below), not a chain of cosmetic renames. Names come from the existing language corpora; do not name every country after its capital, restore historical American names by coordinates, or present invented text as a word of a real language.

### Colonial countries

The vanilla mechanism is `scripted_country_names` (C180). N1 neutralizes its eight American entries on generated land; colonies then take the engine's default name [UNKNOWN which; INFERRED from premises: reused area and region keys carry generated display names, so a default built from them reads generated geography]. N4 writes a finite world-specific catalogue in the same format: per generated area or region and colonizer language, a local root, a river or port identity, or a metropolitan naming tradition, selected by the founder and the place of foundation.

Whether a scripted name is re-evaluated after a capital move, an overlord change or independence, and whether it overrides a player's manual name, are N2's questions, not established engine behaviour. If the engine re-evaluates on a capital move, the catalogue keys on the founding area rather than the capital, through a variable set at foundation. A transition the engine does not support stays blocked rather than imitated by a static name.

Visibility is part of the design: a selected name, a potential formable and its requirements appear only when the game exposes that country or territory. This does not promise protection against a player reading local mod files.

## New formable countries

Choose opportunities from the generated world. Export a finite set of identities and requirements before the campaign; participants and progress change during play. A possibility is not an instruction that the AI must form the country.

| Family | Foundation | Distinct political path |
| --- | --- | --- |
| River-basin union (pilot) | Connected river areas and several populated centres | Economic integration and administration of a connected territory |
| Highland confederation | Connected inhabited valleys in a mountain region | Unity with real local autonomy; not a set of unrelated highland cells |
| Maritime league | Populated coasts or islands with a valid sea connection | Several ports and actual maritime capability |
| Cultural union | Related local societies with substantial population | Several centres and cultural inclusion; tiny diaspora pops give no eligibility |
| Regional realm | A large connected region with several centres | Control and integration beyond taking one settlement |
| Postcolonial federation | Related former colonial territories | Independence, consolidation and a new identity |

Relatedness uses vanilla culture groups and languages or a recorded political association among generated societies; the plan invents no cultural-family data. Substantial presence means the main population of suitable locations.

A target follows the vanilla formable-only pattern of `ADU` (C175): the formable entry, a flag definition or coat of arms, a named colour and name and adjective keys, with no country definition and no country in 1337. The generator already writes flags and coats of arms for its native tags. Formables get their own adjective where the name is a political formula (*Kalumet Union* → *Kalumet*); the language rule is a template per official language, not an inflection algorithm. The remaining risk, that a tag first seen in a mod behaves like `ADU`, is N2's question; a rejected branch stays blocked, and ghost starting countries are no workaround.

Support diplomatic or subject-based and direct territorial consolidation where installed mechanics permit; not every union is a full-annexation checklist. Required territory comes from generated connected areas at the scale of that world. Consequences use suitable ranks, reforms, obligations and relationships with checked prerequisites, not one permanent bonus for every formable. Prevent formation cycles and repeated rewards; keep potential visibility, progress and formation eligibility distinct. Historical formables that N0 keeps or rebinds stay beside the new ones without becoming the obligatory best continuation of every society.

## More varied societies (R7d)

Four more combinations of real traits (a maritime trade network, a highland confederation, a fragmented region with several centres, a sacred centre with political competitors) belong to the peoples layer as a continuation of R7, not to the content stages; like them, R7d is part of 1.0.0. An archetype follows geography and social structure; randomness chooses among suitable combinations. Strength comes from population, infrastructure, trade and organization; weakness from connection costs, autonomy, relationships and diversity. Neither collapse nor a giant empire is guaranteed, and not every combination needs a new government type. Stories and formables read traits (river, coast, holy site, subjects), not archetype labels, so N3 and N4 do not wait for R7d.

## Randomness and layer ownership

- Story opportunities, formables and colonial name catalogues use independent named streams in the peoples layer, keyed by stable object IDs. They add no draws to the current native-society stream, and adding one family does not reshuffle the others.
- Exceptional resource places belong to the resources layer and depend on land and resources, not peoples. Rerolling peoples does not move a deposit; rerolling resources changes no country or name. Resource-related events inspect the actual resource in play; any further resource-owned output is explicit in the layer comparison allowlist.
- Region keys chosen by content (N5) would belong to the land layer.
- Definitions and opportunities reproduce from the world code, epoch and input manifest. Campaign outcomes use the game's random state; a world code does not promise an identical campaign.
- New content does not migrate into existing saves. Each stage that changes mod output raises the product version, starts a new epoch and updates the reference world; a released epoch's digest is never rewritten.

## Scope and constraints

Use the existing stack, delivery model, settings and rare-empire control. No new public controls, story reroll layer, paid service or dependency. Original prose and templates belong in the project; vanilla-derived output is generated locally from the player's installation.

Excluded: mandatory historical doubles, fixed old capitals as hidden anchors, duplicate disease, independence or trade systems, flat archetype bonuses, post-export repair layers, silent substitutions, a new history engine, an LLM in the generator, a replacement religion system, a name-inflection engine. Preserve the Old World and existing profiles and saves. Push and publication are outside this plan.

## Staged plan

Every stage, R7d included, is part of 1.0.0 (owner, 2026-10-23); nothing in this plan is deferred past it. Owner types as in the [roadmap](roadmap.md). Each stage includes its tests. A stage that changes output raises the version, starts an epoch, renews the reference world and installs a verified candidate in a new recorded `rnw_exp_*` folder. Game checks are experiments the agent prepares and the owner runs; until run they are NOT-RUN. Proposed paths do not imply that the files exist.

- [x] **N0. Inventory and decisions** — Opus design; offline, no output change. Done 2026-10-23.
  - `rnw content-inventory GAME_DIR OUT` writes local JSON of every consumer: category, vanilla ID, files, the keys it names by kind (tag, location, province, area, region, subcontinent, and `state` for a variable only a retired object sets) and its decision. The committed table is `content_decisions.py` (identifiers only; rows plus two rules: a definition keyed by a retired tag is inert, an object the exporter retires is neutralized or, where a later stage carries its purpose, replaced). The export calls `content_check.check_decisions` after the script remap: a consumer without a decision stops it. Code: `content_inventory.py` (scan), `content_decisions.py`, `content_report.py`, `content_check.py`.
  - Acceptance: the 58 events, 39 modifiers, five natural bonuses, eight scripted names, the American formables and the region and area consumers of C179 all have a decision; the positional mechanics are counted for N5.
  - QA: `tests/test_content_inventory.py` with synthetic chains (a shared retained event, an adapted dependent event, a privilege whose path was retired, an unclassified object that stops the check, a script word that is also a location); `test_local_content_consumers_all_have_a_decision` reports drift after a patch, both ways. The reference world of epoch 11 came out byte for byte the same with the check in the export.
  - Commit: `Inventory the New World's vanilla content consumers and decide each`.

  **Result** (EU5 1.4.3 build 26105915, C181–C185). 634 consumers: 243 coats of arms keyed by a retired tag and 391 other script objects (186 events, 43 advances, 30 customizable localizations, 18 holy sites, 12 area preferences, 8 scripted country names, 8 formables, 44 retired modifiers and base values, and 42 in smaller categories). Decisions: **keep 391**, **rebind 6**, **neutralize 84**, **replace 153**.

  | Decision | Count | Why |
  | --- | --- | --- |
  | keep, inert | 264 | 243 coats of arms of retired tags and 21 objects gated by them (the Russian case forms of C176, `country_flavor` exceptions) |
  | keep, positional | 68 | Follow a vanilla region or area key by position: the regional advances of R7b, AI area preferences, goods filters, situations, 9 Old World events about the Caribbean, Brazil and the colonies |
  | keep, generic | 39 | Earthquakes, expeditions, pirates, a Dutch city on `manhattan`: the remap keeps them working |
  | keep, homeland | 18 | The holy sites that the natives pass places in the religion's most populated locations |
  | keep, name | 2 | Not references: given names equal to location keys |
  | rebind, culture | 6 | `AZT_f`, `INC_f`, `IRO_f`, `MAY_f`, `PUE_f` (gated by a culture or religion the world reuses) and the Huitzilopochtli start effect of `on_game_start`: N1 |
  | neutralize | 84 | 49 events naming American people, places, companies or incidents and 3 inert helpers; 23 inert unique advances of retired states; 2 other inert objects; the Panama canal chain (7: advance, three decisions, footprint, map object, achievement) |
  | replace | 153 | The 58 retired events and 44 retired modifiers and base values (by chain: CHK, AZT, CSU to N3; IRO, PUE to N4; the five natural bonuses to N1), the temple of Tenochtitlan and the privilege whose variable only a retired event set (N3), the eight scripted names and `USA_f`, `CAN_f`, `MEX_f` (N4), the silver chain (N1) and the colonial rebellion chain (N4) |

  By stage: N1 carries 6 rebindings and 9 replacements, N3 76 replacements, N4 68. Two objects from G2 appear only through analysis: `flavor_chk.32` (a plain event whose trigger names a retired tag, not a dynamic one) and `hurin_qusqu_privilege` (reads a variable that only retired events set). **For N5:** the 68 positional consumers stand in 27 files and name all 14 American regions, 53 of the 154 areas, 43 locations and both subcontinents; every region key is thus load-bearing, and the case for N5 rests on whether those 68 read sensibly on random land. The decisions about events are judgements by the text and the gating, not by a count; the rule used: an event that names a historical American person, place, company, work or incident is neutralized, one that speaks only of roles, goods and regions stays.
- [ ] **N1. Correct the current output** — Sonnet implementable after N0; first game-facing candidate.
  - [x] The official languages from the installation (G6), Turkish thereby included, need no inventory and went first: 0.10.2, epoch 12, C186.
  - [x] Neutralize and rebind per N0 (0.10.3, epoch 13, C187–C188), by `eu5_content.py`: an object whose decision is to neutralize *an identity* (101 objects: 82 events, 8 scripted country names, 3 colonial formables, the Panama canal's advance and three decisions, the pilgrimage to Cholula) has the gate vanilla gives it closed with `always = no` (the `trigger` of an event, the `potential` of a decision, advance, formable or generic action, the `country_trigger` of a name), so it stays in its file, no reference to it dangles (28 of the events stand in on-action pulse lists) and nothing can fire, offer or apply it. Five culture-gated formables take as territory the generated places where their culture dominates, as many as the vanilla territory had (`AZT_f`, `INC_f`, `IRO_f`, `MAY_f`, `PUE_f`); a culture too thin to hold three places, or a third of the vanilla size, closes the formable instead; the Huitzilopochtli start effect of `on_game_start` finds the seat of the Nahuatl religion or can never hold. The retired chains stay retired (N0's rule) and are **losses until their stage**: the Cahokia river-city chain (22 events, 22 modifiers), the Aztec and Inca chains, the temple of Tenochtitlan and the Hurin Qusqu privilege, the pilgrimage to Cholula (N3); the Haudenosaunee and Pueblo chains, the colonial names, the road to independence, `USA_f`, `CAN_f` and `MEX_f` (N4); the silver chain and the five natural bonuses (N1's exceptional places).
  - [x] Exceptional resource places in the resources layer (G5), 0.10.4, epoch 14, C189–C190, by `eu5_places.py`: five kinds, each with a static modifier of the mod's own (`rnw_great_silver_lode`, `rnw_rich_silver_vein`, `rnw_silver_seam`, `rnw_mercury_lode`, `rnw_rich_fishery`) that carries the size of the vanilla bonus it replaces (2.5, 1.5, 1, 2.5 and 2, read from the installation at generation time) under original names; a place stands on a generated cell with the right material (silver preferably in mountains, a fishery on a coast), chosen by a stream of its own from the resources seed, so adding a kind moves no other. A world without a suitable cell has no such place.
  - QA: synthetic scripted names and formables neutralized or rebound by decision; rerolling peoples leaves the deposits, rerolling resources the countries; Old World unchanged; an unclassified consumer stops the export.
  - Owner experiment: no new `error.log` lines (read by the agent); an exceptional place shows its bonus (`goto`, row 9 of the [console sitting 036](../experiments/036-console-session/README.md)). A colony's name and a culture's formable need play and wait for N4 and L1.
  - Commit: `Neutralize positional historical identities and add exceptional places`.
- [x] **N2. Hook experiment** — prepared by the agent, run by the owner; may share a session with N1's. Prepared and installed 2026-10-23: [experiment 034](../experiments/034-content-hooks-n2/README.md), probe `rnw_exp_probe_hooks` (`eu5_probe.py`, `rnw probe-hooks`); **the run itself is NOT-RUN** (rows 1 to 5 of the [console sitting 036](../experiments/036-console-session/README.md)), so every branch of N3 and N4 that leans on a hook stays [UNKNOWN] until the owner has run it.
  - Questions, each with its vanilla precedent: a mod-generated formable tag (`ADU`, C175); a world-specific scripted country name after a capital move, an overlord change, independence and a manual rename (C180); start-state variables (EU5 keeps state in variables, with no flag effects, C191) after save and load; the Russian fallback with a generated tag (C176); vanilla titles with a generated tag.
  - Offline acceptance: valid syntax, verified anchors and a complete experiment record. An absent anchor fails; a skipped local test is not a pass. A branch whose hook fails stays blocked.
  - **First run (owner, 2026-10-23, EU5 1.4.4, C199-C201, [036](../experiments/036-console-session/README.md) Result):** H1 holds (the formable of a mod-defined tag, with its flag, colour and names), H7 holds (a dynamic start with a variable and a delayed event), H6 holds as far as the mod's hook fires (a sub-on-action listed in `on_actions`). H3 is answered the other way round: a mod's `on_game_start` `effect` *replaces* the game's, so a start hook is an `on_actions` entry (the game's own `ai_personalities_setup.txt` does it); **in 037 that hook ran beside the game's start, with variables set on a country and a location (C206)**. The keys the game looks up for decisions and formables were wrong in the probe and the unions (C201). H2 (the colony's scripted name): a plain `vassal` made from a location keeps the location's name two game years on (C207), so the name needs another path; the probe now founds a `colonial_nation` ([038](../experiments/038-lobby-list-and-colony/README.md)). Open: the Russian forms (H4) and the titles (H5).
  - Commit: `Add content hook probes and their experiment`.
- [x] **N3. Content model and river pilot** — Opus design, then Sonnet. Implemented offline 2026-10-23 (0.10.5, epoch 15, C193–C196); **the owner's run is NOT-RUN**.
  - `src/rnw/content.py` (the model: facts, eligibility, absence reasons, incompatibilities, independent streams), `src/rnw/stories.py` (the static story templates and their graphs), `src/rnw/eu5_story.py` (the world's files: start events, payload copies, unions, texts), integrated in `eu5_nw_export.py` after the natives, before the texts are verified. The model reads the finished world and draws from streams of its own derived from the peoples seed, so it changes no existing draw and no full-raster scan is made.
  - **Design.** A story is a short graph of events about one place and the state that holds it; the templates carry no tag and no location. What a world adds is one *hidden start event* per bearer: a `dynamic_historical_event` bound to the bearer's tag (the proven vanilla mechanism, with a window of 45 years drawn from 1340 to 1397 and a monthly chance of 2 to 5 per cent) that, if the bearer still owns the centre, stores the centre in a variable (`rnw_river_centre`), fires node 1 and schedules a hidden cleanup 15 years on. The chain events read `var:rnw_river_centre`, check that the owner is still the receiver, and go forward by delayed `trigger_event_non_silently`; each ending removes the story's variables. So a conquered bearer's pending events die with its scope, an event aimed at a state that no longer owns the centre cannot fire, and a story cut short is cleaned by its own timer. No hook beyond what vanilla already does is needed (not the start variables of H3, not the yearly pulse of H6).
  - **Pilot families.** *River centre* (4 nodes, 6 endings, 7 modifiers): a populous state centre on a river that the river turns against; embankments and canals, tolls and neglect, or guilds that keep the banks, each with its price and later consequence; replaces the Cahokia chain. *Sacred centre* (4 nodes, 6 endings, 2 modifiers and an estate privilege): a holy place held by a state of its own faith; an endowment, a tithe or a seat for the high priest; replaces the temple of Tenochtitlan, the Hurin Qusqu privilege and the pilgrimage (the temple's effect becomes a location modifier, not a building). Every modifier copies the payload of a vanilla source (`chk_*` static modifiers, the temple building's `modifier`, the privilege's `country_modifier`) at generation time under a name and text of the mod's own; a source that is gone stops the export. *River-basin union*: a formable of a tag the game does not define (the `ADU` pattern, C175) over up to 30 connected river places that hold at least three centres and the capitals of two states or more, offered to those states (at most 8); it depends on H1.
  - **Rules kept.** A family with no bearer is a recorded result, not an error (`absences` in the report), and writes no event (it would be orphaned). A place is the centre of one story; a state bears at most two chains, begins at most one story a year, and the plan reproduces from the peoples seed alone whatever the order of its inputs. In the reference world: 4 river centres, 2 sacred centres and 2 unions.
  - QA: `tests/test_content.py` (river chain, island, highland; disconnected, single-state and foreign-faith failures; iteration-order invariance; non-interference when a family is added; unions connected and limited; one start a year), `tests/test_stories.py` (every node reached, every path ended and its variables removed, each branch leads to the node whose trigger asks for the value it set, nothing offered that cannot be paid for, no loop, all texts present, no tag and no location in a template) and `tests/test_story_files.py` (start events, payload copies, category clashes, missing sources, unions, texts in every language); the local reference test asserts each family is offered, and `RNW_LAYERS=1` shows that rerolling the peoples changes the stories and rerolling the resources leaves them. A transition model is not proof of in-game effects.
  - Owner experiment: [035](../experiments/035-new-world-content-n3/README.md), run as rows 6 to 8 of the [console sitting 036](../experiments/036-console-session/README.md): a pilot chain fired with the console (`event rnw_story.1001`) to an outcome, the union on the formables list. A forced event tests its effects, not its natural frequency; the natural start is tested in miniature by the probe (a certain dynamic window in the first year, H7). A conquered bearer's chain and a save mid-chain are covered offline.
  - Commit: `Generate content roles and the river pilot`.
- [ ] **N4. Expansion** — Sonnet implementable after N3.
  - The remaining six story families and five formable families, one family or a small group per version; world-specific colonial names once N2 has answered; the postcolonial federation after them.
  - QA per family as in N3, plus a structural eligibility witness per formable family and rejection of disconnected targets, diaspora-only eligibility, invalid rank, repeated formation and key or tag conflicts; visibility of undiscovered goals.
- [ ] **N5. Region keys chosen by content** (option; owner decision after N0) — Opus design.
  - Assign vanilla region and area keys by similarity within their subcontinent; R7b's families then follow content. Gate: the counted positional mechanics read sensibly on three worlds; Old World unchanged; a new epoch.

Shared exporter, key registry and content-model edits have one owner at a time.

Acceptance across stages: `uv sync --locked --group dev && make check`, then the exact local tests with `EU5_GAME_DIR`; `RNW_REPRODUCE=1` reference generation for each new epoch. Compare Old World files, peoples and resources rerolls, references, tags, flags, localization, input manifests, digests and epochs; for files holding several layers compare owned fields rather than demand whole-file identity. Evidence goes to `local_data/content/`; commit conclusions, not derived logs. Keep OFFLINE-PASS, NOT-RUN and V-GAME apart; a successful start does not validate a long campaign.

## Assessing interest

| Dimension | Evidence to seek | Insufficient evidence |
| --- | --- | --- |
| Accessibility | A suitable bearer, attainable prerequisites and a working outcome | A file or button exists |
| Variety | Different worlds produce different goals, societies and development paths | Different names and colours |
| Choice | Costs and beneficiaries vary with circumstances; alternatives make sense | A free best option |
| Discovery | Contact, ownership or knowledge reveals opportunities | Hidden realms and goals visible before exploration |
| Dynamics | Conquest, capital moves, independence and save/load preserve causality | It worked once at start |
| Balance | Advantages and costs use normal mechanics and AI decisions | An archetype label grants power |

The criterion is whether players on different seeds can describe different decisions they had to make. Event counts and invented percentages of vanilla interest are no substitute.

## Final verification

- [ ] F1. Reconcile the inventory with every keep, rebind, neutralization and replacement; nothing disappears silently.
- [ ] F2. Review code quality, determinism, layer ownership and Old World preservation from completed checks only.
- [ ] F3. Run the owner's experiments of N1–N4; until run, the runtime result is NOT-RUN, not PASS.
- [ ] F4. Map G1–G7 to evidence from two materially different campaigns, with limits stated.

## Decisions

Settled by the owner (2026-10-23): the mod and the generator use the game's official languages everywhere; authored text stays English until the full localization before release (L1); the whole plan, R7d included, is part of 1.0.0, the complete product of [ADR 0003](adr/0003-versioning.md).

Open: **region keys by content (N5)**, whether, not when. Recommendation: decide after N0; if positional mechanics are many, N5 is the one change that makes them semantic with vanilla data.

Settled by this plan: a plausible random world by default; historical formables kept only where N0 keeps or rebinds them; player-chosen names preserved; no additional settings. Engine uncertainties belong to N2, not to the design.
