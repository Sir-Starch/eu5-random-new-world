# Roadmap

## Released baseline

**RNW 1.1.0 / epoch 60** is the current released and accepted baseline, targeting
**EU5 1.4.6 / Steam build 26300913**. See the [release notes](releases/1.1.0.md)
and [known limitations](known-limitations.md). The 1.0.0 record below preserves
the first release's acceptance and distribution history.

**RNW 1.0.0 / epoch 59**, released on 2026-10-29, targets **EU5 1.4.5 /
Steam build 26211608**, including optional Across the Pillars adaptation.
The owner accepted the tested product and completed the rules review (C437).
[GitHub Release](https://github.com/Sir-Starch/eu5-random-new-world/releases/tag/v1.0.0)
is published with checked downloads (C439). The owner also installed and launched
the [Workshop item](https://steamcommunity.com/sharedfiles/filedetails/?id=3829217331);
its downloaded hub matches the prepared package (C441).

| Area | Shipping capability | Current reference |
|---|---|---|
| Geography (D0/R1–R5, V1) | Procedural land, relief, climate, biomes, rivers and connected hierarchy with preserved Old World | [Architecture](architecture.md), [terrain](terrain-biomes.md) |
| Seas (S1/S2) | Ports, named waters, lanes, currents, crossings and optional wider ocean canvas | [Sea geography](sea-geography.md) |
| Societies and economy (R6/R7) | Countries and tribes, populations, cultures, religions, markets, technology, empires and varied societies | [Natives](natives.md), [economy](economy.md) |
| Content (N0–N5) | Vanilla content dispositions, adapted geography keys, stories, formations and colonial names | [Content plan](content-plan.md), [catalogue](content-catalog.md) |
| Languages (L1) | Generator and world text in the official languages discovered from the installed game; eleven for this build | [Localization](localization.md) |
| Generator (R8/U1/G0–G4) | Tauri window with the classic Qt window as fallback, world library, atlas, codes/files, layer rerolls, queue, recovery and installation | [Guide](generator-guide.md), [GUI design](gui-design.md) |
| Runtime and delivery (R9/R10/G5/P1) | Rust kernels, bounded memory, Windows/Proton hub, native Linux application, tagged CI and public releases | [ADRs](README.md#decision-records), [release process](release-process.md) |

The phase codes remain useful identifiers in research records; they are not a
list of unfinished prerequisites. Detailed observations keep their original game
build and scope. Known limitations are in [one current page](known-limitations.md).
An unobserved detail alone does not reopen acceptance or require another game session.

## Released in 1.1.0

- **Peasant population mix (issue #6):** Advanced → Peoples controls the upper peasant share
  at full social complexity from 30% to 80%, across all inhabited land. It keeps the existing
  population and state-support rules and works in both windows and world codes. See
  [native societies](natives.md#peasant-and-tribesmen-balance).

- **Resource distribution sliders:** Advanced → Resources offers individual
  0–3× placement weights for all 34 ordinary New World RGOs alongside the existing
  precious-resource control, in both windows and every official language. Defaults
  retain vanilla weights and climate/terrain matching. These are relative placement
  probabilities: increasing one leaves fewer locations for others and does not
  change production per location. See [economy](economy.md#resource-frequency-controls-110).

- **Native polity growth and identity cores (issues #5, #7, #8):**
  - **Corridor affinities (issue #8):** political growth adds seeded preferences for farming
    corridors, similar-habitat belts or coasts alongside generalist expansion. See
    [native societies](natives.md#territorial-variety-issue-8-110--epoch-60).
  - **Identity cores (issue #7):** identity-aware capital scoring and territorial growth give
    native states stronger primary-culture and faith cores while preserving cultural minorities.
    See [native societies](natives.md#primary-identity-cores-issue-7-110--epoch-60).
  - **State land targets (issue #5):** Advanced → Peoples → Land in states targets up to 60%
    of inhabited land; States quick choice's Many setting targets 44%. See
    [native societies](natives.md#higher-state-land-targets-issue-5).

- **Hydrology and continental variety (first pass):** coasts from a bent density field,
  vanilla-calibrated lakes (Pareto tail up to ~22,000 px, `lakes.py`), rivers that cross lakes
  with outflows at their lowest rim (`rivers.py`), local river valley carving (`carve_valleys`),
  inland seas, lagoons behind spits and gulfs behind straits (`gulfs.py`), isthmuses (`isthmuses.py`),
  and army strait crossings (`straits.py`, `crossings`). See
  [terrain](terrain-biomes.md#coast-shape-water-bodies-and-drainage-110--epoch-60).

- **Ocean currents, slivers and sea-zone cleanup:**
  - Clear, directed ocean current courses that continue vanilla currents or follow game gyres
    across open water (`currents.py`).
  - Merging thin sea location slivers (`synth.merge_slivers`) and absorbing needle remainders of
    trimmed sea zones into the canvas. See [sea geography](sea-geography.md).

- **Colonial overseas boundary protection (issue #9):** connected ocean-area boundaries
  separate generated American coastal waters from passable Old World seas, preserving colonial
  nation overseas status for North and South America. Checked by export validation.

- **Pacific canvas expansion and island preservation:**
  - Expanded canvas reaches the Pacific side, opening wide ocean while moving covered island
    groups whole to the nearest free ocean with their vanilla height, material and mountain layers intact.
  - Advanced → Land → Distance from the Old World (`new_world.centre_permille`) moves land toward
    the ocean middle without changing total land area.

- **Mountains and hills rework:** continuous chains with varied-height massifs, ridged crests,
  additive mountain stamps from game sources rotated along range axes with material layers, fine
  ground grain matching vanilla roughness, and removal of lake cones. See
  [terrain](terrain-biomes.md#mountains-and-hills-110--epoch-60).

- **Polar map-edge correction:** ordinary continents are constrained to narrow polar contacts,
  locations grow larger toward the poles, and all edge-touching land locations are impassable.
  See [terrain](terrain-biomes.md).

- **Climate and vegetation consistency (issue #4):** paired (climate, vegetation) smoothing
  prevents incompatible biomes (e.g., desert in subtropical or forest in arid).

- **The Wall preset:** procedural longitudinal continent or island chain with mountain spine,
  island detour routing, width/position/gaps controls, and broader secondary continent placement.
  See [terrain](terrain-biomes.md#the-wall).

- **Generator workbench and performance:**
  - Tauri window as primary 3-pane workbench (ADR 0011), classic Qt window as fallback.
  - Stable generation ETA forecasts based on stage dependencies and local timing history.
  - Responsive background world selection and worker-computed map relief.
  - Workshop Gameplay/Utilities tags and updated descriptions.

## Next major update — 1.2.0: history and geopolitics

**Owner direction, 2026-11-02.** The next major update will focus on history and
geopolitics, with three connected goals:

- **Simulated prehistory:** simulate a history before the 1337 campaign start so
  the starting world has a past that explains its political situation. Histories
  should arise from the generated world and shape its start state.
- **Complex starting relationships:** use that prehistory to form a web of
  relationships between countries, rather than choosing each relationship in
  isolation. Existing alliances, rivalries, subjects and extraordinary societies
  provide a starting point; the exact mechanics remain a design decision.
- **Deeper and more diverse societies:** develop societies' distinct identities,
  structures and experiences so their differences matter to their history,
  relationships and play, building on geography, population, economy, culture
  and religion.

**Owner clarification, 2026-11-05.** The goal is a varied, interesting political
map at the campaign start, with generation controls keeping their meaning. A
world may have no large empire at all. History is the backstory of EU5 countries
within the generation parameters, not a world simulation. The plan's
[audit](history-plan.md#21-independent-audit-and-redesign-2026-11-05) applies this.

This brings generated national histories and broader society/diplomacy work out
of the general future list and into the 1.2.0 focus. The earlier
[community history suggestion](https://www.reddit.com/r/EU5/comments/1xia8uu/comment/19rtkpx9hq1z9/)
remains background. See [native societies](natives.md) for the implemented model
and the [content plan](content-plan.md) for the story/content boundary.

The direction is agreed, and the owner accepted the detailed
[1.2.0 plan](history-plan.md) on 2026-11-02: simulation model, decisions, EU5
projection with fallbacks, controls, phases H0–H7, cut order and acceptance
criteria. Implementation needs a separate instruction. This documentation
decision does not bump the package version or algorithm epoch.
Implementation follows [ADR 0003](adr/0003-versioning.md): 1.2.0 is a compatible
MINOR target, and changed world output will need a pending epoch relative to the
last frozen release. Preserve the Old World, existing worlds and saves, both
generator windows and the one-enabled-world-mod rule.

### Workshop feedback in 1.2.0

**Owner decision, 2026-11-05.** The Workshop item's 75 comments and its two pinned
discussions were triaged on 2026-11-05 (C493). Bugs and generator errors come first,
then requests that fit history and geopolitics. Another feature joins only when many
players are likely to need it soon. These items ship with 1.2.0 beside the
[history plan](history-plan.md). They leave its §18 criteria unchanged, except that
the W2 matrix runs in R6 and the R6 candidate enables W6.

| ID | Report | 1.2.0 work | Done when |
|---|---|---|---|
| W1 | The New World is all Clay, and its climate, vegetation, topography and resource map modes are empty (several worlds, also after 1.1.0) | [V-LOCAL] Clay is the first good in the installed `00_raw_materials.txt`. [INFERRED] The game therefore read no template for the generated locations. The world writes those templates and its export parses them, so the likely causes lie outside the generated file. Candidates: a mod after the world replaces `in_game/map_data/location_templates.txt` or another file the world writes; two worlds are enabled; or the installation is incomplete. The generator already reads the active playset for diagnostics. **Implemented 2026-11-06** (`app/playset.py`, [V-EXEC]): the world's page in both windows and the diagnostics report warn when an enabled mod after the world has files at the same paths as the world's (compared by path without case, `.metadata` and root files excluded), and when another RNW world is enabled. A later mod that defines the same keys in a file of another name is not found. Later mods whose folders the generator cannot find (a Workshop item it cannot place) are listed only in the diagnostics report, not in the window. The troubleshooting guide names the symptom | Synthetic playset fixtures for each case (`tests/test_playset.py`); text in every official language (window catalogues). The reported world stays unreproduced until its code and `error.log` arrive |
| W2 | *Create a version* with new peoples or resources stops with "the generator stopped" | Run the version path as a matrix: presets × seeds; new peoples and new resources twice each; a world in the game and one only in the library; *Keep this one in the game too*; a drawn land image; both windows. Fix every failure at its cause. The message and the diagnostics report keep the technical detail | Matrix passes in R6; each failure found has a test |
| W3 | Found in triage: a version of a world made by an earlier algorithm epoch can get different land | [V-LOCAL] The version buttons are enabled for every world. `worldcode.rolled` records the running generator, so the land comes from the current algorithm. Epoch 61 would expose every 1.1.0 world. The version path refuses a world of another epoch and says why, in both windows and the CLI. It points to a new world with the same settings | Tests in both windows and the CLI; text in every official language |
| W4 | Castile cannot form a colonial nation when the New World lies close to Western Europe (reported 3 Nov, after the issue #9 fix) | Audit the C453 overseas gate at the minimum *Distance from the Old World*, on presets whose land reaches the waters by Western Europe. Check every input of passable neighbours against the export check, including moved island groups and their sea zones. Extend the check if an input is uncovered. Known limitations say that worlds made by 1.0.0 keep the defect | Audit recorded; any newly found contact is rejected by export validation |
| W5 | The queue stops at the first failed world | A failed world stays in the queue, marked with its error, and the next world starts. *Cancel* still stops the queue. Both windows | Tests; text in every official language |
| W6 | An optional reveal of the whole New World at the campaign start, for multiplayer (promised on the Workshop) | A world setting, off by default and carried in world codes. At game start every country discovers every area of the generated New World through the vanilla `discover_area` effect, a start effect that leaves vanilla country records unchanged. Output with the setting off is unchanged. Before shipping, check the vanilla content that reacts to discovering the Americas; for example, `institution_events.txt` reads `discovered_any_in_americas_trigger` | The R6 owner sitting sees the New World revealed at start |

W1–W4 belong to the irreducible scope of 1.2.0. When time runs short, W6 is cut
first and W5 second, before the history cut order in the plan's
[§17](history-plan.md#17-phases-and-scope-control).

**Not taken into 1.2.0:**

- **Feudalism and Legalism in the New World.** Vanilla spawns them only in Europe;
  they reach the New World by spreading ([economy](economy.md#research-limits-and-possible-refinements)).
  This is not an RNW defect. Known limitations say so. Seeding institutions is future research.
- **Polynesia split across generated land** (C479). This is a retained-region limitation;
  the reporter found that nothing breaks.
- **An archipelago over the engine's limit.** This is the documented invalid-seed case;
  the message already asks for another seed or larger locations.
- **More realistic mountains and hills.** Delivered in 1.1.0.
- **Custom progress tracks and new cultures.** RNW uses vanilla American cultures and their
  advances.

## Player requests after 1.2.0

These player requests from the Workshop are candidates, not promises. Each needs its own
scope when chosen.

- **Colonizers' place names (promised on the Workshop):** a location takes the name of
  its owner's language. Vanilla does this with `<location>.<language>` keys in
  `location_names`; the installed Spanish file names American locations too. Names
  adapted for the main colonizing languages would be generated at construction and
  translated into every official language. This is the first candidate after 1.2.0.
- **An option to put all organized land into settled states:** this revises the fixed
  tenure partition ([history plan §21.4](history-plan.md#214-unchanged-commitments)).
- **Renaming generated countries** in the generator, written at construction.
- **Terrain classes in a drawn land image** (mountain ranges, wasteland), together with
  the fantasy-map presets below.
- **Institutions at the start:** research whether a world mod can seed them.
- **Curated ready-made worlds:** further standalone Workshop items, such as the published
  Wall world, are the owner's distribution choice, not a generator release.
- **More Locations:** only as an explicitly supported input layer after a payload audit
  ([assessment](research/more-locations-compatibility.md)).
- **Generating the whole world** remains an idea for a separate project after RNW, not
  RNW planning.

## Other future work requested by the owner

These are directions, not promises for 1.0.0 or automatic tasks for every agent.
Choose a concrete scope when work is requested; use the next release target and
pending epoch according to [ADR 0003](adr/0003-versioning.md).

- **Hydrology (future directions):** deltas and river splits in coastal plains; drainage-driven
  macro-relief and valleys (where mountain ranges and valleys are sculpted by river drainage
  rather than relief generated first); climate-dependent (endorheic) closed basins in arid regions;
  and smoothing high-mountain lake bank slopes.
- **Continental variety (future directions):** sea routes and distinct naming for inland seas,
  gulfs and lagoons treating them as separate named waters; and coastline shapes tied directly
  to regional climate and geology.
- **Ready-made fantasy maps:** add land-shape presets such as a Kerbin-inspired
  map within the New World generation area, using the existing land-mask workflow.
  Verify that workflow alongside the presets
  ([community suggestion](https://www.reddit.com/r/EU5/comments/1xia8uu/comment/19rtj2ndbo2gz/)).
- **Optional Easter egg countries:** add country scenarios inspired by EU4 RNW
  Easter eggs, including Vinland, Secret Denmark and Atlantis
  ([community suggestion](https://www.reddit.com/r/EU5/comments/1xia8uu/comment/19rtdzylmh2mb/)).
- **Optional alternative-history settlements:** add an opt-in setting for
  historically inspired peoples and overseas settlements, including Norse/Vinland
  settlements, integrated into the generated societies
  ([community suggestion](https://www.reddit.com/r/EU5/comments/1xia8uu/comment/19rtcqs3rwjgi/),
  first added 2026-10-29).
- **Generator interface and settings:** running the Tauri window under Proton with a WebView2 runtime,
  and exposing additional generation settings in the interface.
- **World-wrap research:** retain the accepted mechanical fixes and visual source
  extension. Use the [dedicated dossier](research/map-wrap-dossier.md) for new
  evidence relevant to a possible Paradox report. A historical rendering comparison
  is a research option, not a standing request to the owner.

Confirmed regressions take priority when reported. Historical diagnostic warnings
need attribution before becoming RNW bug tasks. Signing and extra platform
coverage are improvements; unsigned Windows delivery is disclosed and accepted.

## History

The [roadmap through 1.0.0](archive/roadmap-through-1.0.md) preserves phase-by-phase
plans, early acceptance checklists, version milestones and campaign follow-ups.
Use the [changelog](../CHANGELOG.md) for releases and the
[claims ledger](research/claims-ledger.md) for scoped evidence. The archive's
old pending states are not the current backlog.
