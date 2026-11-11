# Documentation

RNW 1.2.1 (epoch 62) shipped on 2026-11-10 for official EU5 1.4.7 / Steam build 26377361,
the latest compatible game version; 1.1.0 (epoch 60) targeted EU5 1.4.6. The 1.4.8 test
branch with hourly ticks is not supported.
Continue each generated map's campaign on the exact EU5 version used to create it.
Start with [AGENTS.md](../AGENTS.md) for working instructions and
[architecture](architecture.md) for current code. This index distinguishes current
guidance from the historical record; an old unchecked box is not a current task.

The next major update is **1.2.0**, focused on simulated prehistory, starting
geopolitics and the depth, identity and diversity of societies. The
[roadmap](roadmap.md#next-major-update--120-history-and-geopolitics) records the
owner's direction; the accepted [1.2.0 plan](history-plan.md) holds its design,
phases and acceptance criteria. The roadmap also lists the
[Workshop-feedback fixes](roadmap.md#workshop-feedback-in-120) that ship with 1.2.0.

## Current guides

| Document | Purpose |
|---|---|
| [Generator guide](generator-guide.md) | Installation, window/CLI workflow, library, world files and recovery |
| [Player's guide website](../website/README.md) | `rnw.sirstarch.com` in every official language: sources, terms, build and hosting |
| [Known limitations](known-limitations.md) | Game/save compatibility, generation requirements and known visual issues |
| [Product specification](product-spec.md) | Shipping player journey and engineering requirements |
| [Architecture](architecture.md) | Current pipeline, module map and invariants |
| [Capability overview](feasibility.md) | Implemented T3 route and boundaries of the product |
| [Roadmap](roadmap.md) | Released scope and owner-requested future directions |
| [1.2.0 plan](history-plan.md) | Accepted design, decisions, phases and acceptance criteria for history and geopolitics |
| [Testing](testing.md) | Appropriate offline checks, CI and bounded owner-only game observation |
| [Release process](release-process.md) | Version/tag/package/publication workflow and permanent hub identity |
| [Distribution and licences](legal.md) | Accepted distribution boundary, licences and when to review a real change |
| [Changelog](../CHANGELOG.md), [1.2.0 candidate notes](releases/1.2.0.md), [1.1.0 notes](releases/1.1.0.md), [1.0.0 notes](releases/1.0.0.md) | Release history and player-facing release notes |

## Subsystem references

These pages combine implemented models with **dated** calibration and observations.
Use their stated build when interpreting numbers; current code owns actual settings,
formats and constants. Historical per-feature unknowns are not new release gates.

| Document | Contents |
|---|---|
| [Terrain and biomes](terrain-biomes.md) | Relief, climate, materials, vegetation and rivers |
| [Sea geography](sea-geography.md) | Ports, depth, lanes, currents and crossings |
| [Native societies](natives.md) | Peoples, identity zones, states, technology and extraordinary societies |
| [History core and export](history-core.md) | H2–H3 rounds and societies; H4 physical bootstrap, historical final start, localized artifacts and output verification |
| [Economy](economy.md) | Starting development, harbours, markets and agrarian support |
| [Content plan](content-plan.md) | Current content inventory/disposition and story/formable architecture |
| [Content catalogue](content-catalog.md) | Player stories, choices, formables and exceptional places |
| [Generated content reference](content-reference.md) | Exact definitions; maintained by `build_content_reference.py` |
| [Localization](localization.md) | Official-language discovery, catalogues, grammar and translation maintenance |
| [Generator window](gui-design.md) | The Tauri window's design and the classic Qt window's rules |
| [Workshop description](workshop-description.md) | Reviewed BBCode text in each official language |

## Decision records

Accepted decisions apply to their scope; a later decision supersedes conflicting
parts. ADR context and implementation-phase tables explain history, not a new
queue of work. The release-level version policy is ADR 0003.

| ADR | Current role |
|---|---|
| [0001](adr/0001-python-research-tooling.md) | Python research/validation tooling |
| [0002](adr/0002-d0-generator-stack.md) | Historical D0 diagnostic exporter; shipping T3 uses the current architecture |
| [0003](adr/0003-versioning.md) | Product releases, public compatibility contract and algorithm epochs |
| [0004](adr/0004-generator-application.md) | Superseded delivery proposal; final decision is 0009 |
| [0005](adr/0005-native-core.md) | Rust kernels and reference equality |
| [0006](adr/0006-machine-resources.md) | Resource-aware threads, bands and memory |
| [0007](adr/0007-application-window-and-packaging.md) | Qt window (now the classic fallback)/native development packaging; Windows delivery follows 0009 |
| [0008](adr/0008-workshop-worlds.md) | Superseded finite-world delivery proposal; final decision is 0009 |
| [0009](adr/0009-hub-mod-with-generator.md) | Current Workshop generator hub and independent app delivery |
| [0010](adr/0010-layered-worlds-and-a-generator-of-its-own.md) | Implemented layers, world files, reproducibility and installed-world recovery |
| [0011](adr/0011-tauri-window.md) | The Tauri window over a Python bridge, its delivery and the classic fallback |
| [0012](adr/0012-vanilla-geography.md) | Keeping the vanilla Americas and generating only their societies |
| [0013](adr/0013-experimental-features-and-epoch-choice.md) | The experimental-features box and the choice of an algorithm epoch (61 to the current one) |

## Research and evidence

The [claims ledger](research/claims-ledger.md) and [research log](research/log.md)
preserve dates, builds, corrections and owner observations. They do not override
current instructions or turn uncertainty into a publication prohibition.

| Record | Scope |
|---|---|
| [Interoperability register](research/interoperability.md) | Closed formats and written binaries, with source/compatibility rationale |
| [1.4.7 compatibility check](research/compatibility-1-4-7.md) | Installed build, full input delta, map contract and offline checks |
| [1.2.0 history calibration](research/history-120-calibration.md) | Development calibration, R6 held-out results, control sweeps, reference/portability and remaining acceptance scope |
| [History contracts](research/history-contracts.md) | Installed history contracts, baseline measurements and seed matrices |
| [1.4.6 compatibility check](research/compatibility-1-4-6.md) | Installed build, input delta and offline checks |
| [More Locations compatibility](research/more-locations-compatibility.md) | Potential map conflicts, load-order limits and generation-time integration; third-party payload and combined engine behavior unverified |
| [1.4.5 compatibility audit](research/compatibility-1-4-5.md) | Target-build fingerprints and DLC dispositions |
| [World-wrap dossier](research/map-wrap-dossier.md) | Authoritative seam investigation, accepted data policy and historical comparisons |
| [TR46 register](research/tr46-observer-audit.md), [log catalogue](research/tr46-log-catalog.md) | Dated campaign findings; attribution and later fixes must be read before treating an item as open |
| [TR46 expansion](research/tr46-native-expansion.md), [expeditions](research/tr46-expeditions.md), [AI](research/tr46-ai-diagnostics.md), [Tordesillas](research/tr46-tordesillas.md) | Detailed subsystem evidence from that campaign |
| [EVXP diagnostics](research/evxp-session-diagnostics.md), [0.13.20 observer audit](research/observer-01320-audit.md) | Later owner campaigns and diagnostic attribution |
| [N0–N4 audit](research/n0-n4-audit.md), [N5 matching](research/n5-region-keys.md), [canvas expansion](research/canvas-expansion.md) | Implementation-time investigations and comparisons |
| [Initial findings](research/findings.md), [installation inventory](research/game-install-inventory.md) | EU5 1.4.1 survey, retained as historical evidence |
| [Sources](research/sources.md), [EU4 analysis](research/eu4-rnw-analysis.md) | External references and their dates/target versions |
| [Experiments](../experiments/README.md), [installation history](../experiments/INSTALLED.md) | Original setups, observations and installation/removal records |
| [Design archive](archive/README.md) | Superseded proposals, completed implementation plans and pre-release checklists |
