<div align="center">

<img src="packaging/assets/rnw-avatar.png" alt="Random New World" width="160">

# Random New World for Europa Universalis V

**A generator that replaces the Americas with a procedurally generated New World and leaves the Old World as Paradox made it.**

[![check](https://github.com/Sir-Starch/eu5-random-new-world/actions/workflows/check.yml/badge.svg)](https://github.com/Sir-Starch/eu5-random-new-world/actions/workflows/check.yml)
[![Licence: MPL-2.0](https://img.shields.io/badge/licence-MPL--2.0-brightgreen.svg)](LICENSE)
![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB.svg)
![Rust core](https://img.shields.io/badge/core-Rust-B7410E.svg)
![EU5 1.4](https://img.shields.io/badge/EU5-1.4.x-8B6F47.svg)
![Status: pre-release](https://img.shields.io/badge/status-pre--release%200.x-orange.svg)

</div>

---

Each seed produces new continents, coastlines, relief, climate, rivers, seas, resources, provinces and native civilisations. The generator writes them as an ordinary EU5 mod. Every world is a self-contained map mod, has a short **world code**, and can be rebuilt byte for byte from that code with the same game version.

![A generated New World beside the preserved Old World in Europa Universalis V](docs/images/showcase/00-world-overview.png)

Installed RNW worlds with a readable world code appear in the generator's library automatically. New worlds carry recovery data for their atlas, pictures and generation record, so their library entry can be restored from the mod itself.

> [!IMPORTANT]
> **Pre-release (0.x).** No public release or Workshop item exists yet. The maintainer has played much of the generated New World in game; see [`CHANGELOG.md`](CHANGELOG.md) and the [experiment records](experiments/). Expect breaking changes until 1.0.0, the first Steam Workshop publication ([ADR 0003](docs/adr/0003-versioning.md)).

## Features

| Layer | What the generator makes |
|---|---|
| **Land** | Five world types (supercontinent, continents, small continents, archipelago, scattered islands), with Random (one of them, drawn) and Total Chaos (a drawn type and every advanced value drawn), coastlines that follow the seed, an optional land outline you draw yourself; recommended ocean expansion gives continents room beyond the familiar outline of the Americas |
| **Physical world** | Relief, climate, biomes, terrain materials and vegetation from one model; rivers from drainage; vanilla-calibrated coast and shelf profiles |
| **Seas** | One port for every coastal sea zone; names taken from the water's shape (gulfs, straits, capes, island waters); depth and topography; ocean lanes and currents that continue the game's own; strait crossings armies can use |
| **Political map** | Compact, connected locations, provinces, areas and regions. The original American region and area keys are matched to the generated ones by physical similarity |
| **Peoples** | Native cultures and religions with homelands, states, tribes and vassals; rare great empires, sea leagues, highland confederations, fractured realms and sacred centres, each with causes and weaknesses |
| **Economy** | Start development, harbours, market villages and technology levels derived from each society |
| **Content** | Stories and formable countries planned from the finished world; colonial names built from each region's generated name; the historical American content is rebound, neutralised or replaced decision by decision |
| **Before you play** | The New World stays terra incognita in the generator, in the game's mod list and at country selection until you choose to see it |

## Screenshots

### In game

<details>
<summary>Eight in-game screenshots — geography, native societies, oceans and dynamic content</summary>

Click a screenshot to view it at full size.

<table>
<tr>
<td width="50%"><a href="docs/images/showcase/01-procedural-continents.png"><img src="docs/images/showcase/01-procedural-continents.png" alt="Full-Scale Procedural Continents — Simulated Relief, Climate &amp; Biomes"></a></td>
<td width="50%"><a href="docs/images/showcase/02-lobby-terra-incognita.png"><img src="docs/images/showcase/02-lobby-terra-incognita.png" alt="True Terra Incognita in the lobby (optional)"></a></td>
</tr>
<tr>
<td width="50%"><a href="docs/images/showcase/03-ocean-navigation.png"><img src="docs/images/showcase/03-ocean-navigation.png" alt="40% Expanded Canvas: Dynamic Sea Lanes, Currents &amp; Reshaped Ocean Wastelands"></a></td>
<td width="50%"><a href="docs/images/showcase/04-playable-native-societies.png"><img src="docs/images/showcase/04-playable-native-societies.png" alt="Playable Native Societies — With Full Ironman &amp; Achievement Support!"></a></td>
</tr>
<tr>
<td width="50%"><a href="docs/images/showcase/05-native-realms.png"><img src="docs/images/showcase/05-native-realms.png" alt="Procedural Native Realms, Tribes, Cultures &amp; Religions (1337 Start)"></a></td>
<td width="50%"><a href="docs/images/showcase/06-script-compatible-regions.png"><img src="docs/images/showcase/06-script-compatible-regions.png" alt="Vanilla region &amp; subcontinent keys dynamically remapped for full script compatibility"></a></td>
</tr>
<tr>
<td width="50%"><a href="docs/images/showcase/07-ai-colonization.png"><img src="docs/images/showcase/07-ai-colonization.png" alt="Full AI Colonization Support: New oceans won&#x27;t stop Europe from creating horrific borders by 1837+"></a></td>
<td width="50%"><a href="docs/images/showcase/08-dynamic-content.png"><img src="docs/images/showcase/08-dynamic-content.png" alt="Dynamic Content: Procedural colonial names, custom formable nations, and adapted historical &amp; regional events"></a></td>
</tr>
</table>

</details>

### Generator

The current generator window (Qt, the platform's own controls) with the owner's generated worlds in the library. Supercontinent EVXP is the featured world throughout the overview and map views. The screenshots show the current 0.13.4 interface, including its covered view and the maps available after revealing the world.

<table>
<tr>
<td width="50%"><img src="docs/images/01-new-world.png" alt="The current new-world page beside a library of generated worlds"><br><sub>Choose a world type and broad settings; Supercontinent EVXP and other generated worlds stay in the library.</sub></td>
<td width="50%"><img src="docs/images/02-customize.png" alt="Advanced world settings with a seed and reproducible world code"><br><sub>Set a seed, copy a world code, or adjust exact values.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/images/03-world-overview.png" alt="Supercontinent EVXP's overview with its covered New World preview"><br><sub>Supercontinent EVXP's overview keeps its New World covered by default.</sub></td>
<td width="50%"><img src="docs/images/04-world-maps.png" alt="The generated land layer for Supercontinent EVXP"><br><sub>Reveal the world to inspect its geography and the summary of its peoples.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/images/05-world-countries.png" alt="Countries in Supercontinent EVXP on the generated map"><br><sub>See Supercontinent EVXP's countries and search for peoples and places.</sub></td>
<td width="50%"><img src="docs/images/06-world-development.png" alt="Start development in Supercontinent EVXP"><br><sub>Inspect start development and other map layers alongside terrain.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/images/07-world-covered.png" alt="Supercontinent EVXP's map stays covered until the player reveals it"><br><sub>The world stays covered in the Maps tab until you choose to reveal it.</sub></td>
<td width="50%"><img src="docs/images/08-world-religions.png" alt="Religions in Supercontinent EVXP shown on the map"><br><sub>Religions have their own map layer and legend.</sub></td>
</tr>
</table>

*Europa Universalis V* is © Paradox Interactive AB. The Old World in these pictures is the game's own map; the New World is generated. The screenshots illustrate this unofficial mod and generator.

## How it works

EU5 builds its map from files when it loads mods. A mod is data: it cannot run code, and script cannot create land, mountains or rivers. The generation therefore runs in a separate program that reads the player's own installation and writes a mod. The generator does not change or hook into the game.

```mermaid
flowchart LR
    G[("EU5 installation<br/>(read only)")] --> R["Read and fingerprint<br/>the map contract"]
    C(["World code<br/>preset + seed + settings"]) --> W
    R --> W["Generate the New World<br/>Python + Rust core"]
    W --> V{"Validators<br/>fail loudly"}
    V --> M[/"World mod<br/>mod/rnw_exp_world_…"/]
    M --> P(("Play a new<br/>1337 campaign"))
```

- **Old World preserved.** Pixels, keys and contacts outside the New World canvas are checked against the installed game.
- **Deterministic.** The same code, generator version and game build give identical files on any machine, with any thread count. A reference world's digest is pinned in the test suite.
- **Fails loudly.** An unknown game build, an undecided vanilla script object or a broken invariant stops the export. No output is silently repaired.
- **Native core.** Hot kernels (noise, distance fields, drainage, terrain slots, LZAV) are in Rust and bit-identical to the Python reference implementations in [`tests/reference/`](tests/reference/).

See [architecture](docs/architecture.md), [ADR 0009](docs/adr/0009-hub-mod-with-generator.md) (delivery) and [ADR 0010](docs/adr/0010-layered-worlds-and-a-generator-of-its-own.md) (layered, reproducible worlds) for the design.

## Getting started

### Requirements

- **Europa Universalis V 1.4.x**, installed through Steam (Windows, or Linux through Proton). The generator checks the installed build and refuses one it has not been verified against.
- **Python 3.12+** and [**uv**](https://docs.astral.sh/uv/).
- A stable **Rust** toolchain ([rustup](https://rustup.rs/)) to build the native core.
- About **7.5 GB of free memory** while a world is generated, which takes a few minutes.

### Run from source

```sh
git clone https://github.com/Sir-Starch/eu5-random-new-world.git
cd eu5-random-new-world
uv sync --locked --group dev     # builds the Rust extension as part of the package
uv run rnw gui                   # the generator's window
```

The window finds EU5 and your profile on its own. Missing folders can be chosen under *Settings*. From the command line:

```sh
uv run rnw find-game                                      # installations and profiles found (read only)
uv run rnw world-code --preset small_continents --seed 42 # print a world code
uv run rnw world CODE --install                           # build that world and add it to the game
uv run rnw worlds                                         # the worlds you have made
uv run rnw --help                                         # everything else
```

### Play a world

1. Generate a world. It appears in the game's mod list as **RNW: *type* *tag*** (for example *RNW: Small continents 7K3Q*).
2. In the EU5 launcher, enable that world in a playset, **one world at a time**.
3. Start a **new 1337 campaign**. If you have already played a campaign in this session, restart EU5 first: the engine crashes when a different world starts after a campaign in the same process.

The [generator guide](docs/generator-guide.md) covers world files, rerolls, queues and the atlas.

## Documentation

The [documentation index](docs/README.md) lists everything. The main entry points:

- **Using it:** [generator guide](docs/generator-guide.md), [product specification](docs/product-spec.md)
- **Design:** [architecture](docs/architecture.md), [natives](docs/natives.md), [economy](docs/economy.md), [sea geography](docs/sea-geography.md), [terrain and biomes](docs/terrain-biomes.md), [content plan](docs/content-plan.md), [decision records](docs/adr/)
- **Progress:** [roadmap](docs/roadmap.md), [changelog](CHANGELOG.md), [experiments](experiments/README.md)
- **Evidence:** [findings](docs/research/findings.md), [claims ledger](docs/research/claims-ledger.md), [interoperability register](docs/research/interoperability.md)

## Development

```sh
uv sync --locked --group dev
make check        # ruff format + lint, basedpyright, pytest, cargo fmt/clippy/test
```

CI runs the same checks on Linux and Windows. Tests use synthetic fixtures and need no game. With a local installation, `EU5_GAME_DIR=/path/to/game uv run pytest -q tests/test_local_install.py` adds read-only checks against it.

| Path | Contents |
|---|---|
| [`src/rnw/`](src/rnw/) | The generator: world model, geography, seas, peoples, content, EU5 exporters, validators, CLI |
| [`src/rnw/app/`](src/rnw/app/), [`src/rnw/gui/`](src/rnw/gui/) | Headless application core and the Qt window |
| [`native/`](native/) | Rust crate behind `rnw._native` |
| [`packaging/`](packaging/) | Application and Workshop-item builds, release tooling, third-party notices |
| [`tests/`](tests/) | Test suite, Python reference kernels, golden digests |
| [`docs/`](docs/), [`experiments/`](experiments/) | Design, decisions, evidence and in-game experiment records |

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) first. In particular, **never commit files from the game or anything derived from them.** [AGENTS.md](AGENTS.md) holds the project's working rules, which coding agents read too.

## Legal

*Europa Universalis* and *Paradox Interactive* are trademarks of Paradox Interactive AB. This project is **not affiliated with or endorsed by Paradox Interactive**.

This repository contains no game files. A generated world is built on your computer from your own copy of the game. It contains material derived from the game, is not covered by this project's licence, and is subject to [Paradox's user agreement](https://legal.paradoxplaza.com/eula). See [legal notes](docs/legal.md) for the reasoning and open questions.

The code and mod files are licensed under the [Mozilla Public License 2.0](LICENSE). Bundled third-party components keep their own licences ([notices](packaging/THIRD_PARTY_NOTICES.md)). To report a vulnerability, follow [SECURITY.md](SECURITY.md).
