# Documentation

The project's documentation, grouped by purpose. Technical claims carry evidence labels (`[V-GAME]`, `[V-EXEC]`, …; see [CONTRIBUTING](../CONTRIBUTING.md#evidence-labels)) and `C###` numbers from the [claims ledger](research/claims-ledger.md).

## Using the generator

| Document | Contents |
|---|---|
| [Generator guide](generator-guide.md) | The window, world codes and files, rerolls, the queue, the command line |
| [Workshop description](workshop-description.md) | The player-facing Steam Workshop text for 1.0.0, in Steam's markup and every official language |

## Product and plan

| Document | Contents |
|---|---|
| [Product specification](product-spec.md) | Vision, the player's journey and the target feature set |
| [Roadmap](roadmap.md) | Phases, dependencies and acceptance gates |
| [Release process](release-process.md) | Internal gates and owner hand-off for GitHub and Workshop publication |
| [Content plan](content-plan.md) | The vanilla content tied to the Americas, decided object by object, and the stories and formables that replace it (N0–N5) |
| [Changelog](../CHANGELOG.md) | Progress release by release |

## Design

| Document | Contents |
|---|---|
| [Terrain and biomes](terrain-biomes.md) | Relief, climate, biomes, materials, vegetation and rivers (V1) |
| [Sea geography](sea-geography.md) | Ports, names, depth, lanes, currents and strait crossings (S1) |
| [Natives](natives.md) | Peoples, cultures, religions, states, technology and extraordinary societies (R6, R7) |
| [Economy](economy.md) | Start development, harbours and market villages (R7a) |
| [R7a design](r7a-development.md), [R7b and R7c design](r7-technology-and-empires.md) | Design notes written before those slices were implemented |
| [Localization](localization.md) | How EU5 writes its eleven languages, the rules for the mod's texts and names, the translation design and its status (L1) |
| [Generator window](gui-design.md) | Layout, spacing and interaction rules of the Qt window |
| [Architecture](architecture.md) | The architecture options as weighed at the start *(historical)* |

## Engineering

| Document | Contents |
|---|---|
| [Testing](testing.md) | Test suites, reproducibility and the in-game testing protocol |
| [Legal notes](legal.md) | Licence choice, Paradox's terms, distribution of generated worlds, dependencies |

## Decision records

| ADR | Decision | Status |
|---|---|---|
| [0001](adr/0001-python-research-tooling.md) | Python for the research and validation kit | Accepted |
| [0002](adr/0002-d0-generator-stack.md) | D0 generator stack and ID-preserving first exporter | Accepted (D0) |
| [0003](adr/0003-versioning.md) | One product version for the mod and its output | Accepted |
| [0004](adr/0004-generator-application.md) | The generator as a local application with a window | Superseded by 0008 |
| [0005](adr/0005-native-core.md) | A Rust core for the hot kernels | Accepted |
| [0006](adr/0006-machine-resources.md) | The export reads the machine and bounds its memory | Accepted |
| [0007](adr/0007-application-window-and-packaging.md) | Qt window, PyInstaller for development builds | On hold; window kept under 0009 |
| [0008](adr/0008-workshop-worlds.md) | Worlds as Workshop mods | Replaced by 0009 |
| [0009](adr/0009-hub-mod-with-generator.md) | One Workshop mod that carries the generator | Accepted |
| [0010](adr/0010-layered-worlds-and-a-generator-of-its-own.md) | Layered, reproducible worlds and a standalone generator | Accepted |

## Research and evidence

| Document | Contents |
|---|---|
| [Findings](research/findings.md) | What is known about EU5's map and mod loading |
| [Claims ledger](research/claims-ledger.md) | Every consequential claim with its evidence, game build and date |
| [Interoperability register](research/interoperability.md) | Each reverse-engineered EU5 format: why it is needed and how compatibility is kept without distributing Paradox's files |
| [Sources](research/sources.md) | External sources with dates and target versions |
| [Research log](research/log.md) | Chronological working log |
| [TR46 problem register](research/tr46-observer-audit.md), [log catalog](research/tr46-log-catalog.md) | Open issues from the long 0.12.3 observer campaign: all seven owner observations, evidence, investigation entry points and closure criteria; exhaustive session diagnostics |
| [TR46 native expansion](research/tr46-native-expansion.md) | Saved vanilla AI colonization rule, native conquest and consolidation, extraordinary societies' land/subjects, successors and frontier evidence limits |
| [TR46 expeditions](research/tr46-expeditions.md) | Corrected mining/Pacific counts, inherited no-travel and return-event gaps, anonymous calls and port/water assertion evidence limits |
| [Installation inventory](research/game-install-inventory.md) | Layout of the EU5 1.4.1 installation as first inspected |
| [N0–N4 audit](research/n0-n4-audit.md), [N5 region keys](research/n5-region-keys.md) | Offline audits of the content plan |
| [Canvas expansion](research/canvas-expansion.md) | Why large ocean locations constrain generation, and a proposed wider domain with preserved ocean names |
| [EU4 analysis](research/eu4-rnw-analysis.md) | What EU4's Random New World does and does not tell us |
| [Feasibility](feasibility.md) | The original ambition ladder (T0–T5) *(historical)* |

In-game experiments, each with its setup, result and removal, are in [`experiments/`](../experiments/README.md).
