# Product specification: genuine Random New World

> Historical snapshot retained from before the 2026-10-29 documentation cleanup.
> Dated plans, checklists and uncertainties below describe their original context;
> current instructions are in [AGENTS.md](../../AGENTS.md) and the [documentation index](../README.md).

**Vision.** A normal historical Old World opens onto an unknown, procedurally generated New World. Each seed changes coastlines, islands, terrain, resources, routes and societies. Political reshuffling on vanilla geography is a fallback diagnostic, not the product. This is the target specification for 1.0.0; the [roadmap](../roadmap.md) tracks how much of it exists.

## Player journey

1. In the game, press Open in folder on Random New World and start its generator, which finds the game ([ADR 0009](../adr/0009-hub-mod-with-generator.md)). Choose a preset, a continent type or a few advanced controls; the seed is random unless one is entered or pasted, and it can be copied, saved and reused.
2. Inspect a preview showing land/sea, navigation, climate, resources and broad civilization distribution. Reroll without touching the active game profile.
3. Generate with visible progress; the generator validates the world and installs it in place as one local mod, the generated world. In the game's main menu the player ticks it once in the playset beside Random New World, applies the playset and starts a new 1337 campaign; a later world loads when the playset is applied again, without closing the game [V-GAME C88, C93]; a new game without that reload would mix two worlds [V-GAME C85]. Options applied at game start are game rules in the game's setup screen where the engine allows; whether the New World is shown before it is played (the generator's pictures, the mod-list picture and the cover at country selection) is one setting of the generator, hidden by default (C133).
4. Explore without a full New World reveal. Save the seed, settings and generator/build fingerprints for reproducibility.

## Controls and feasibility

“Tool” means controllable in a future standalone generator without asserting game acceptance; “engine pending” means the relevant mod override/playability test has not run. See [capability matrix](../feasibility.md).

| Control | Presets / range concept | Feasibility |
|---|---|---|
| Seed and preview/reroll | Explicit seed and preview | Tool feasible [INFERRED C14]; engine output pending |
| Continental layout, fragmentation and landmass size | Few large masses ↔ many smaller masses | T1.5/T2/T3 engine pending [UNKNOWN C13] |
| Archipelagos, islands, inland seas, straits | Low ↔ high, topology constrained | T1.5/T2/T3 engine pending [UNKNOWN C13] |
| Topography, climate and vegetation | Coherent distributions, optional volatility | T1 engine pending [V-LOCAL C08; UNKNOWN C13] |
| Resources and settlement opportunities | Scarce ↔ abundant, geographically conditioned | T1 and setup pending [V-LOCAL C08–C09] |
| Population density and urbanization | Sparse ↔ dense, with empty regions | T0/setup pending [V-LOCAL C09] |
| Number, scale and political fragmentation of societies | Few large ↔ many small | T0/T3 setup pending [V-LOCAL C09] |
| Economy, institutions and technology | Grounded variation with rare advanced clusters | T0/T3 setup pending [V-LOCAL C09] |
| Extraordinary-civilization frequency/intensity | Never, Seldom (default), Sometimes, Often: the chance per cultural hearth of a great native empire, after EU4's Fantasy Random New World [SOURCE C122] | Implemented as `natives.empire_permille` (0.9.15, C125, C126); gameplay pending |
| Historical plausibility ↔ alternative history | Grounded default, opt-in fantasy | Content design feasible; gameplay pending [UNKNOWN C13] |

Presets: **Historical-ish** (plausible, rare anomalies), **Unpredictable** (more geography and polity variation), **Chaotic** (high fragmentation and terrain variety), and **Legendary** (opt-in higher chance of extraordinary or fantasy societies). Exact numeric distributions require balance tests; no odds are invented here [UNKNOWN]. The default should be grounded, with extraordinary outcomes uncommon and fantasy disabled [INFERRED product decision].

## Civilizations

Generate empty wilderness, small decentralized societies, regional states and complex powers. Exceptional outcomes could be a continental empire, advanced maritime culture, commercial network or fractured successor realm. Their strength must come from populations, production, institutions, technology, infrastructure, geography and organization, with weaknesses such as logistical strain, factionalism or resource dependence [INFERRED product design]. Flat superpower modifiers are excluded. Exact EU5 mechanics and required files remain subject to T0/T3 validation [UNKNOWN C09,C13].

## Quality bars

- [OWNER 2026-10-19] Generated terrain must look deliberate at every zoom level: coherent biome regions, smooth ecotones, mountain chains, rivers and valleys; no pixel-scale patchwork or patch seams. Visual layers and gameplay templates must come from the same climate/biome model. See [terrain-biomes](../terrain-biomes.md).
- [OWNER 2026-10-23] The mod and the generator use exactly the game's official languages, everywhere. Text is written in English during development; everything a player sees is translated before 1.0.0 ([roadmap](../roadmap.md) L1).
- [INFERRED] Identical seed, settings, generator version and game-build fingerprint must produce byte-identical mod output on Windows and Linux; this remains a future acceptance test. The owner-run Windows smoke (C428) verifies launch, generation and installation, without a cross-platform digest comparison.
- [INFERRED] Geography must be connected as intended, with no orphan sea zones, broken coastlines or Old World pixel/identifier changes. Ship and land route behavior must be observed in game before release.
- [INFERRED] Every society needs coherent pops, ownership, culture, religion, economy and diplomacy. Exploration, colonization, trade and conquest must be tested in an actual campaign.
- [SOURCE C15] Distribution should use original assets and generator code; local generation from the player's installation is the conservative path for modified vanilla rasters.

EU4's officially advertised randomized discovery and indigenous/colonial play [SOURCE C16] are design inspirations. EU4 algorithm, settings and rarity are not established here; see [analysis](../research/eu4-rnw-analysis.md).
