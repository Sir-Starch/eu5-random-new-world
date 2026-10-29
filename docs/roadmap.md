# Roadmap

## Released baseline

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
| Generator (R8/U1/G0–G4) | Qt window, world library, atlas, codes/files, layer rerolls, queue, recovery and installation | [Guide](generator-guide.md), [GUI design](gui-design.md) |
| Runtime and delivery (R9/R10/G5/P1) | Rust kernels, bounded memory, Windows/Proton hub, native Linux application, tagged CI and public releases | [ADRs](README.md#decision-records), [release process](release-process.md) |

The phase codes remain useful identifiers in research records; they are not a
list of unfinished prerequisites. Detailed observations keep their original game
build and scope. Known limitations are in [one current page](known-limitations.md).
An unobserved detail alone does not reopen acceptance or require another game session.

## Future work requested by the owner

These are directions, not promises for 1.0.0 or automatic tasks for every agent.
Choose a concrete scope when work is requested; use the next release target and
pending epoch according to [ADR 0003](adr/0003-versioning.md).

- **Hydrology:** improve basins, drainage, tributaries and water bodies together
  with relief, climate, coastlines and navigation. Use measurable structural and
  visual comparisons on diverse seeds.
- **Continental variety:** develop more realistic lakes, inland seas, narrow land
  connections and coastal formations, including the Gdańsk/Crimea-like examples
  requested by the owner. Design their representation with hydrology and sea routes.
- **The Wall preset:** add a selectable landmass preset with a long, narrow
  north–south continental barrier inspired by the EU4 RNW scenario
  ([community suggestion](https://www.reddit.com/r/EU5/comments/1xia8uu/comment/19rtciacccl1h/)).
- **Ready-made fantasy maps:** add land-shape presets such as a Kerbin-inspired
  map within the New World generation area, using the existing land-mask workflow.
  Verify that workflow alongside the presets
  ([community suggestion](https://www.reddit.com/r/EU5/comments/1xia8uu/comment/19rtj2ndbo2gz/)).
- **Societies and dynamic content:** broaden state structures, relationships and
  context-sensitive stories through the existing R6/R7 and N0–N5 systems.
- **Optional Easter egg countries:** add country scenarios inspired by EU4 RNW
  Easter eggs, including Vinland, Secret Denmark and Atlantis
  ([community suggestion](https://www.reddit.com/r/EU5/comments/1xia8uu/comment/19rtdzylmh2mb/)).
- **Optional alternative-history settlements:** add an opt-in setting for
  historically inspired peoples and overseas settlements, including Norse/Vinland
  settlements, integrated into the generated societies
  ([community suggestion](https://www.reddit.com/r/EU5/comments/1xia8uu/comment/19rtcqs3rwjgi/),
  first added 2026-10-29).
- **Generated national histories:** generate coherent pre-1337 histories for
  generated states and use them to inform starting relationships and subsequent
  events, goals or mission-style content through the existing society/story systems
  ([community suggestion](https://www.reddit.com/r/EU5/comments/1xia8uu/comment/19rtkpx9hq1z9/)).
- **Generator interface and settings:** fully rework the interface and expose
  more generation settings as part of the planned Tauri migration, preserving
  generation, library, atlas, localization, accessibility and cancellation
  workflows. Qt remains current until an implemented replacement is accepted.
- **Resource distribution sliders:** add individual frequency controls for
  ordinary RGOs alongside the existing precious-resource control. Keep resource
  selection tied to climate and terrain, with vanilla weights as the defaults.
  Explain that the sliders change relative placement probabilities, so increasing
  one resource leaves fewer locations for others; they do not directly change
  production per location. These controls are planned for a future update.
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
