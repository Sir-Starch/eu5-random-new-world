# Changelog

## 0.13.21 — 2026-10-28

- Sacred-centre theocracies now start with compatible marriage and heir-religion
  laws and a native assembly, read from the installed game's precedents.
  Generation rejects incomplete or incompatible government institutions before
  installing a world. Existing worlds and saves are preserved.

## 0.13.20 — 2026-10-28

- Restore the previous periodic primary terrain-source extension at the owner’s
  request after the unpadded version exposed a more prominent map seam. Epoch 57.
- Retain independent river watersheds, genuine-outlet validation and all mechanical
  wrap corrections. Rendering of this combination remains unverified in game.

## 0.13.19 — 2026-10-28

- Generate independent river catchments on either side of the display seam, with
  closed boundaries and genuine sea/lake outlets. Preserve the expanded canvas
  and mainland crossings. Epoch 56.
- Follow every main river to actual water and reject inland endings. Encode the
  planned network without cutting pixels or inventing sources at the seam.

## 0.13.18 — 2026-10-28

- Remove the extended terrain sources and shifted primary placements used to conceal
  the world-edge crack, now reproduced by the owner in vanilla. Retain continuous
  geography, location identities and all route/hang corrections. Epoch 55.
- Separate the terrain crack, river discontinuity and locator diagnostics in a
  dedicated evidence dossier, including an owner-run historical comparison plan.

## 0.13.17 — 2026-10-28

- Build remote states around local farming centres before allocating population. Landed
  countries must meet the installed vanilla Americas’ minimum peasant population and share;
  insufficient settlements remain tribal, including would-be confederation members.
- Give disconnected groups of landed countries a trading town and local market, reusing
  existing centres within a group. Preserve the population budget and vanilla expansion rules.
  Epoch 54; actual income and subsequent AI development remain unverified in game.

## 0.13.16 — 2026-10-27

- Build ocean routes from the generated shores and live current entries. Interior remnants
  of the old world's current footprints no longer impose curved fragments on the new map.
- Require an opening of useful width where a deep route meets other water; a few touching
  pixels no longer count as a completed ocean route. Natural shallow channels keep their
  contacts. Isolated one-location gaps remain navigable ordinary sea without current arrows.
- Align unambiguous current passages with their actual exits, including ordinary water at
  their ends. Preserve the generated land and relief. Epoch 53.

## 0.13.15 — 2026-10-27

- Keep sea classifications consistent with planned ocean lanes when closed water is folded,
  complete any route ends introduced by later crossings and check navigation before the
  expensive export stages. Epoch 52.
- Keep location, province and area replacements separate when vanilla reuses a name. Choose a
  drawable river-fragment start when the first one leaves no room for a confluence marker,
  without changing the physical river or discarding its drawing pixels.
- Check the location limit against final identities, avoiding a premature refusal when generated
  sea cells share a retained ocean identity.
- Show generation errors in a selectable, scrollable panel with explanations for ocean,
  river, location-limit, file and unexpected errors. Offer an immediate retry with a different
  seed and the same settings.

## 0.13.14 — 2026-10-27

- Align currents on straight designed crossings to the band's geometry. The direction is
  chosen consistently along each band from its continued source currents; ambiguous broad
  junctions retain their interpolated flow. Epoch 51; game rendering remains unverified.

## 0.13.13 — 2026-10-27

- Plan useful crossings over the generated water before partitioning sea locations. Their
  centre lines are simplified through unobstructed water and their bands become connected
  sea-cell geometry, while actual currents still require a reachable existing source.
- Join small, disconnected retained-ocean remainders to an adjacent navigable sea when they
  share an edge; preserve principal vanilla identities and landlocked remnants. Epoch 50;
  in-game rendering and navigation remain unverified.

## 0.13.12 — 2026-10-27

- Plan crossings between distant shore stretches and retained water from the generated geography,
  remove isolated closed-water slivers before zoning, and name impassable water for its area.
- Partition generated sea cells by Euclidean distance so their shared borders do not develop the
  large Manhattan-distance elbows seen in the owner's hover screenshot. Epoch 49; game rendering
  and navigation remain unverified.

## 0.13.11 — 2026-10-27

- Build sea locations against the installed game's current bands, rather than approximating their
  shape with unrelated sea-cell borders. Complete cyclic open-ocean ends, align unambiguous narrow
  currents with their routes, and reject currents without a reachable, unambiguous source. Epoch 48;
  offline candidate, with no new EU5 launch.

## 0.13.10 — 2026-10-27

- Set up sacred centres as theocracies without inheriting monarchy laws and
  privileges, following the vanilla Tibetan setup. Epoch 47; offline candidate.

## 0.13.9 — 2026-10-27

- Keep vanilla's `ai_balanced` as the normal baseline. Countries receive a more
  distinctive personality only for explicit threats, rivalries, diplomatic ties,
  a great empire's designated prey, or a defining society archetype; a coastline,
  population advantage or ordinary border alone no longer forces a personality.
  The report includes every selection signal, including confederation membership.
  Epoch 46; offline candidate, with no EU5 launch.

## 0.13.8 — 2026-10-26

- Choose generated countries' vanilla AI personalities from their generated context: comparative
  population and technology, borders, markets and coasts, empires' prey and threats, rivalries,
  alliances, subjects and extraordinary-society archetypes. Selection is deterministic and each
  country's profile has an auditable reason in `report.json`; Balanced remains for ordinary border
  states without a defining strategic signal. Epoch 45; offline candidate, with no EU5 launch.

## 0.13.7 — 2026-10-26

- Generated landed New World countries receive a reproducible AI personality assignment, sampled
  by the frequencies of explicit country assignments in the installed game's 1337 setup. Pop-only
  tribal groups remain unassigned; vanilla personality definitions and the setup file are read
  locally and validated. Epoch 44;
  game behavior not yet rechecked.

## 0.13.6 — 2026-10-26

- Correct the mod defects identified in the owner's completed EVXP campaign.
  Treaty comparisons use native scoped numeric values; generated treaty files
  carry UTF-8 BOMs and geography labels in all eleven official languages.
- River drawing fragments stop before the final raster column: EU5 discovers
  components with bounded coordinates but its line walker can normalize that
  column's next neighbour to column zero, joining unrelated drawing fragments.
  Physical drainage, carved valleys and continuous location identities stay intact.
- Write exactly one VFX locator per final location, including retained oceans;
  reject duplicate identifiers and incomplete whole-world VFX coverage.
- Derive starting town templates from the installed guild-capacity rules and
  generated development/population. Initial guild levels fit even at the lowest
  market access; vanilla building rules and generated population are preserved.
  Epoch 43; offline candidate, with no new EU5 launch or save migration.

## 0.13.5 — 2026-10-26

- Generated locations keep one identity across the map's raster edge, as vanilla does.
  Removed the legacy seam split for land, sea, lakes and wastelands, including from the
  land cache. This removes the artificial straight border and the extra adjacency in
  the owner's immediately reproducible Towa troop-raising case. Mainland, relief and
  rivers are preserved; no engine patch or replacement geography. Epoch 42. Written
  output and reproducibility checked offline; the owner's
  [22F4 test](experiments/068-continuous-location-identities/README.md#owner-crossing-test-22f4-2026-10-26)
  verifies post-fix troop movement across the seam without a hang (C380).
- When a generated region has no counterpart for a former sea area, setup discoveries
  and script references use the same geographic replacement binding. A vanished
  discovery area no longer retires an otherwise retained country. Existing validators
  still reject unresolved references and incompatible destinations.

All notable changes to Random New World. The project has one product version ([ADR 0003](docs/adr/0003-versioning.md)): `0.MINOR.PATCH` is development, MINOR rises when the owner accepts a roadmap phase in game, and the first Steam Workshop publication will be 1.0.0. Any change to generated output raises at least PATCH. A change to any file of a world's mod other than `.metadata` also starts a new **algorithm epoch** with a new reference world.

`C###` numbers refer to the [claims ledger](docs/research/claims-ledger.md). Evidence labels (`[V-GAME]`, `[V-EXEC]`, …) are explained in [CONTRIBUTING](CONTRIBUTING.md#evidence-labels). Entries without an in-game result have been checked offline only.

## [Unreleased]

- Generator interface improvements:
  - Fixed preview zoom and drag on the "World" tab. The scale constraint now considers both width and height rather than width alone, enabling smooth wheel zoom, scroll drag, and double-click fit on height-constrained preview views.
  - Added an "About…" dialog with application details, version, author, licence, legal disclaimer, and links to the GitHub repository, documentation, issues tracker, and changelog. Accessible from the main window header and the Settings dialog, translated into all eleven official languages.
- Two draws in the window's world type list. **Random** draws one of the five world types, and **Total Chaos** draws a type and every Advanced value within its playable range. Random draws its world type again at each press of the random button; Total Chaos is drawn only when chosen, and its button press only gives a new seed. Both draws stay inside the location budget. The world made is an ordinary world of the type drawn: its values travel in its world code, as any other choice does. No generated output changes. Checked offline: three Total Chaos worlds were made on build 26142040 and finished without error.
- Generator progress keeps its stage description on one fixed-height line, shows a live ETA that adapts to the weighted stage pace measured in the current run, and uses the same rounded percentage in the world list and progress bar.
- The Workshop description is rewritten for players, as EU5 mod pages are: what a world holds, a quick start, the window's choices, why there is a program, the limits, a FAQ and links, with an emoji for each section. It is kept in Steam's markup, ready to paste, in all eleven official languages, and each text is checked against Steam's limit of 8,000 bytes (C277).
- Generator library: select several worlds with Ctrl/Shift or Select all, then remove their mods from EU5 directly below the list. Codes and pictures stay in the library. A separate bulk deletion asks once before deleting library records and kept files. Selection survives list updates; removal no longer needs the game installation, and deletion errors stop the batch visibly (C266). The library panel takes its width from the splitter alone: its texts wrap or clip instead of setting a minimum, so a wide font or an error that names a long Windows path no longer widens the window past 1080 pixels.
- Repository prepared for publication: new README, changelog, contribution, security and conduct documents, issue and pull-request templates, documentation index. Completed agent hand-off notes were retired, and the history was cleaned of local machine details.
- Windows fixes found by the first CI run on Windows. The window's self-test closes its log before removing its temporary folder. The atlas cache also compares file sizes, so a file rewritten within one clock tick is not served stale. Tests now write fixtures with LF line endings, escape Windows paths in Steam's VDF, use short test ids, and wait for the window to enable a control before clicking it. A notice about a world's visibility is no longer wiped by the refresh that the change triggers.

## 0.13.4 — 2026-10-26

- Every generated map mod now has a short description introducing Random New World Generator, giving its world code, and pointing players to the Steam Workshop to create their own worlds. Metadata-only change; algorithm epoch 41 is unchanged.

## 0.13.3 — 2026-10-26

- Installed RNW worlds are recognized automatically from their world code or saved recovery data (C354–C356). Their existing mod folders and playsets stay intact. New application-generated worlds carry a library recovery bundle in `.metadata`, including their atlas, pictures, original record and input manifest; private notes, favourites and user tags stay in the library. Recovery checks the record and asset hashes before committing a full entry, handles metadata-first copies, and preserves existing names and notes. The open window notices new mods and library entries without resetting selection or unsaved notes. Legacy worlds with only a code remain usable, with their missing build/record shown honestly. All new wording is translated into every official language. The Maps panel yields its width to the splitter so wide translations and large desktop fonts cannot expand the window past its minimum supported size. This changes application behaviour and metadata only: algorithm epoch 41 and its reference world remain unchanged.

## 0.13.2 — 2026-10-26

- Ocean routes continue to another lane, coastal water or retained navigable water instead of ending inside impassable ocean (C349–C352). The 657Q report reproduced four open-ocean ends; the gap beside Ruaziasleir Coast is one closed internal cell. The planner opens it and completes the other two ends, adding eleven lane cells in total. Continuations prefer the incoming course's outward direction and cannot loop straight back into their own stem. An independent export check rejects reachable lanes with an open-ocean dead end. Version 0.13.2, algorithm epoch 41; checked offline, with no EU5 launch.

## 0.13.1 — 2026-10-26

- Map object VFX locator generation completed for all expanded ocean locations (C348). When `expand_oceans` adds new `rnw_ocean_*` wasteland locations to `definitions.txt`, their positions are now explicitly exported into `generated_locators_vfx.txt`. In vanilla EU5, all 28,573 locations require a VFX locator; with ocean expansion, all 30,565 locations now have full 1:1 locator coverage, eliminating the engine's `map object locator "vfx" is incomplete!` startup error. Validated offline with an explicit test in `verify_locators`. Algorithm epoch 40 with updated reference world digest.
- Diagnostic audit of corrupted country-name formatting in TR46 observer logs (`error.log:1210–1269`, C347). Traced via binary analysis of `countryname.cpp:1135` and `pdx_text_formatter.cpp:807` to vanilla Jomini country acronym formatting on an Old World Moroccan civil war (`game.log:7389`), producing control-byte-polluted initials `\x15.\x15.W.R.`. Attributed to vanilla engine; no generator defect.

## 0.13.0 — 2026-10-25

- In-game acceptance of the cylindrical wrap, impassable mountain relief and TR46 candidate fixes by the owner (C345-C346). ADR 0003: MINOR rises when a roadmap/campaign phase is accepted in game. The visual seam at the horizontal map wrap is confirmed absent in game (TR46-06a CLOSED [V-GAME]). Impassable mountains are visibly improved and accepted for release (TR46-01 / TR46-02 ACCEPTED [V-GAME], further aesthetic ridge improvements postponed to post-release). No file of a world changes; epoch stays 39 and the reference world is the one of 0.12.9.

## 0.12.9 — 2026-10-25

- Tordesillas follows the continuous New World longitude axis across the raster seam. Its side selection, line moves, side-swap estimates, map shading and final province claims use the same generated coordinates; the western continuation of a mainland is no longer treated as east merely because it is drawn at raster right. Vanilla religion, ownership, existing-claim and province-granularity rules are preserved. Coordinates are immutable native geography/value data, with no campaign startup repair or engine modification. Offline candidate; engine behavior remains unobserved.

## 0.12.8 — 2026-10-25

- Compatible connected impassable land becomes one location before provinces and areas are built, retaining distinct biome boundaries. Generated highlands gain fine eroded height detail sampled from the installed vanilla mountain sources, with continuous wrap support and preserved river lines. Epoch 38; checked offline, final game appearance remains unobserved. Administrative regrouping can rebind native cultures/religions and their dependent start data.

## 0.12.7 — 2026-10-25

- Nearby coasts now receive short local shipping connections as well as global access to the Old World; retained navigable boundary contacts continue into open water. Connected closed water is no longer divided into arbitrary 48-cell oceans with unrelated names. Script replacements preserve ports and passable water, fixing the inland landfalls found in TR46's western voyage. Epoch 37; checked offline, engine navigation and expedition outcomes remain unobserved.

## 0.12.6 — 2026-10-25

- Primary edge heightmaps now contain periodic source pixels beyond the world boundary, with matching source dimensions, cached geometry and original instances. Interior height/material samples keep their alignment and values. This replaces outside-only duplicate placements and provides primary source coverage for boundary vertices and tested page halos while preserving full mainland wrap. A stale layer size now fails before writing. Epoch 36; checked offline, the reported terrain crack remains open pending engine appearance.

## 0.12.5 — 2026-10-25

- Rivers crossing the map seam now receive the starts and tributary markers required by each planar raster fragment. The continuous drainage, channel widths and carved valleys are retained; networks away from the seam keep their exact raster codes. This addresses TR46’s missing river-source errors without changing the continent shape or restoring a seam strait. Epoch 35; checked offline, engine rendering remains unobserved.

## 0.12.4 — 2026-10-25

- Replaced coastlines now include their offshore visual footprint. Height and material synthesis covers the old shelf beside removed islands, including across decal and map boundaries, while retaining Old World land. Water colour and foam are rebuilt where the changed coast affects their distance field and blur, even outside the replaced location colours. This addresses the remaining original-Alaska shelf rims near Chukotka reported in TR46. Location identities and land generation are unchanged. Epoch 34; checked offline, rendered result not yet observed in game.

## 0.12.3 — 2026-10-25

- Continent-scale noise now interpolates with 16-bit fractions. The former 8-bit fractions held the large-scale field flat for about 14 pixels, then jumped, producing long straight teeth on thresholded coasts. This fixes the field itself, including climate and relief that use the shared kernel; no post-generation coast smoothing. Epoch 33.
- Heightmap placements now continue periodically outside both horizontal map edges, in the terrain cache and instance files. The vanilla decal contract excludes a placement's upper endpoint, which left the world-edge sample and outside page halos without their opposite-side terrain. Original textures and interior placements are retained; no shader/engine change. Offline tests cover boundary/halo samples and unchanged interior coverage. The owner's 0.12.2 screenshot confirms a physical crack; the new placement's engine result is still unverified (C293–C295).

## 0.12.2 — 2026-10-25

- The New World can continue across the map edges as one continent. Removed the mandatory seam strait that had isolated the former-Alaska part near Japan, including its coast ramp and exclusion of drawn land. Terrain sampling and fine detail now continue across the wrap; water distance, foam blur and detail use horizontal wrapping, and roads cover contacts across the seam by the short route. Existing worlds retain their geography; newly generated worlds use epoch 32. Checked offline; the new seam terrain and road rendering have not been observed in game (C289–C290).

## 0.12.1 — 2026-10-25

- Seeded placement of the land-noise lattice removes fixed high-variance positions that favoured recurring island outlines in the narrow former-Alaska part of the canvas near Japan. One origin applies to the whole New World across the map wrap; there is no regional land quota or island deletion rule. A lobe may stay ocean or contain islands according to the seed. Existing worlds keep their maps; newly generated worlds use epoch 31 (C286–C287, checked offline).

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
