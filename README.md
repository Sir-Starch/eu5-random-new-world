<div align="center">

<img src="packaging/assets/rnw-avatar.png" alt="Random New World" width="160">

# Random New World for Europa Universalis V

**A standalone procedural New World generator for EU5 — full-scale continents, physical geography, and native societies with an untouched vanilla Old World.**

[![check](https://github.com/Sir-Starch/eu5-random-new-world/actions/workflows/check.yml/badge.svg)](https://github.com/Sir-Starch/eu5-random-new-world/actions/workflows/check.yml)
[![License: MPL-2.0](https://img.shields.io/badge/license-MPL--2.0-brightgreen.svg)](LICENSE)
![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB.svg)
![Rust core](https://img.shields.io/badge/core-Rust-B7410E.svg)
![EU5 1.4.*](https://img.shields.io/badge/EU5-1.4.%2A-8B6F47.svg)
![Ironman & Achievements](https://img.shields.io/badge/Ironman%20%26%20Achievements-supported-success.svg)
![Version: 1.1.0](https://img.shields.io/badge/version-1.1.0-blue.svg)

</div>

---

**Random New World (RNW)** is a standalone desktop application (Python + Rust, with a Tauri window) that replaces the Americas with a procedurally generated landmass while keeping the Old World completely vanilla.

Each seed simulates elevation, climate zones, drainage basins, sea currents, resources, provinces, and native civilizations from scratch, compiling the result into a standard, self-contained EU5 map mod. Every world has a short shareable **World Code** and reproduces byte-for-byte on any machine running the same game build and generator version.

Installed RNW mods with a valid world code are detected automatically in the generator's library. Generated mods also embed recovery metadata for their atlas, preview images, and generation records, allowing library entries to be restored directly from the mod folder.

![Random New World procedural generation showcase](docs/images/showcase/rnw_showcase_full.gif)

> [!IMPORTANT]
> **Compatibility:** RNW supports EU5 **1.4.***. New patches in the 1.4 branch are usually compatible without a generator update; the latest fully verified version is **1.4.7, Steam build 26377361**. Keep each generated map and its campaign on the exact EU5 version used to generate it, and keep its world mod. Updating the generator does not migrate saves.

Read [Known limitations](docs/known-limitations.md) before playing: supported game
build, save and mod compatibility, generation requirements and known visual issues.

## Features

| Layer | Capabilities |
|---|---|
| **Landmasses & Canvas** | Six archetypes (*Supercontinent*, *Continents*, *Small Continents*, *Archipelago*, *Scattered Islands*, *The Wall*), plus **Random** and **Total Chaos** modes, coastline sketch previews, and custom hand-drawn outlines. Optional **+65% ocean expansion** (`62.5M px` canvas) claims surrounding ocean space across the Pacific and Atlantic beyond the vanilla Americas footprint, while preserving or relocating enclosed island groups (Polynesia, Hawaii, Atlantic islets). |
| **Physical Geography** | Unified elevation, climate, biome, terrain material, and vegetation simulation; drainage-driven river networks, hydrologically integrated lakes, and branching mountain ranges with realistic relief and passes; vanilla-calibrated continental shelves and coastlines. |
| **Seas & Navigation** | Guaranteed natural harbors for coastal sea zones; shape-aware water naming (gulfs, straits, bays, capes); dynamic reshaping of vanilla oceans and impassable `ocean_wasteland` basins; continuous ocean currents, shipping lanes, and physical-shore army strait crossings (`adjacencies.csv`). |
| **Political & Region Keys** | Compact, connected locations, provinces, areas, and regions. Vanilla American region and area keys are mapped to generated landmasses via global integer assignment based on climate, relief, and coastal similarity. |
| **Native Societies & History** | 300-year causal prehistory simulation (1037–1337) shaping starting polities, regional power settings, starting alliances, subjects, and opinions. Conservative population migration, primary identity cores, and fine-grained controls for state land targets, historical turbulence, and peasant/tribesman balance. Optional **Extraordinary Peoples** spawns (*Great Empires*, *Sea Leagues*, *Highland Confederations*, *Fractured Realms*, and *Sacred Centres*) seeded as ambitious centres with prudent or overreaching strategies. |
| **Economy & Institutions** | Starting development matching EU5 exact rules (including river size weighting), valid initial laws and policies, harbor capacity, market hubs, road spline networks, and tech levels derived organically from local society structure. Individual 0–3× placement weights for all 34 ordinary New World RGOs alongside precious resources. |
| **Dynamic Content & L10n** | [Procedural regional stories, formable nations ladder with missions & cores, restorations of fallen realms, narrative Our History storytelling, rare resource deposits, and colonial naming](docs/content-catalog.md) (*New X*). Settle the Frontier enabled across all New World land countries. Full localization across all **11 official EU5 languages** (including script-native transliteration and grammar for RU, ZH, JA, KO, PL, DE). |
| **True Terra Incognita** | Spoiler-free by default: the New World remains masked in the generator preview, mod thumbnail, and EU5 country-selection map until you explicitly choose to reveal it. Optional multiplayer reveal at game start. **Ironman and Achievements are fully supported.** |

The **1.2.0** update introduces simulated prehistory, starting geopolitics, starting laws and diplomatic budgets, narrative Our History storytelling, regional formable nations with missions, and responsive generator workbench features. See the [1.2.0 candidate notes](docs/releases/1.2.0.md), the [roadmap](docs/roadmap.md) and the [1.2.0 plan](docs/history-plan.md) for full design and details.

## Screenshots

### In game

<details>
<summary>Twelve in-game screenshots — geography, native societies, oceans, dynamic content and history simulation</summary>

Click a screenshot to view it at full size.

<table>
<tr>
<td colspan="2"><a href="docs/images/showcase/01-procedural-continents.png"><img src="docs/images/showcase/01-procedural-continents.png" alt="Full-Scale Procedural Continents — Simulated Relief, Climate &amp; Biomes"></a></td>
</tr>
<tr>
<td width="50%"><a href="docs/images/showcase/02-lobby-terra-incognita.png"><img src="docs/images/showcase/02-lobby-terra-incognita.png" alt="True Terra Incognita in the lobby (optional)"></a></td>
<td width="50%"><a href="docs/images/showcase/03-ocean-navigation.png"><img src="docs/images/showcase/03-ocean-navigation.png" alt="65% Expanded Canvas: Dynamic Sea Lanes, Currents &amp; Reshaped Ocean Wastelands"></a></td>
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
<tr>
<td width="50%"><a href="docs/images/showcase/10-the-wall-returns.png"><img src="docs/images/showcase/10-the-wall-returns.png" alt="The Wall Returns: a continent-wide barrier across the New World"></a></td>
<td width="50%"><a href="docs/images/showcase/11-improved-gen.png"><img src="docs/images/showcase/11-improved-gen.png" alt="RNW 1.1.0: More realistic mountains, water bodies, and coastlines"></a></td>
</tr>
<tr>
<td colspan="2"><a href="docs/images/showcase/history-simulation.png"><img src="docs/images/showcase/history-simulation.png" alt="RNW 1.2.0: Overhauled societies &amp; geopolitics with 300-year history simulation"></a></td>
</tr>
</table>

</details>

### Generator

The Tauri generator window, with its world library, map canvas, generation queue and inspector. The examples include **Supercontinent 33XV**; the last image shows the classic Qt fallback.

<p align="center"><img src="docs/images/new-ui.png" alt="Generator window with the world library, the making queue and a comparison of two worlds" width="100%"></p>

<table>
<tr>
<td width="50%"><img src="docs/images/01-new-world.png" alt="New world with continent sketches"><br><sub>Choose a world type and preview continent sketches before generating a world.</sub></td>
<td width="50%"><img src="docs/images/02-customize.png" alt="Exact generation values in the Advanced inspector"><br><sub>Adjust individual values alongside the land preview, with the location budget always visible.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/images/03-world-covered.png" alt="Covered world in the library"><br><sub>Keep the New World hidden for exploration in the game, or reveal it in the generator.</sub></td>
<td width="50%"><img src="docs/images/04-world-physical.png" alt="Revealed physical map"><br><sub>Explore the physical map, with region names, relief, settlements and a minimap.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/images/05-world-countries.png" alt="Political map with states and optional tribes"><br><sub>Inspect generated states; show tribes separately when you want them.</sub></td>
<td width="50%"><img src="docs/images/06-world-resources.png" alt="Resource map at location scale"><br><sub>See each location’s resources up close and isolate a resource through the legend.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/images/07-world-location.png" alt="Culture map with a pinned location card"><br><sub>Inspect a location’s people, faith, resource and population from its map card.</sub></td>
<td width="50%"><img src="docs/images/08-classic-window.png" alt="Classic Qt fallback window"><br><sub>The classic Qt window remains available, including under Proton without WebView2.</sub></td>
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

For deep dives into the engineering, see [Architecture](docs/architecture.md), [ADR 0009 (Hub Mod Delivery)](docs/adr/0009-hub-mod-with-generator.md), [ADR 0010 (Layered Reproducible Worlds)](docs/adr/0010-layered-worlds-and-a-generator-of-its-own.md), and [ADR 0011 (Tauri Window)](docs/adr/0011-tauri-window.md).

## Getting Started

### For Players (Standalone Binary / Steam Workshop)

No Python or Rust installation is required for the [released packages](https://github.com/Sir-Starch/eu5-random-new-world/releases/latest):

1. Subscribe to [**Random New World** on the Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3829217331) (or download the standalone archive from [GitHub Releases](https://github.com/Sir-Starch/eu5-random-new-world/releases) — release archives include SHA-256 checksums).
2. In the EU5 **Mods** menu, locate *Random New World*, click **Open in folder**, and launch **Random New World Generator** (works on Windows and on Linux/Steam Deck via Proton).
3. Pick an archetype (or paste a friend's **World Code**) and click **Generate** (usually a few minutes; allow about 7.5 GB of free RAM).
4. Enable the newly created world mod (e.g., *RNW: Small continents 7K3Q*) in your playset — **only one RNW world mod at a time** — and start a new 1337 campaign. *(Do not enable the generator hub item itself in your playset).*

> [!TIP]
> **Ready-to-play worlds:** If you prefer to jump straight into a game without generating a world, pre-compiled standalone worlds like [The Wall — CWYS](https://steamcommunity.com/sharedfiles/filedetails/?id=3832180151) are available directly on the Steam Workshop. Subscribe, enable the world mod in your playset, and start playing immediately.

> [!NOTE]
> **Windows:** the generator is unsigned. Smart App Control may block it. No administrator access is required. See [known limitations](docs/known-limitations.md) for platform testing and trust limits.
>
> **Switching between RNW maps:** If you have already loaded into a campaign during your current game session, restart EU5 before starting a campaign on a different RNW map. Reloading map overhauls within the same process has caused mixed map data and a crash.

---

### Build & Run from Source

#### Requirements

* **Europa Universalis V (`1.4.*`, latest fully verified: 1.4.7 / Steam build 26377361)** installed via Steam (Windows or Linux/Proton). Across the Pillars is optional.
* **Python 3.12+** and **[uv](https://docs.astral.sh/uv/)**.
* Stable **Rust** toolchain ([rustup](https://rustup.rs/)) to compile the native extension.
* **Node.js 20+** (only needed when building the Tauri desktop window from source).
* **~7.5 GB of free RAM** during world compilation.

#### Launch the GUI

```sh
git clone https://github.com/Sir-Starch/eu5-random-new-world.git
cd eu5-random-new-world
uv sync --locked --group dev     # compiles the Rust core extension automatically
uv run rnw gui                   # opens the window (--classic: the Qt window)

```

The application detects your EU5 installation and user profile automatically (custom paths can be configured in *Settings*). To build the Tauri desktop window from source, run `make desktop` (requires Node.js and system WebKitGTK / WebView2 development packages). Without a local desktop build, `uv run rnw gui` opens the classic Qt window as a fallback.

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
| [`src/rnw/app/`](src/rnw/app/), [`src/rnw/gui/`](src/rnw/gui/) | Headless application controller, window choice, Tauri bridge and the classic Qt window |
| [`desktop/`](desktop/) | Tauri window shell and TypeScript/Svelte interface ([ADR 0011](docs/adr/0011-tauri-window.md)) |
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
