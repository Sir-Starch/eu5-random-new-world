# Changelog

All notable changes to Random New World. The project has one product version ([ADR 0003](docs/adr/0003-versioning.md)): `0.MINOR.PATCH` is development, MINOR rises when the owner accepts a roadmap phase in game, and the first Steam Workshop publication will be 1.0.0. Any change to generated output raises at least PATCH. A change to any file of a world's mod other than `.metadata` also starts a new **algorithm epoch** with a new reference world.

`C###` numbers refer to the [claims ledger](docs/research/claims-ledger.md). Evidence labels (`[V-GAME]`, `[V-EXEC]`, …) are explained in [CONTRIBUTING](CONTRIBUTING.md#evidence-labels). Entries without an in-game result have been checked offline only.

## [Unreleased]

- Generator progress keeps its stage description on one fixed-height line, shows a live ETA that adapts to the weighted stage pace measured in the current run, and uses the same rounded percentage in the world list and progress bar.
- The Workshop description is rewritten for players, as EU5 mod pages are: what a world holds, a quick start, the window's choices, why there is a program, the limits, a FAQ and links, with an emoji for each section. It is kept in Steam's markup, ready to paste, in all eleven official languages, and each text is checked against Steam's limit of 8,000 bytes (C277).
- Generator library: select several worlds with Ctrl/Shift or Select all, then remove their mods from EU5 directly below the list. Codes and pictures stay in the library. A separate bulk deletion asks once before deleting library records and kept files. Selection survives list updates; removal no longer needs the game installation, and deletion errors stop the batch visibly (C266). The library panel takes its width from the splitter alone: its texts wrap or clip instead of setting a minimum, so a wide font or an error that names a long Windows path no longer widens the window past 1080 pixels.
- Repository prepared for publication: new README, changelog, contribution, security and conduct documents, issue and pull-request templates, documentation index. Completed agent hand-off notes were retired, and the history was cleaned of local machine details.
- Windows fixes found by the first CI run on Windows. The window's self-test closes its log before removing its temporary folder. The atlas cache also compares file sizes, so a file rewritten within one clock tick is not served stale. Tests now write fixtures with LF line endings, escape Windows paths in Steam's VDF, use short test ids, and wait for the window to enable a control before clicking it. A notice about a world's visibility is no longer wiped by the refresh that the change triggers.

## 0.12.0 — 2026-10-24

- **Optional ocean expansion (S2).** *Expand generation into the oceans* is enabled by default and recommended. It adds a fixed ocean sector around the Americas, preserving the Old World and protected islands; unchecking it uses the original coast-following canvas. The choice travels in the world code, sketches, land templates and rerolls. Codes made before 0.12.0 select the original canvas. The canvas grows from 37,978,627 to 53,240,944 pixels on the current map contract.
- Surviving closed oceans keep their vanilla names in every official language. Connected retained and generated water shares one location; land or lanes separating it produce separate connected locations with the same name. Disconnected ocean remnants no longer exclude an entire closed ocean from generation. Passable water, currents and ports remain separate.
- Location density and the window's budget estimate account for the larger domain. Discovery uses the actual generated coastal areas, including new ones and omitting regions that have become landlocked. A short gap crossing two sea zones no longer produces an invalid army crossing. Epoch 30; expanded-map engine results remain unverified.
- Verification uses the project's Python 3.12 environment explicitly, resolving the previously recorded type-checker discovery failure.

## 0.11.6 — 2026-10-24

- **L1: the generator's window in every official language.** The window starts in the language Steam runs the game in, or in the one chosen in Settings (the change applies at the next start). All its texts are translated into the ten other official languages: export stages, messages and errors included. Numbers are grouped the local way. Maps show place names in the window's language, and, when the game is installed, the game's own names for cultures, religions, resources and terrain. Every language is tested to fit the smallest supported window size. The atlas beside a world's mod is now format 2, which stores names as phrases; format 1 is still read. The mod's files are unchanged, so this stays in epoch 29.
- The Workshop description is written in every official language (`docs/workshop/`), each checked against its English source. A mod's metadata holds one language only, so the mod list's titles stay English (C276).

## 0.11.5 — 2026-10-24

- **L1: the world's mod in every official language** ([localization](docs/localization.md), C268–C274). The stories, formable countries and exceptional places are translated into Brazilian Portuguese, French, German, Japanese, Korean, Polish, Russian, Simplified Chinese, Spanish and Turkish. Their English was rewritten first: fewer repeated devices, more of the country's own voice, as the game's events have it. Generated names follow each language's geography: *Море Кайра*, *Kaira-Meer*, *Mer de Kaira*, *カイラ海*; parts of a sea are *Западная часть моря Кайра* or *Golfe d'Akaira du Nord*; formables are *Кайрский союз*, *Kairanische Union*, *Unia Kairańska*; colonies are *Новая Кайра* or *ヌエバ・カイラ*. Russian, Japanese, Korean and Chinese write every generated name in their own script, as the game does with its American names. Country adjectives take the form the game's texts complete in Russian, Polish and German. A release check fails on a missing or outdated translation. Epoch 29, reference world of 814 files.

## 0.11.4 — 2026-10-24

- **N5: region and area keys by physical content** ([design and audit](docs/research/n5-region-keys.md), C262–C265). The 14 American land regions and 135 land areas keep their vanilla parents, and each key goes to the generated part whose climate, relief, coast and relative size are closest to the vanilla template, chosen by one global integer assignment (position only breaks ties). On three worlds the total template difference falls by 18.91 to 22.26 per cent, and the Old World is unchanged. Region parts are built before names are assigned, with room for every original area. Epoch 28, reference world of 814 files.

## 0.11.3 — 2026-10-24

- Fixes from the 0.11.2 sitting and the seed-210 regression ([046](experiments/046-sitting-fixes/README.md), C257–C261):
  - The sea planner no longer emits an empty area when an ocean area survives entirely in vanilla water.
  - The lobby handles an absent selected country through an optional saved scope.
  - Map-name replacements occupy their installed localisation paths and no longer define the same keys in an extra file.
  - The window reports completion only after its library holds the finished world.
- Epoch 27.

## 0.11.2 — 2026-10-24

- **R7d: more varied societies** ([natives](docs/natives.md), C251–C253). Besides the great empire, a world can now hold:
  - a sea league: 3 to 5 republics on one sea, allied in a ring, with a city and a market at the hub's port;
  - a highland confederation: 3 to 6 tribes of one faith in one `tribal_confederation`;
  - a fractured realm: 3 or 4 rival centres;
  - a sacred centre: a theocracy among rivals of its faith.

  Each uses records the vanilla 1337 setup already uses, with a cost beside every gain. With the chance set to 0 the world is byte for byte as 0.11.1 made it. The window calls the control *Extraordinary peoples*. Epoch 26, reference world of 792 files.

## 0.11.0 – 0.11.1 — 2026-10-24

- **0.11.0:** `[V-GAME]` the sea phase (S1) is accepted in game. The owner observed the 0.10.14 world for four months of game time, and the logs show no port, lane, topography, current or crossing error (C248).
- **0.11.1:** the game's closed ocean zones have no unit or combat locators, and generated closed zones no longer have them either. The lobby's scripted GUI checks `country_exists` before asking about the selected country, which removes 263 script errors a session (C249–C250). Epoch 25.

## 0.10.12 – 0.10.14 — 2026-10-24: sea geography

- **0.10.12:** ports are assigned so that every coastal sea zone has one wherever the land allows. Water is named by its shape (seas, gulfs, bays, straits, coasts, capes, island waters), and the game's ocean areas keep their names in every language. The game's own kinds of water are used: deep ocean, inland sea, narrows. Generated deep water continues the game's currents (C232–C240). Epoch 22.
- **0.10.13:** `[V-GAME]` the open ocean is closed to ships, as in the game: lanes one or two cells wide follow the currents, and the remaining deep water is impassable `ocean_wasteland` (C241–C244). Epoch 23.
- **0.10.14:** strait crossings. Landmasses that come within 36 pixels are brought together to a narrow channel, and every pair of lands across a run of at most 9 pixels of one sea zone gets an `adjacencies.csv` row (C245–C247). Epoch 24.

## 0.10.0 – 0.10.11 — 2026-10-23: New World content

- **0.10.11:** offline audit of N0 to N4 ([audit](docs/research/n0-n4-audit.md)). Three faults are repaired: `province_definition:` references are remapped, hidden story events have titles, and the DLC pyramid models of Teotihuacan and Cholula are no longer moved to random places. The export now refuses a world in which a vanilla script object vanished without a decision (C222–C231). Epoch 21.
- **0.10.10:** *Contact across the ocean* and *Colony becomes a country* stories, a *Postcolonial federation* formable and 70 colonial names (*New X*, built from each region's generated name) (C218–C220).
- **0.10.9:** four stories: *Harvest and food supply*, *Route and market*, *Great alliance*, *Empire and periphery* (C215–C217).
- **0.10.8:** four formable families: *Highland confederation*, *Maritime league*, *Cultural commonwealth*, *Regional realm* (C212–C214).
- **0.10.7:** `[V-GAME]` the New World's countries are dimmed in the lobby list instead of hidden, which ends the list's flicker (C205–C211).
- **0.10.6:** `[V-GAME]` fixes from the first console sitting on EU5 1.4.4 (C198–C204).
- **0.10.5:** content model and first stories: *River centre*, *Sacred centre* and the *River-basin union* formable (C193–C196).
- **0.10.4:** five rare resource places replace the vanished historical bonuses: silver, a mercury lode, rich fisheries (C189–C190).
- **0.10.3:** N0 decisions carried out. American historical events, colonial names, colonial formables and the Panama canal are gated off on generated land, and historical formables take the places of their culture (C187–C188).
- **0.10.2:** the mod's languages are taken from the installation; all eleven official languages are written, including Turkish (C178, C186).
- **0.10.0 – 0.10.1:** the country-selection cover uses vanilla terra incognita drawings (C172–C174).

## 0.9.24 – 0.9.33 — 2026-10-22 to 2026-10-23

- **0.9.33:** holders of the great empires' opinions discover their partners' capitals (C170–C171).
- **0.9.32:** the country-selection cover stays on the map and off the frame (C169).
- **0.9.30 – 0.9.31:** the spline network: road strips for generated locations, in vanilla's order. `[V-GAME]` no strip errors, and roads are drawn (C161–C168; [interoperability register](docs/research/interoperability.md) R-001).
- **0.9.29:** great empires with vanilla ranks, royal roads, feared neighbours and resentful vassals (R7c, C160).
- **0.9.28:** technology levels and regional families from each society (R7b, C159).
- **0.9.26 – 0.9.27:** extended New World cover and lobby guards. The cover is isolated in a private map-mesh include so loading screens and character scenes keep vanilla shaders (C150–C154).
- **0.9.25:** verified against EU5 1.4.3 (Steam build 26105915) (C148–C149).
- **0.9.24:** reproducible layered worlds and the independent generator application: world codes, library, rerolls, world files, queue, atlas ([ADR 0010](docs/adr/0010-layered-worlds-and-a-generator-of-its-own.md), C141–C147).

## 0.9.1 – 0.9.14 — 2026-10-19 to 2026-10-21

- **0.9.14:** every world is a mod of its own. Adds world types, playable settings ranges and spoiler-free pictures (C116–C120).
- Delivery decided: one Workshop item carries the generator, and worlds are built locally ([ADR 0009](docs/adr/0009-hub-mod-with-generator.md)). The project is licensed under MPL-2.0.
- Rust core for the hot kernels ([ADR 0005](docs/adr/0005-native-core.md)), machine-aware threads and memory ([ADR 0006](docs/adr/0006-machine-resources.md)), and the Qt application window ([ADR 0007](docs/adr/0007-application-window-and-packaging.md)).
- **0.9.6 – 0.9.13:** EU5 1.4.2 support, collision-free localisation keys, government templates, and fixes found against the vanilla 1.4.2 baseline log.
- **0.9.4 – 0.9.5:** compact, connected areas and regions; coastal water belongs to the region of its shore.
- **0.9.2 – 0.9.3:** start development, harbours and market villages from the societies (R7a, C73–C76).
- **0.9.1:** one product version for the mod and its output (ADR 0003).

## Earlier development — 2026-10-13 to 2026-10-19

- **R6 (generator 0.8.0 – 0.9.0):** native societies (hearths, cultures, religions, states, tribes, towns, markets, holy sites), place names in local languages, and vassals. `[V-GAME]` loads with visible states (C67–C72).
- **V1 (generator 0.4.0 – 0.7.0):** terrain from one relief, climate and biome model, rivers from drainage, and coastlines that follow the seed. `[V-GAME]` accepted by the owner (C47–C66).
- **T3 (2026-10-14 – 15):** a New World with new location IDs replaces the 1337 Americas, and its terrain decals, water, foam and lake meshes are rebuilt. `[V-GAME]` the first playable start (C42–C46).
- **D0 (2026-10-14):** the first deterministic geography generator: moved land–sea boundaries between existing American location IDs, byte-reproducible. `[V-GAME]` location outlines follow the mod's raster (C28–C34).
- **Research (2026-10-13):** inventory of EU5 1.4.1, the map contract and its fingerprint, the feasibility ladder, and a metadata-only test mod (C01–C27).
