<div align="center">

<img src="packaging/assets/rnw-avatar.png" alt="Random New World" width="160">

# Random New World for Europa Universalis V

**A standalone procedural New World generator for EU5 — full-scale continents, physical geography, and native societies with an untouched vanilla Old World.**

[![check](https://github.com/Sir-Starch/eu5-random-new-world/actions/workflows/check.yml/badge.svg)](https://github.com/Sir-Starch/eu5-random-new-world/actions/workflows/check.yml)
[![License: MPL-2.0](https://img.shields.io/badge/license-MPL--2.0-brightgreen.svg)](LICENSE)
![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB.svg)
![Rust core](https://img.shields.io/badge/core-Rust-B7410E.svg)
![EU5 1.4.5](https://img.shields.io/badge/EU5-1.4.5-8B6F47.svg)
![Ironman & Achievements](https://img.shields.io/badge/Ironman%20%26%20Achievements-supported-success.svg)
![Version: 1.0.0](https://img.shields.io/badge/version-1.0.0-blue.svg)

</div>

---

**Random New World (RNW)** is a standalone desktop application (Python + Rust + Qt) that replaces the Americas with a procedurally generated landmass while keeping the Old World completely vanilla.

Each seed simulates elevation, climate zones, drainage basins, sea currents, resources, provinces, and native civilizations from scratch, compiling the result into a standard, self-contained EU5 map mod. Every world has a short shareable **World Code** and reproduces byte-for-byte on any machine running the same game build and generator version.

Installed RNW mods with a valid world code are detected automatically in the generator's library. Generated mods also embed recovery metadata for their atlas, preview images, and generation records, allowing library entries to be restored directly from the mod folder.

![Random New World procedural generation showcase](docs/images/showcase/rnw_showcase_full.gif)

> [!IMPORTANT]
> **Compatibility:** RNW 1.0.0 targets EU5 **1.4.5, Steam build 26211608**. Start a new campaign and keep its generated world mod. Exact regeneration needs the original algorithm and game inputs; updating the generator does not migrate saves.

Read [Known limitations](docs/known-limitations.md) before playing: supported game
build, save and mod compatibility, and what remains unverified in the current version.

## Features

| Layer | Capabilities |
|---|---|
| **Landmasses & Canvas** | Five archetypes (*Supercontinent*, *Continents*, *Small Continents*, *Archipelago*, *Scattered Islands*), plus **Random** and **Total Chaos** modes, coastline sketch previews, and custom hand-drawn outlines. Optional **+40% ocean expansion** (`53.2M px` canvas) claims surrounding ocean space beyond the vanilla Americas footprint. |
| **Physical Geography** | Unified elevation, climate, biome, terrain material, and vegetation simulation; drainage-driven river networks; vanilla-calibrated continental shelves and coastlines. |
| **Seas & Navigation** | Guaranteed natural harbors for coastal sea zones; shape-aware water naming (gulfs, straits, bays, capes); dynamic reshaping of vanilla oceans and impassable `ocean_wasteland` basins; continuous ocean currents, shipping lanes, and army strait crossings (`adjacencies.csv`). |
| **Political & Region Keys** | Compact, connected locations, provinces, areas, and regions. Vanilla American region and area keys are mapped to generated landmasses via global integer assignment based on climate, relief, and coastal similarity. |
| **Native Societies** | Procedural native cultures, religions, homelands, settled states, decentralized tribes, and subject networks. Optional **Extraordinary Peoples** spawns (*Great Empires*, *Sea Leagues*, *Highland Confederations*, *Fractured Realms*, and *Sacred Centres*) with balanced structural tradeoffs. |
| **Economy & Institutions** | Starting development, harbor capacity, market hubs, road spline networks, and tech levels derived organically from local society structure. |
| **Dynamic Content & L10n** | [Procedural regional stories, formable nations, rare resource deposits, and colonial naming](docs/content-catalog.md) (*New X*). Vanilla American historical triggers are cleanly gated or rebound. Full localization across all **11 official EU5 languages** (including script-native transliteration and grammar for RU, ZH, JA, KO, PL, DE). |
| **True Terra Incognita** | Spoiler-free by default: the New World remains masked in the generator preview, mod thumbnail, and EU5 country-selection map until you explicitly choose to reveal it. **Ironman and Achievements are fully supported.** |

Planned work includes deeper hydrology, more varied continental geography and societies, additional dynamic content, and a modern Tauri interface. See the [roadmap](docs/roadmap.md) for scope and status.

## Screenshots

### In game

<details>
<summary>Nine in-game screenshots — geography, native societies, oceans and dynamic content</summary>

Click a screenshot to view it at full size.

<table>
<tr>
<td colspan="2"><a href="docs/images/showcase/01-procedural-continents.png"><img src="docs/images/showcase/01-procedural-continents.png" alt="Full-Scale Procedural Continents — Simulated Relief, Climate &amp; Biomes"></a></td>
</tr>
<tr>
<td width="50%"><a href="docs/images/showcase/02-lobby-terra-incognita.png"><img src="docs/images/showcase/02-lobby-terra-incognita.png" alt="True Terra Incognita in the lobby (optional)"></a></td>
<td width="50%"><a href="docs/images/showcase/03-ocean-navigation.png"><img src="docs/images/showcase/03-ocean-navigation.png" alt="40% Expanded Canvas: Dynamic Sea Lanes, Currents &amp; Reshaped Ocean Wastelands"></a></td>
</tr>
<tr>
<td width="50%"><a href="docs/images/showcase/04-playable-native-societies.png"><img src="docs/images/showcase/04-playable-native-societies.png" alt="Playable Native Societies — With Full Ironman &amp; Achievement Support!"></a></td>
<td width="50%"><a href="docs/images/showcase/05-native-realms.png"><img src="docs/images/showcase/05-native-realms.png" alt="Procedural Native Realms, Tribes, Cultures &amp; Religions (1337 Start)"></a></td>
</tr>
<tr>
<td width="50%"><a href="docs/images/showcase/06-script-compatible-regions.png"><img src="docs/images/showcase/06-script-compatible-regions.png" alt="Vanilla region &amp; subcontinent keys dynamically remapped for full script compatibility"></a></td>
<td width="50%"><a href="docs/images/showcase/07-ai-colonization.png"><img src="docs/images/showcase/07-ai-colonization.png" alt="Full AI Colonization Support: New oceans won&#x27;t stop Europe from creating horrific borders by 1837+"></a></td>
</tr>
<tr>
<td width="50%"><a href="docs/images/showcase/08-east-colonization.png"><img src="docs/images/showcase/08-east-colonization.png" alt="East Meets West: Turn off the European-only colonization rule and watch Asian powers settle the New World from across the Pacific"></a></td>
<td width="50%"><a href="docs/images/showcase/09-dynamic-content.png"><img src="docs/images/showcase/09-dynamic-content.png" alt="Dynamic Content: Procedural colonial names, custom formable nations, and adapted historical &amp; regional events"></a></td>
</tr>
</table>

</details>

### Generator

The generator interface (native Qt controls) displaying generated worlds in the library, featuring **Supercontinent QUXQ** (`v0.13.17`) in its world overview and revealed atlas mapmodes.

<table>
<tr>
<td width="50%"><img src="docs/images/01-new-world.png" alt="New World setup page and world library"><br><sub>Select a landmass archetype and presets alongside your library of generated worlds.</sub></td>
<td width="50%"><img src="docs/images/02-customize.png" alt="Advanced customization sliders and World Code"><br><sub>Fine-tune generation parameters, enter a seed, or share a reproducible World Code.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/images/03-world-overview.png" alt="Spoiler-free world overview"><br><sub>By default, the New World stays hidden behind Terra Incognita to preserve exploration.</sub></td>
<td width="50%"><img src="docs/images/04-world-maps.png" alt="Revealed physical map in the built-in Atlas"><br><sub>Reveal the world to inspect physical geography and society summaries in the built-in Atlas.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/images/05-world-countries.png" alt="Political mapmode in the Atlas"><br><sub>Browse generated native states, tribes, and search for specific cultures or locations.</sub></td>
<td width="50%"><img src="docs/images/06-world-development.png" alt="Starting development mapmode"><br><sub>Inspect starting development, harbors, and economic layers alongside terrain.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/images/07-world-covered.png" alt="Covered Atlas view"><br><sub>The Atlas tab remains locked behind a spoiler guard until revealed.</sub></td>
<td width="50%"><img src="docs/images/08-world-religions.png" alt="Religions mapmode and legend"><br><sub>Generated religious families with dedicated map layers and interactive legends.</sub></td>
</tr>
</table>

*Europa Universalis V* is © Paradox Interactive AB. The Old World shown in these screenshots belongs to the base game; the New World is procedurally generated.

## How It Works

EU5 compiles its map topology, meshes, and splines during initial mod loading — runtime scripts cannot dynamically generate heightmaps, terrain materials, or river networks. **Random New World** runs as an external compiler that reads your local EU5 installation (read-only) and outputs a standard static map mod without modifying vanilla files or hooking into the game binary.

```mermaid
flowchart LR
    G[("EU5 Installation<br/>(read-only)")] --> R["Verify & fingerprint<br/>map contract"]
    C(["World Code<br/>archetype + seed + params"]) --> W
    R --> W["Compile New World<br/>Python + Rust core"]
    W --> V{"Strict Validators<br/>(fail-fast)"}
    V --> M[/"Standalone Mod<br/>mod/rnw_exp_world_…"/]
    M --> P(("Play 1337 Campaign<br/>(Ironman & Achievements OK)"))

```

* **Untouched Old World:** Every pixel, province key, and adjacency outside the New World canvas is verified against the vanilla installation baseline.
* **Bit-for-Byte Deterministic:** Frozen releases with the same algorithm epoch, resolved settings, seed and game inputs produce identical world files across operating systems and CPU thread counts (excluding presentation metadata). Synthetic digests are checked in CI; the full game-derived reference is verified locally.
* **Fail-Fast Invariants:** Unverified game builds, unhandled vanilla script references, or broken map invariants halt compilation immediately — never emitting silently corrupted mods.
* **Native Rust Core:** Compute-heavy kernels (simplex/domain-warped noise, distance fields, drainage routing, terrain slot assignment, LZAV compression) are written in Rust and verified bit-identical against Python reference implementations in [`tests/reference/`](tests/reference/).

For deep dives into the engineering, see [Architecture](docs/architecture.md), [ADR 0009 (Hub Mod Delivery)](docs/adr/0009-hub-mod-with-generator.md), and [ADR 0010 (Layered Reproducible Worlds)](docs/adr/0010-layered-worlds-and-a-generator-of-its-own.md).

## Getting Started

### For Players (Standalone Binary / Steam Workshop)

No Python or Rust installation is required for the [released packages](https://github.com/Sir-Starch/eu5-random-new-world/releases/latest):

1. Subscribe to [**Random New World** on the Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3829217331) (or download the standalone archive from [GitHub Releases](https://github.com/Sir-Starch/eu5-random-new-world/releases) — release archives include SHA-256 checksums).
2. In the EU5 **Mods** menu, locate *Random New World*, click **Open in folder**, and launch **Random New World Generator** (works on Windows and on Linux/Steam Deck via Proton).
3. Pick an archetype (or paste a friend's **World Code**) and click **Generate** (usually a few minutes; allow about 7.5 GB of free RAM).
4. Enable the newly created world mod (e.g., *RNW: Small continents 7K3Q*) in your playset — **only one RNW world mod at a time** — and start a new 1337 campaign. *(Do not enable the generator hub item itself in your playset).*

> [!NOTE]
> **Windows:** the generator is unsigned. Smart App Control may block it. No administrator access is required. See [known limitations](docs/known-limitations.md) for platform testing and trust limits.
>
> **Switching between RNW maps:** If you have already loaded into a campaign during your current game session, restart EU5 before starting a campaign on a different RNW map. Reloading map overhauls within the same process has caused mixed map data and a crash.

---

### Build & Run from Source

#### Requirements

* **Europa Universalis V (`1.4.5`, verified Steam build 26211608)** installed via Steam (Windows or Linux/Proton). Across the Pillars is optional.
* **Python 3.12+** and **[uv](https://docs.astral.sh/uv/)**.
* Stable **Rust** toolchain ([rustup](https://rustup.rs/)) to compile the native extension.
* **~7.5 GB of free RAM** during world compilation.

#### Launch the GUI

```sh
git clone https://github.com/Sir-Starch/eu5-random-new-world.git
cd eu5-random-new-world
uv sync --locked --group dev     # compiles the Rust core extension automatically
uv run rnw gui                   # launches the Qt desktop application

```

The application detects your EU5 installation and user profile automatically (custom paths can be configured in *Settings*).

#### Command-Line Interface (CLI)

```sh
uv run rnw find-game                                       # detect EU5 installations and profiles (read-only)
uv run rnw world-code --preset small_continents --seed 42  # generate and print a shareable World Code
uv run rnw world CODE --install                            # compile a world from a code and install to EU5
uv run rnw worlds                                          # list locally generated worlds
uv run rnw --help                                          # view all CLI commands and flags

```

See the [Generator Guide](docs/generator-guide.md) for details on `.rnworld` world files, political/resource rerolls, batch queues, and the built-in Atlas.

## Documentation

The [Documentation Index](docs/README.md) provides a full map of the repository:

* **User Guides:** [Known limitations](docs/known-limitations.md) · [Generator Guide](docs/generator-guide.md) · [Dynamic Content Catalogue](docs/content-catalog.md) · [Complete Event Reference](docs/content-reference.md) · [Product Specification](docs/product-spec.md) · [Localization](docs/localization.md)
* **System Design:** [Architecture](docs/architecture.md) · [Terrain & Biomes](docs/terrain-biomes.md) · [Sea Geography](docs/sea-geography.md) · [Native Societies](docs/natives.md) · [Economy](docs/economy.md) · [Content Plan](docs/content-plan.md) · [Architecture Decision Records (ADRs)](docs/adr/)
* **Project Tracking:** [Roadmap](docs/roadmap.md) · [Changelog](CHANGELOG.md) · [In-Game Experiments](experiments/README.md)
* **Verification & Audits:** [Engine Findings](docs/research/findings.md) · [Claims Ledger](docs/research/claims-ledger.md) · [Interoperability Register](docs/research/interoperability.md)

## Development & Verification

```sh
uv sync --locked --group dev
make check        # runs ruff (format + lint), basedpyright, pytest, and cargo (fmt, clippy, test)

```

CI executes the full verification suite across Linux and Windows using synthetic fixtures (no game installation required). When an EU5 installation is present locally, run read-only contract verification against the live game files:

```sh
EU5_GAME_DIR=/path/to/eu5 uv run pytest -q tests/test_local_install.py

```

| Directory | Contents |
| --- | --- |
| [`src/rnw/`](src/rnw/) | Core generator pipeline: world model, physical geography, seas, societies, content, EU5 exporters, validators, CLI |
| [`src/rnw/app/`](src/rnw/app/), [`src/rnw/gui/`](src/rnw/gui/) | Headless application controller and Qt desktop interface |
| [`native/`](native/) | Rust crate powering `rnw._native` hot kernels |
| [`packaging/`](packaging/) | Standalone binary builders, Workshop staging, release automation, third-party notices |
| [`tests/`](tests/) | Automated test suite, Python reference kernels, and golden world digests |
| [`docs/`](docs/), [`experiments/`](experiments/) | Technical specifications, ADRs, verification ledgers, and in-game experiment logs |

## Contributing

Contributions, bug reports, and pull requests are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR.

* **Strict clean-room rule:** Never commit proprietary game files or data extracted from an EU5 installation into this repository.
* **Architectural invariants:** See [AGENTS.md](AGENTS.md) for engineering rules, verification evidence labels (`[V-EXEC]`, `[V-GAME]`), and coding guidelines.

## License & Legal

**Random New World Generator** is an independent, third-party open-source software application licensed under the **[Mozilla Public License 2.0 (MPL-2.0)](LICENSE)**. Anyone is welcome to inspect the source code, submit pull requests, or build upon the project on GitHub, provided that all MPL-2.0 license terms, copyright notices, and source-code disclosure requirements are strictly respected. Bundled third-party libraries retain their respective licenses ([`THIRD_PARTY_NOTICES.md`](packaging/THIRD_PARTY_NOTICES.md)).

* **No Game Assets Included:** This repository contains zero proprietary files from *Europa Universalis V*. Generated map mods are compiled locally on the user's machine from their own legitimate copy of the game; generated mod output is subject to [Paradox Interactive's EULA](https://legal.paradoxplaza.com/eula) (see [Legal Notes](docs/legal.md)).
* **Redistribution:** The generator may be redistributed under MPL-2.0, retaining its licence and notices and providing the covered source as required. Generated world mods contain game-derived data and are for local use, not public upload. Workshop distribution also remains subject to the platform and game terms.
* **Security:** To report a security issue, please follow [SECURITY.md](SECURITY.md).

*Europa Universalis* and *Paradox Interactive* are registered trademarks of Paradox Interactive AB. This project is **not affiliated with or endorsed by Paradox Interactive**.
