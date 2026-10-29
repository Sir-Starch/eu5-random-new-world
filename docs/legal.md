# Distribution and licences

The owner has reviewed the publication rules and accepted the released RNW 1.0.0
hub (C437). The unchanged distribution does not require another general legal
review or a guarantee covering every hypothetical interpretation. The factual
boundaries below are the working policy; review a new dependency, asset, copying
requirement or distribution route when it actually changes them.

## What is distributed

- The generator, our original code/assets and their source, plus licensed Python,
  Qt and other runtime dependencies with their notices and licences.
- The Workshop hub contains the application only. A built world is generated
  from the player's lawful local EU5 installation and stays local. Public packages
  exclude game files, derived map rasters, shaders copied from the installation,
  generated worlds, logs and saves. Archive audits enforce this boundary.
- Compact world files carry the generator's record, atlas, names, settings and
  original previews, not the built game-derived mod. A built-mod transfer is a
  separate local/personal-machine function with explicit compatibility checks
  ([ADR 0010](adr/0010-layered-worlds-and-a-generator-of-its-own.md)).
- The owner approved publication of generator screenshots and in-game screenshots
  of generated worlds on 2026-10-24/26. This does not authorize distributing the
  game's underlying rasters, textures or models. The project is unofficial and
  attributes Europa Universalis V to Paradox.

The downloaded Workshop hub was compared with the prepared upload on 2026-10-29:
all 3,272 file hashes matched, with no world/library files (C441). The player's
existing application library is outside that package.

## Project and dependency licences

Project code is **MPL-2.0** (`LICENSE`, `pyproject.toml`, `native/Cargo.toml`).
Original later-added art and prose use CC BY 4.0. Redistribution of MPL-covered
files preserves their notices and makes their corresponding source available;
the MPL permits a larger work with separately licensed components. There is no
blanket ban on compliant generator redistribution. New contributors sign the
Developer Certificate of Origin.

`packaging/THIRD_PARTY_NOTICES.md`, generated dependency metadata and `licenses/`
travel with the application. Python uses the PSF licence; NumPy/Pillow and other
wheels retain their own licences. Qt/PySide6 uses LGPL-3.0: keep its replaceable
libraries, licence text and source information. PyInstaller's exception applies
to its development/native packaging route. Rust dependency licences are recorded
in the wheel SBOM. Do not relicense third-party or Paradox content as project work.

The candidate Tauri window (ADR 0011, not yet distributed) adds Tauri 2 and its plugins
(MIT/Apache-2.0), Svelte (MIT) and bundled Inter, Fraunces and JetBrains Mono fonts (SIL OFL
1.1). Before it ships, its package must carry these notices, the `Cargo.lock`/`package-lock.json`
dependency licences and the OFL text; the platform web views (WebView2, WebKitGTK) are system
components, not redistributed by the window.

## Reviewed platform terms

The reviewed sources are the [Paradox User Agreement](https://legal.paradoxplaza.com/eula?locale=en)
(2026-01-21 update, §5), [Steam Subscriber Agreement](https://store.steampowered.com/subscriber_agreement/)
(2026-09-10 revision, §6), [Workshop submission information](https://steamcommunity.com/workshop/workshopsubmitinfo/)
and [Mozilla's MPL FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/).
The publication review was performed on 2026-10-28/29 and accepted by the owner
(C437). It covers the free generator/runtime/original-assets distribution.

C267 preserves limits of the source interpretation and questions about other
scopes, especially redistribution of game-derived worlds. It identifies no
prohibited file in the audited hub and imposes no additional sign-off on that
unchanged package. A newly identified specific conflict should be investigated
on its facts. Account agreement acceptance and upload are performed through the
owner's explicitly authorized account actions; this document does not perform them.

## Research records

The [interoperability register](research/interoperability.md) records each touched
closed EU5 format and written binary: purpose, studied structure, source basis
and compatibility without shipping Paradox resources. Extend its relevant entry
when a task changes that work. Do not redo unrelated legal research each session.
External code needs a pinned source and a compatible licence before reuse.

The [distribution review history](archive/distribution-review-history.md) retains
the original licence choice, source checks, screenshot decisions and interpretive
questions. It is risk-analysis history, not a legal opinion or an extra release
checklist. Current source/licence audits are part of [release process](release-process.md).
