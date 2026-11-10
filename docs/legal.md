# Distribution and licences

The owner has reviewed the publication rules and accepted the released RNW 1.0.0
hub (C437). The unchanged distribution does not require another general legal
review or a guarantee covering every hypothetical interpretation. The factual
boundaries below are the working policy; review a new dependency, asset, copying
requirement or distribution route when it actually changes them.

## What is distributed

- The generator, our original code/assets and their source, plus licensed Python,
  Qt and other runtime dependencies with their notices and licences.
- The outlines of four known lands for the land editor (`src/rnw/lands`, 6-12 KB each): the
  shape of a coast cut out of a map picture, with no name, drawing, colour or text of the map. The
  pictures and the recipes are named in `experiments/070-known-lands`; the owner decided on
  2026-11-10 that the shape of a coast is used as such.
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

The Tauri window (ADR 0011) ships in the hub and the native packages. It adds Tauri 2 and
its plugins (MIT/Apache-2.0), the crates it links (their licences, including BSL-1.0 and
MPL-2.0 ones, listed per crate), Svelte (MIT) and bundled Noto Sans and JetBrains Mono fonts
(SIL OFL 1.1). Packages carry `licenses/window/crates.txt` and `npm.txt` with every distinct
licence file of those crates and npm packages. The Windows window carries Microsoft's
`WebView2Loader.dll` 1.0.3800.47, byte-identical to the one in the Microsoft.Web.WebView2 SDK
package; that SDK's licence is BSD-3-Clause-style and its text travels as
`licenses/window/WebView2Loader.txt` [SOURCE nuget.org Microsoft.Web.WebView2 1.0.3800.47,
2026-10-30]. The web views themselves (the WebView2 runtime, WebKitGTK) are system
components and are not redistributed.

DOM regression tests use pinned Happy DOM 21.0.4 (MIT; npm metadata and local licence,
2026-11-08). It and its added transitive dependencies are development-only, locked with
integrity hashes, and excluded from the built interface and package notices.

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

## Build toolchain: Microsoft SDK and CRT (1.1.0)

The Windows window is built for `x86_64-pc-windows-msvc` with `cargo-xwin`, which fetches the
Microsoft Windows SDK and MSVC runtime libraries when the build runs, on the build machine only.
The packages contain only the compiled window program: no SDK, CRT or other Microsoft file is
redistributed, and the program imports only system DLLs (no Visual C++ redistributable is needed).
The fetched libraries are used under Microsoft's own licence terms, which this review has not
examined in their text. The owner confirmed on 2026-11-02 that no further written review is required
before publication, since no SDK or CRT file is redistributed.

## Player's guide website

`website/public` (`rnw.sirstarch.com`) carries original guide text and drawings (CC BY 4.0),
crops of the owner-approved screenshots in `docs/images/showcase`, frames of the generator's own
window, two crops of the owner's EU5 **Mods & DLCs** screenshot taken for the guide on 2026-11-04
(without the account name or other parts of the screen), and subsets of Cinzel,
Noto Sans, Noto Serif and Noto Serif CJK under the SIL OFL 1.1. Each subset keeps the font's
name records and `fonts/OFL.txt` lists the copyright notices; no font is sold or renamed. EU5's
interface is named by single words from the game's localisation, as the Workshop text does.
The site carries no game files, rasters or worlds, loads nothing from other hosts and sets no
cookies. fontTools (MIT) builds the subsets; it is a development tool and is not distributed.

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
