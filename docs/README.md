# Documentation

RNW 1.0.0 is released and accepted for EU5 1.4.5 / Steam build 26211608
(epoch 59). Start with [AGENTS.md](../AGENTS.md) for working instructions and
[architecture](architecture.md) for current code. This index distinguishes current
guidance from the historical record; an old unchecked box is not a current task.

## Current guides

| Document | Purpose |
|---|---|
| [Generator guide](generator-guide.md) | Installation, window/CLI workflow, library, world files and recovery |
| [Known limitations](known-limitations.md) | Accepted compatibility, save, platform and gameplay limits |
| [Product specification](product-spec.md) | Shipping player journey and engineering requirements |
| [Architecture](architecture.md) | Current pipeline, module map and invariants |
| [Capability overview](feasibility.md) | Implemented T3 route and boundaries of the product |
| [Roadmap](roadmap.md) | Released scope and owner-requested future directions |
| [Testing](testing.md) | Appropriate offline checks, CI and bounded owner-only game observation |
| [Release process](release-process.md) | Version/tag/package/publication workflow and permanent hub identity |
| [Distribution and licences](legal.md) | Accepted distribution boundary, licences and when to review a real change |
| [Changelog](../CHANGELOG.md), [1.0.0 notes](releases/1.0.0.md) | Release history and player-facing release notes |

## Subsystem references

These pages combine implemented models with **dated** calibration and observations.
Use their stated build when interpreting numbers; current code owns actual settings,
formats and constants. Historical per-feature unknowns are not new release gates.

| Document | Contents |
|---|---|
| [Terrain and biomes](terrain-biomes.md) | Relief, climate, materials, vegetation and rivers |
| [Sea geography](sea-geography.md) | Ports, depth, lanes, currents and crossings |
| [Native societies](natives.md) | Peoples, identity zones, states, technology and extraordinary societies |
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

## Research and evidence

The [claims ledger](research/claims-ledger.md) and [research log](research/log.md)
preserve dates, builds, corrections and owner observations. They do not override
current instructions or turn uncertainty into a publication prohibition.

| Record | Scope |
|---|---|
| [Interoperability register](research/interoperability.md) | Closed formats and written binaries, with source/compatibility rationale |
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
