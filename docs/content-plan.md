# Random-first New World content: proposed design and implementation plan

**Status:** Proposed, 2026-10-23. No implementation or game launch is authorized by this document.
**Baseline:** Generator 0.10.1; EU5 1.4.3 open beta, Steam build 26105915.
**Evidence:** Existing behavior is labeled below. Every proposed behavior is [INFERRED design]; its acceptance by the running game is [UNKNOWN] until observed separately.

## Design direction

Generate geography and societies first. Identify meaningful opportunities within that world: a crowded river city, a maritime network, a fragmented cultural region, a sacred center, an exceptional deposit, or a large state with a difficult periphery. Those opportunities supply appropriate stories and political goals without prescribing their outcome.

Vanilla supplies the mechanics: religions, buildings, technology, governments, estates, trade, colonization, and established scripting patterns. The generator supplies suitable places, participants, identities, and combinations of conditions. Players and AI determine what happens during the campaign.

Randomness governs the world's structure and available opportunities. Causal eligibility governs who receives them. Random event timing cannot substitute for either. A seed must not be rerolled until it contains a preferred historical analogue.

This plan covers both native and colonial play. Its deliverables are adapted vanilla opportunities, new local stories, dynamic native and colonial identities, new formable countries, exceptional economic places, and more varied societies. The work is architectural and spans several verified stages; no calendar estimate is assigned.

## Desired experience and current gaps

| ID | Desired experience | Current gap | Tasks |
| --- | --- | --- | --- |
| IS-1 | Content follows generated geography and societies; the same world code remains reproducible | GAP-1: reference remapping usually chooses a nearby compatible location, not a semantic role | 1, 3, 4, 10 |
| IS-2 | A vanilla opportunity remains accessible, has a meaningful replacement, or has an explicit reason for absence | GAP-2: 58 events are retired; some retained buildings and privileges lose their unlock path | 1, 2, 4, 10 |
| IS-3 | A native campaign offers consequential decisions and long-term goals | GAP-3: the generator does not emit original event chains | 5, 8, 9, 10 |
| IS-4 | Native and colonial names express a stable identity and meaningful historical changes | GAP-4: generated base names exist, but the identity lifecycle is not designed | 2, 6, 7, 10 |
| IS-5 | Regional consolidation offers different, intelligible political paths | GAP-5: historical formables are remapped; procedural formables do not exist | 2, 8, 10 |
| IS-6 | Wealth and social structure create different strategic problems | GAP-6: exceptional historical resource places disappear; large-society patterns are limited | 3, 4, 9, 10 |
| IS-7 | Old World preservation, independent world layers, and concealed geography remain intact | GAP-7: new triggers, names, and goals could violate those contracts without explicit checks | 2, 3, 6, 7, 8, 10 |

## Evidence and implementation anchors

Project paths are relative to the repository. Installed-game paths below are relative to `game/` within the installation; derived game text remains local.

- [V-EXEC inspection] [eu5_events.py](../src/rnw/eu5_events.py), `retire_events`, removes events of retired tags and follow-ups referenced only by those events. [eu5_remap.py](../src/rnw/eu5_remap.py), `build_remap`, maps removed locations to nearby compatible generated cells. Neither proves semantic accessibility.
- [V-LOCAL EU5 1.4.3 / V-EXEC 0.10.1 audit] World 6DIV retires 58 events: AZT 16, CHK 22, CSU 7, IRO 7, PUE 6. It retires 39 related modifiers and five historical natural-resource bonuses. Its event overrides introduce no new event IDs. See [native societies](natives.md) and `retired_base_modifiers` in [eu5_nw_export.py](../src/rnw/eu5_nw_export.py).
- [V-LOCAL EU5 1.4.3] `in_game/common/building_types/event_only_buildings.txt`, `great_temple_of_tenochtitlan`, requires `has_or_had_tag = TNC` and an unlock. `estate_privileges/clergy_estate.txt`, `hurin_qusqu_privilege`, requires a variable set by a retired CSU event. Keeping their definitions does not preserve their access paths.
- [V-LOCAL EU5 1.4.3] `scripted_country_names/00_default.txt` supplies country/capital/location predicates. `scripted_effects/country_effects.txt`, `change_tag_cosmetic`, uses separate name and adjective effects. Conflicting-name precedence and preservation of manual names remain [UNKNOWN runtime].
- [V-LOCAL EU5 1.4.3] `formable_countries/readme.txt` documents levels, territorial fractions, potential/allow conditions, names, adjectives, tags, flags, and formation effects. Acceptance of generated target tags and flags without creating a country in 1337 remains [UNKNOWN runtime].
- [V-EXEC inspection] [eu5_natives.py](../src/rnw/eu5_natives.py), `new_tags`, `country_definitions`, and `country_names`, generates native identities; the current adjective equals the country name. [loc_keys.py](../src/rnw/loc_keys.py) reserves localization hashes.
- [V-EXEC inspection] [layers.py](../src/rnw/layers.py), [rng.py](../src/rnw/rng.py), and `generate_societies` in [societies.py](../src/rnw/societies.py) establish layer ownership and named seed derivation. New features must not consume additional draws from the existing sequential native-society stream.
- [V-EXEC inspection] [ADR 0010](adr/0010-layered-worlds-and-a-generator-of-its-own.md), sections A and G, defines rerolls and reproducibility. Names are not a separate rerollable layer. Any changed non-metadata mod output requires a new algorithm epoch and reference digest; the baseline epoch is 11.
- [UNKNOWN runtime] Structural checks do not establish campaign accessibility. [AGENTS.md](../AGENTS.md) prohibits agent game launches in the current session. Future running-game checks need separate authorization and remain NOT-RUN until performed.

## Content model and vanilla adaptation

### Semantic opportunities

Before serialization, build a compact content model with stable IDs, role types, eligible locations and connected areas, cultural/religious associations, prerequisites, incompatibilities, identity keys, story families, and consolidation goals. Compute it from existing graphs, fields, population, and societies, without another full-raster pass.

An area may have several traits, but should not receive every narrative role. There is no mandatory Aztec, Inca, or Cahokia slot. No eligible role is a valid result recorded with its reason. A selected role missing one of its mandatory requirements is an export error. Never substitute an arbitrary country or repair an already-written mod in another pass.

### Three treatments of vanilla content

| Class | Treatment | Examples |
| --- | --- | --- |
| General systems | Preserve and verify their references and conditions; do not duplicate them | Diseases, Columbian exchange, colonial revolution, general colonization |
| Transferable gameplay role | Bind to a suitable generated society; replace literal historical actors, dates, and place identities | River-city decline, religious reform, irrigation, tribal consolidation |
| Irreducibly historical narrative | Do not transplant literally; record the loss and, where useful, replace its gameplay purpose | A named ruler's rise or a particular dynasty's intrigue |

Inventory all 58 retired events: original ID, original gameplay purpose, keep/adapt/retire decision, replacement or justified omission, dependent unlocks/variables/modifiers, and verification. Do not promise 58 direct replacements or treat event count as the measure of quality.

Adapt religious buildings and privileges only for appropriate religions and political roles. Preserve vanilla properties and costs where suitable, use neutral original identities, and give each unlock a reachable path and political cost. A generic empire does not automatically inherit Tenochtitlan's temple.

Replace historical natural-resource exceptions with rare suitable generated places: a major silver vein, a mercury deposit, or a rich fishery. Their position follows generated geography and resources, not Potosi's former coordinates. Calibrate output against installed vanilla local bonuses; do not award a country a flat superpower modifier for its archetype.

## New local and colonial stories

The initial complete authored catalogue comprises eight families of three to five nodes, including alternative branches. This is an authoring budget, not a guaranteed number of events per seed or campaign.

| Family | Eligibility | Decision and consequence |
| --- | --- | --- |
| River center | Dense population, a river, and an important settlement | Fund water/storage, extract more revenue, or grant autonomy; economic and political consequences |
| Harvest and food supply | Appropriate agriculture and actual food shortage or dependence | Trade, relief, or changed obligations; expenditure versus unrest and resilience |
| Route and market | Several populated centers with a real connection | Roads or trade agreements, tolls, or elite concessions; maintenance costs and market access |
| Sacred center | Religious presence and a suitable holy site | Patronage, centralization, or priestly privileges; tension with secular power and other faiths |
| Great alliance | Suitable neighboring societies with shared interests or an external threat | A council, submission, or continued independence; relations and a path to consolidation |
| Empire and periphery | Distant or diverse holdings and actual subjects | Integration, concessions, or coercion; control and loyalty without a predetermined collapse |
| Contact across the ocean | Actual contact with an outside power | Intermediaries, restrictions, or defense; responses to the actual partner |
| Colony becomes a country | A developed colony, local interests, and a metropolitan relationship | Representation, mixed identity, or self-government; complement vanilla independence |

Events inspect the current owner and present conditions, not an immutable 1337 tag. On conquest or disappearance of a participant, explicitly terminate, suspend, or transfer the relevant chain. Never deliver an outcome to an obsolete owner.

Initial pacing values to test: at most two active original chains per country, at most one new chain start per year, and at least ten years between repeats of a repeatable family. Follow-ups and emergency consequences are handled separately. These are proposed tuning values, not verified balance results. Avoid synchronized starts in 1337 and fixed-year European discovery.

Choices need actual costs, different beneficiaries, and lasting consequences. AI evaluates affordability, war, relations, and utility; unavailable options are not offered. Namespace variables and document their lifecycle. Use supported game effects for economic shocks rather than pretending to simulate unsupported weather or moving rivers.

## Dynamic country identities

### Native countries

Separate a stable identity root from political form. Give each country its own name, separate adjective, and a small number of meaningful transitions: tribe/city to union/state, or colony to independent country. A capital move, new ruler, or temporary occupation must not automatically replace its root identity.

Use existing language corpora and name generation for roots, with original localized political formulas. Do not name every country after its capital, restore historical American names by coordinates, or present invented text as an authentic word of a real language.

Cosmetic name changes do not change the tag, diplomatic identity, color, or flag. Actual formation of another country is a separate mechanic. Name and adjective forms require separate localization and checks in Russian and every supported language; adding an arbitrary suffix is not a general inflection algorithm.

### Colonial countries

Generate a finite catalogue of territorial and colonizer-language naming variants at export time: a local root, an exonym, a river/port identity, or a metropolitan/personal naming tradition. Selection follows the actual founder and place of foundation.

The desired behavior is a persistent founding anchor and selected name. Moving the capital does not automatically select another name. Independence offers retaining the inherited identity or choosing a local one. Later substantive renaming is an explicit player/AI decision.

Founding anchors, manual-name detection, and independence naming hooks are requirements to prove in task 2, not established engine capabilities. If a supported manual-name check exists, honor it. Otherwise do not automatically rename an existing country after creation; offer explicit decisions. An unsupported transition remains blocked rather than being declared complete with a static-name substitute.

Visibility is part of the design: expose a selected name only when the game exposes that country or territory. Potential formables and requirements must not reveal unknown regions. This does not promise protection against a player reading local mod files.

## New formable countries

Choose opportunities from the generated world. Export a finite set of identities and requirements before the campaign; participants and progress change during play. A possibility is not an instruction that the AI must form the country.

| Family | Foundation | Distinct political path |
| --- | --- | --- |
| River-basin union | Connected river areas and several populated centers | Economic integration and administration of a connected territory |
| Highland confederation | Connected inhabited valleys within a mountain region | Unity with meaningful local autonomy; not a collection of unrelated highland cells |
| Maritime league | Populated coasts/islands with a valid sea connection | Multiple ports and actual maritime capabilities |
| Cultural union | Related local societies with substantial population | Several centers and cultural inclusion; tiny diaspora pops do not establish eligibility |
| Regional realm | A large connected region with several centers | Control and integration beyond taking one settlement |
| Postcolonial federation | Related former colonial territories | Independence, political consolidation, and a new identity |

Relatedness uses verified vanilla culture groups/languages or an explicitly recorded political association among generated societies. This plan does not invent new cultural-family data. Substantial presence means the main population of suitable locations, not a small diaspora entry.

Support diplomatic/subject-based and direct territorial consolidation where installed mechanics permit it. Do not make every union a full-annexation checklist if vanilla conditions can express a different political path.

Derive required territory from generated connected areas, with scale appropriate to that world. Generate names, adjectives, and symbols from the relevant identity. Consequences use suitable ranks, reforms, obligations, and relationships with checked prerequisites, rather than an identical permanent bonus for every formable.

Reserve future tags, keys, and flags separately without creating empty countries in 1337. Prevent formation cycles and repeated rewards. Distinguish potential visibility, progress, and actual formation eligibility.

Each opportunity is an export-time declaration with fixed name/adjective/tag/flag keys and generated requirements. Creating arbitrary definitions during a campaign is neither needed nor claimed. If the engine rejects a new target tag or flag, that branch remains blocked pending a demonstrated compatible solution; ghost starting countries are not an acceptable workaround.

Retain meaningful, accessible historical formables alongside new ones. They must not become the obligatory best continuation of every generated society. Overlapping paths should be intelligible choices without repeated rewards.

## More varied societies

Extend the existing large territorial state with four additional combinations of real traits: a maritime trade network, a highland confederation, a fragmented region with several centers, and a sacred center with political competitors. Not every combination needs a new government type.

An archetype follows geography and social structure; randomness chooses among suitable combinations. Strength comes from population, infrastructure, trade, and organization. Weakness comes from connection costs, autonomy, relationships, and diversity. Neither inevitable collapse nor a giant empire is guaranteed.

## Randomness and layer ownership

- Country names, political/religious roles, story opportunities, and formables use independent named streams within peoples, keyed by stable object IDs. Do not add draws to the current native-society stream or reshuffle every feature when adding one story family.
- Natural-resource exceptions belong to resources and depend on land/resources, not peoples. Rerolling peoples does not move a deposit; rerolling resources does not change countries or their names.
- Resource-related events inspect the actual resource during play. They do not reshape society generation after a resource reroll. Any additional resource-owned output is explicit in the layer comparison allowlist.
- Definitions and opportunities reproduce from the world code, algorithm epoch, and input manifest. Campaign outcomes use the game's random state; the world code does not promise an identical campaign history.
- New content does not migrate itself into existing saves. Each completed phase changing mod output raises the product version, starts a new epoch, and updates the reference world. Never rewrite a released epoch's digest.

## Scope and constraints

Use the existing stack, delivery model, settings, and rare-empire control. No new public controls, separate story reroll layer, paid service, or dependency is proposed. Original prose and templates belong in the project; vanilla-derived output is generated locally from the player's installation.

Do not add mandatory historical doubles, fixed old capitals as hidden semantic anchors, duplicate disease/independence/trade systems, flat archetype strength bonuses, post-export repair layers, silent substitutions, a new history engine, an LLM inside the generator, or a replacement religion system. Preserve the Old World and existing profiles/saves. Push and publication are outside this request.

## Implementation plan

Each task includes implementation and its tests. Proposed new paths below do not imply those files already exist. Complete verified phases receive coherent local commits. A phase changing game-facing output installs a verified candidate in a new recorded test-mod folder under the existing project rules.

- [ ] 1. Inventory content and gameplay losses
  - Recommended task executor category: unspecified-high
  - Closes GAP-1/2. Add `docs/content.md` and claims-ledger entries; inspect `eu5_events.py`, `eu5_remap.py`, `eu5_nw_export.py`, local DHE files, and modifiers.
  - Acceptance: all 58 events, 39 related modifiers, five natural exceptions, and known dependent readers have a decision and verification method. Maintain a separate preservation list for general colonial/religious systems.
  - QA: add `tests/test_content_inventory.py` with synthetic chains; run `uv run pytest -q tests/test_content_inventory.py`. Cover a shared retained event, an adapted dependent event, an inaccessible privilege, and an unclassified source ID that must fail. Local source inventory reports drift after patches. Evidence: `local_data/content/task-01.json`.
  - Depends on: none. Commit: `Document procedural content scope and source coverage`.

- [ ] 2. Prove extension points before mass authoring
  - Recommended task executor category: unspecified-high
  - Closes GAP-2/4/5/7. Inspect installed scripted names, country effects, the formables readme, and existing tag/localization checks. Prepare minimal synthetic fixtures and a bounded local experiment.
  - Offline acceptance: valid syntax, verified source anchors, and a complete experiment specification. Fixtures do not establish engine behavior.
  - Runtime acceptance, only in a separately authorized observation: name/adjective precedence and persistence; manual names; colony creation, capital/overlord changes, and independence; previously absent target tags without ghost starting countries; flags; chain state after save/load.
  - QA: add hook fixtures/local checks, then run `uv run pytest -q tests/test_content_hooks.py tests/test_local_install.py -k 'content_hooks or native_calibration'`. An absent anchor must fail; skipped local tests are not passes. Runtime tests remain NOT-RUN until performed; an unsupported branch remains blocked without a visual imitation.
  - Depends on: 1. Commit: `Add bounded content hook probes and compatibility checks`.

- [ ] 3. Generate semantic roles and independent streams
  - Recommended task executor category: unspecified-high
  - Closes GAP-1/6/7. Add `src/rnw/content.py` and `src/rnw/eu5_content.py`; integrate before serialization in `eu5_nw_export.py` using existing societies, hierarchy, rivers, layers, and RNG data.
  - Acceptance: stable role IDs, eligibility and absence reasons, incompatibilities, independent streams, and explicit output ownership. No new full-raster scan or change to existing sequential draws.
  - QA: `uv run pytest -q tests/test_content.py tests/test_layers.py tests/test_rng_noise.py`; cover river/island/highland graphs, disconnected and underpopulated failures, iteration-order invariance, and non-interference when adding a story family. Evidence: `local_data/content/task-03.json`.
  - Depends on: 1; task 2 compatibility is required before a game-facing handoff. Commit: `Generate semantic content roles from world and societies`.

- [ ] 4. Restore suitable vanilla opportunities and exceptional places
  - Recommended task executor category: unspecified-high
  - Closes GAP-1/2/6. Implement in `eu5_content.py` and new `eu5_sites.py`. Change retirement/remapping only according to the explicit inventory; do not disable retirement globally.
  - Acceptance: adapted transferable chains, reachable religious buildings/privileges, and resource exceptions. General vanilla systems remain single systems. Every adaptation has complete references and explicit applicability.
  - QA: `uv run pytest -q tests/test_content_adaptation.py tests/test_sites.py tests/test_script_rewrites.py`; reject an incompatible religion/resource, vanished owner, missing unlock, duplicate bonus, and Old World changes. Evidence: `local_data/content/task-04.json`.
  - Depends on: 2, 3. Commit: `Adapt native opportunities and generate exceptional resource sites`.

- [ ] 5. Add eight original story families
  - Recommended task executor category: unspecified-high
  - Closes GAP-3. Add `src/rnw/eu5_stories.py`, original templates/localization, and content-model inputs.
  - Acceptance: the eight specified families, branches, pacing, costs/consequences, AI choices, ownership transitions, termination, and state cleanup. Committed prose does not copy vanilla passages.
  - QA: `uv run pytest -q tests/test_stories.py`; model a path from each eligible start to every outcome and stop on lost prerequisites. Test repeated rewards, cycles, unaffordable choices, vanished scopes, and synchronized chain starts. A transition model is not proof of in-game effects. Evidence: `local_data/content/task-05.json`.
  - Depends on: 2, 3, 4. Commit: `Add causal native and colonial story families`.

- [ ] 6. Add native identity and separate adjective forms
  - Recommended task executor category: unspecified-high
  - Closes GAP-4/7. Add `src/rnw/identity.py` and `src/rnw/eu5_identity.py`; use `names.py`, `eu5_natives.py`, and `loc_keys.py`. Keep mod/world display names in `worldname.py` separate.
  - Acceptance: a stable root, separate name/adjective forms, and meaningful transitions without cosmetic tag changes or automatic destruction of manual names.
  - QA: `uv run pytest -q tests/test_identity.py tests/test_natives_eu5.py`; same-input identity, seed variation, collision rejection, unchanged roots after capital/ruler changes, and valid original templates in Russian and supported languages. Evidence: `local_data/content/task-06.json`.
  - Depends on: 2, 3. Commit: `Generate stable native identities and separate adjective forms`.

- [ ] 7. Name colonies and handle independence
  - Recommended task executor category: unspecified-high
  - Closes GAP-4/7. Extend `eu5_identity.py` through only the colony hooks proved in task 2; emit world-specific original localization.
  - Acceptance target after proving each hook: founder/place-based names, a stable founding anchor, independence choices, and no historical-American naming by old coordinates. Unsupported transitions remain blocked. Do not alter colonial identities outside the generated geography.
  - QA: `uv run pytest -q tests/test_colonial_identity.py`; cover different founders in one area, two colonies of one founder, moved capitals, changed overlords, independence, manual names, and a non-American colony. Check hidden-country and undiscovered-goal visibility. Evidence: `local_data/content/task-07.json`.
  - Depends on: 2, 3, 6. Commit: `Name generated colonies from place and founding identity`.

- [ ] 8. Generate six formable-country families
  - Recommended task executor category: unspecified-high
  - Closes GAP-3/5/7. Add `src/rnw/formables.py` and `src/rnw/eu5_formables.py`; integrate semantic roles, identity, tag/key reservations, and historical-formable checks.
  - Acceptance: finite export-time declarations with suitable connected targets, potential/allow conditions, fixed identities/flag keys, no ghost starting countries, and no reward cycles. Tag/flag acceptance is gated by task 2; unsupported branches remain blocked.
  - QA: `uv run pytest -q tests/test_formables.py tests/test_identity.py tests/test_script_rewrites.py`; provide a structural eligibility witness for each family and reject disconnected targets, diaspora-only eligibility, invalid rank, repeated formation, and key/tag conflicts. Structural witnesses do not prove campaign attainability. Check undiscovered-goal visibility. Evidence: `local_data/content/task-08.json`.
  - Depends on: 2, 3, 4, 6; the postcolonial branch also depends on 7. Commit: `Generate political goals and world-specific formable countries`.

- [ ] 9. Diversify societies and balance their opportunities
  - Recommended task executor category: unspecified-high
  - Closes GAP-3/6. Extend `content.py` and, where necessary, societies, natives, development, and infrastructure without reshaping geography to fit a predetermined archetype.
  - Acceptance: the four additional trait combinations described above have real advantages, constraints, stories, and goals. Examine low tribal-land development relative to vanilla without spreading developed-city bonuses everywhere to match an average.
  - QA: `uv run pytest -q tests/test_content_archetypes.py tests/test_societies.py tests/test_development.py tests/test_empires.py`; reject unsuitable geography and flat super-bonuses, support worlds without empires, and prove structural variation beyond names/colors. Evidence: `local_data/content/task-09.json`.
  - Depends on: 3-8. Commit: `Diversify generated societies through geography and institutions`.

- [ ] 10. Verify integration and prepare the game-facing candidate
  - Recommended task executor category: unspecified-high
  - Closes all gaps. Add integration/local checks; update version, epoch, golden world, testing documentation, claims, research log, and experiment records for implemented changes.
  - Offline QA: `uv sync --locked --group dev && make check`, then exact local tests with `EU5_GAME_DIR`. Run `RNW_REPRODUCE=1` reference generation only when the heavy check is authorized. Use fast synthetic graphs for the broad corpus and only the necessary representative full worlds; do not start mass heavy generation without approval.
  - Compare Old World objects/files, resource and peoples rerolls, references/tags/flags/localization, input manifests, output digests, and epochs. For files containing several layers, compare owned fields rather than demanding false whole-file identity. Install only a new recorded test-mod candidate and verify its bytes.
  - Runtime QA after separate authorization: a native chain/reform/formation; colonial discovery/foundation/naming/contact/disease; self-government/independence/renaming; conquest or disappearance of an actor; save/load; AI behavior and pacing. Prepared or accelerated scenarios test effects separately from natural frequency; forcing an event does not establish its normal occurrence rate.
  - Evidence: `local_data/content/task-10/`; commit conclusions rather than derived logs/assets. Keep OFFLINE-PASS, NOT-RUN, and V-GAME separate. A successful start does not validate a long campaign.
  - Depends on: 4-9, proved runtime hooks from 2, and separate permission for game observations. Commit: `Validate generated content end to end and record acceptance gates`.

## Execution order

1. Foundation: task 1, then 2 and 3. Resolve naming/tag limitations before mass authoring.
2. Restoration and identity: tasks 4 and 6. These close existing losses but are not completion of the whole plan.
3. New opportunities: tasks 5, 7, and 8 according to their dependencies.
4. Variety and combined verification: task 9, then 10.

Give shared exporter, key registry, and content-model edits one owner at a time. Parallel tasks do not imply concurrent edits to those integration points.

## Assessing interest

| Dimension | Evidence to seek | Insufficient evidence |
| --- | --- | --- |
| Accessibility | A suitable bearer, attainable prerequisites, and a working outcome | A file or button exists |
| Variety | Different worlds produce different goals, societies, and development paths | Different names and colors |
| Choice | Costs and beneficiaries vary with circumstances; alternatives make sense | A free best option |
| Discovery | Contact, ownership, or knowledge reveals opportunities | All hidden realms/goals are visible before exploration |
| Dynamics | Conquest, capital moves, independence, and save/load preserve causality | It worked once at startup |
| Balance | Advantages and costs use normal mechanics and AI decisions | An archetype label grants power |

The thought-experiment criterion is whether players on different seeds can describe different decisions they had to make. Event counts and invented percentages of vanilla interest are not substitutes.

## Final verification

- [ ] F1. Reconcile the source inventory with every adaptation/omission; nothing disappears silently.
- [ ] F2. Review code quality, determinism, layer ownership, and Old World preservation using completed checks only.
- [ ] F3. Observe separately authorized game scenarios. While launches remain prohibited, the runtime result is NOT-RUN, not PASS.
- [ ] F4. Map IS-1 through IS-7 to evidence and experiences from two materially different campaigns, with limits stated explicitly.

## Decisions proposed for adoption

Use a plausible random world by default; retain meaningful historical formables alongside generated ones; preserve player-chosen names; avoid additional settings. There are no blocking questions for this design proposal. Engine uncertainties belong to task 2 rather than being described as established capabilities.

The requested brainstorm and proposed plan are complete. Implementation and game observations have not begun. If this direction is accepted, resolve only changed scope or newly discovered limitations rather than repeating the baseline audit.
