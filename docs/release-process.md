# Release process

This is the maintainer's checklist for the publication phase (P1). It describes the hand-off from a verified source tag to separately reviewed GitHub and Steam Workshop artifacts. It does not authorize or perform a push, GitHub release, Workshop upload, or account action.

## Release boundaries

- The project has one product version, read from `pyproject.toml`. Under [ADR 0003](adr/0003-versioning.md), ordinary main commits keep one target per release cycle and collect Unreleased notes. PATCH fixes, MINOR compatible new capabilities, MAJOR public-contract breaks. The first product release is 1.0.0 after acceptance; a target version is not a published release.
- A GitHub release carries the source and application packages for the same version ([roadmap P1](roadmap.md)). A Steam Workshop item carries the hub mod and generator ([ADR 0009](adr/0009-hub-mod-with-generator.md)). These are separate distributions with separate gates.
- Generated world mods are built locally from the player's EU5 installation. Do not attach a generated world, game files, or files derived from the game's data to a repository release or Workshop item ([legal notes](legal.md); [ADR 0009](adr/0009-hub-mod-with-generator.md); [INFERRED C15]).
- CI builds and audits candidate artifacts from a pinned commit or tag; it uploads artifacts but does not publish them ([V-EXEC C145]). Keep CI implementation and its run evidence in the workflow and CI records.

## Before tagging 1.0.0

Complete each gate and retain its evidence before making a stable release tag.
Build pre-tag candidates by full commit SHA as described below, so a failed
candidate can be fixed without consuming the 1.0.0 version.

- [x] **Product acceptance:** the owner confirms that the mod is ready and tested (2026-10-29, C437). Earlier roadmap experiment statuses retain their original evidence scope; they do not reopen release acceptance.
- [x] **Game compatibility:** the accepted release targets EU5 1.4.5 / Steam build 26211608, with the recorded owner sessions, installed-build audit and offline regressions (C425–C429, C431, C437). Future patches require their own compatibility check; metadata alone proves no future compatibility.
- [x] **Languages:** run the L1 release check against every official language shipped by the target game build. Every player-visible string has a translation, and each translation is current against its English source ([roadmap L1](roadmap.md)).
- [x] **Terms and file audit:** the owner confirms that the rules have been studied (2026-10-29, C437). The audited distribution contains the generator, runtime, original assets and required notices/licences. Game-derived worlds remain local. C267 records interpretive limits of the source review, not an outstanding release prohibition ([legal notes](legal.md)).
- [x] **Windows and Workshop preparation:** owner-run Windows 11 smoke (C428), CI package self-tests, archive audits and exact launcher/native VirusTotal reports pass. Unsigned Windows binaries are an accepted, disclosed limitation. Workshop upload and checking the downloaded item are publication steps performed by the owner, not tests that must somehow finish before the first upload.
- [x] **Player text:** prepare release notes from the changelog. Keep the README as product documentation, not release notes. Remove internal bracketed notes from the [Workshop description](workshop-description.md), and verify every feature, game-build, installation, removal, warning, and support statement against the candidate.
- [x] **Images:** the screenshots of the generator's window in `docs/images/` may be published (owner, 2026-10-24; [legal notes](legal.md)). Take them again on a demo library, with the platform's plain light style and without paths or hardware of the machine, whenever the window changes. Game files, textures and rasters stay out; any upload to the Workshop is an owner action (P1 in the [roadmap](roadmap.md)).
- [x] **Version and reproducibility:** check `pyproject.toml`, `uv.lock`, generated mod metadata and run records use the same version. Choose the version from the whole release relative to the previous stable release, not per commit. Update output goldens when needed; if a world's mod changes outside `.metadata`, freeze the cycle's pending algorithm epoch and final reference world. Do not rewrite frozen epochs ([ADR 0003](adr/0003-versioning.md); [ADR 0010](adr/0010-layered-worlds-and-a-generator-of-its-own.md)).

## Candidate artifact gate

Build pre-tag artifacts with `workflow_dispatch`: `tag` is the intended numeric target (for example `v1.0.0`) and `commit` is the full candidate SHA. The tag need not exist yet. With `commit` empty, the workflow requires the actual tag; tag pushes use this mode too. Both paths validate the package version and clean exact checkout, run `make check`, and pass the resolved SHA to both builders. Fix a failed pre-tag candidate at a new SHA under the same target. After acceptance, tag exactly the reviewed commit and verify the tagged build before publication. Keep stable tags immutable. For that candidate, verify:

- [x] CI is green on the release commit for the required Linux and Windows checks (P1). A run on another commit is not evidence for this candidate.
- [x] The release workflow's tag check matches `pyproject.toml`; package self-tests and archive audits pass ([release workflow](../.github/workflows/release.yml), [`packaging/release.py`](../packaging/release.py)).
- [x] The source archive and every platform archive are present, and the published SHA-256 files cover every archive being handed off. Verify each checksum against the downloaded candidate files.
- [x] The candidate contains the correct third-party notices and no game assets, generated-world files, local logs, saves, or unapproved screenshots. Approved documentation images may travel with the source archive.
- [x] Keep the workflow artifacts as a candidate until the maintainer accepts them. The workflow uploads build artifacts for review; it does not create a GitHub release or publish to the Workshop.

## GitHub release hand-off

The maintainer performs the external publication after accepting the candidate:

- [ ] Create the GitHub release for the reviewed version tag and attach the matching source archive, application archives, checksum files and `BUILD-INFO.json` release manifest.
- [ ] Use the prepared release notes and link to the source tag. Do not add generated worlds or derived game files.
- [ ] Download the posted assets once and recheck their checksums against the candidate.

## Steam Workshop hand-off

The prepared Workshop item is published by the owner:

- [ ] Upload only the hub mod and generator package. Never upload a generated world or a package containing derived vanilla map data.
- [ ] Use the reviewed Workshop description (`docs/workshop/<language>.bbcode`, one per language, pasted without its first `source:` line), preview image, and approved screenshots. Remove every editorial bracketed note before upload.
- [ ] Confirm the item is free, the required dependency notices travel with it, and the installation/removal instructions match the published build.
- [ ] Verify the Workshop page and downloaded item after publication. Record the item identifier and exact product/game versions in the project notes.

## Current readiness

Preparation date: **2026-10-29**. **RNW 1.0.0 / epoch 59** is ready for
publication for **EU5 1.4.5 / Steam build 26211608**, including Across the
Pillars adaptation. The owner confirms that the mod is ready, tested and the
rules have already been studied (C437). Preparation and acceptance are complete;
the tag, release creation and Workshop upload are the remaining publication actions.
Earlier per-experiment UNKNOWN/NOT-RUN entries remain historical evidence limits.
They are not automatically additional release gates, and no new game test is
claimed or requested by this acceptance record.

| Area | Evidence and remaining boundary |
|---|---|
| Product and player text | [V-EXEC C431] Version/lockfile and stable classifier are 1.0.0; dated changelog and release notes are prepared. README, contribution/security policy, limitations and all eleven Workshop descriptions state the supported build and unsigned-Windows limitation. Eight current GUI screenshots use the approved demo copy of the EVXP library. Future roadmap expansion is not a 1.0.0 inclusion promise. |
| Product acceptance | Accepted by the owner on 2026-10-29 (C437), using the existing tests and gameplay experience. Historical experiment notes are not new requests for acceptance. |
| Local checks | [V-EXEC C431] Locked sync and full checks pass: 2,140 Python tests (14 optional skips), 23 Rust tests, formatting, lint and strict typing. The full installed-game reference suite passes 13 tests; one opt-in layer check is skipped. The event expectation was corrected from 82 to 83 for the already adapted D009 diaspora gate; generator output is unchanged. |
| Languages and world output | [V-EXEC C431] All player-visible catalog keys/fingerprints and eleven Workshop texts pass the release checks against the installed game's official languages. The 1.0.0 exporter reproduces all **867** nonmetadata files of epoch 59, SHA-256 `23c0437734288ffa913061f627838855c97962185fe939da18b313ccb1bd9c85`; the frozen reference is unchanged. |
| Exact-source CI | The local hand-off `BUILD-INFO.json` binds the full candidate SHA to successful general and release workflow runs. The release workflow runs Linux and Windows checks, packages and self-tests both app variants, builds platform archives and validates the Windows packages on Windows. |
| Downloaded packages | The hand-off contains CI Windows standalone and Workshop/Proton ZIPs, Linux archive and Python sdist. Their embedded SHA256SUMS match; archive audits found no game assets or generated worlds. The Windows artifact contains only the two delivery ZIPs and checksum manifest. The complete source archive and Workshop text bundle are also present. |
| Installed candidate | [V-EXEC C435] Installed the 3,272-file Windows hub from the CI artifact with package/source verification and a passing isolated Wine self-test. The prior hub is retained at `.rnw-hub-backups/1.0.0-1793232100930439192`. The separately installed 878-file world remains a local candidate with both library entries; it is not part of a public archive. No EU5 launch or control. |
| VirusTotal | The exact launcher and native extension from the hand-off candidate were scanned. The manifest records each binary's SHA-256, size, report URL and per-engine totals. Timeouts and failed engines are unknown results, not clean results. These file scans do not cover archives or every dependency and are not a safety guarantee. |
| Game and platform limits | Owner observations and Windows 11 smoke C428 remain valid at their recorded versions. Known wrap, DLC completion, balance and multiplayer limits remain disclosed. macOS is not an offered package or a verified game route. These disclosed limits are accepted for 1.0.0 (C437). |
| Source/licences | [V-EXEC / SOURCE C431] Third-party notices and licences travel with the packages; no game assets or generated worlds are included. A 2026-10-29 check found the Steam Subscriber Agreement revision dated 2026-09-10 and Paradox's 2026-01-21 agreement; the owner confirms that the rules have been studied and accepts the audited hub distribution (C437). C267 retains the limits of the source interpretation, without imposing another approval process. Windows binaries remain unsigned and this is stated in player-facing text. |
| External publication | **Pending:** stable `v1.0.0` tag, GitHub Release and Workshop upload/download acceptance. CI uploads candidate artifacts only. No tag, release, account agreement or Workshop publication has been performed. |

The candidate packages, source, checksums and verification records are available
in the local `dist/release-1.0.0/` hand-off folder. Include its `BUILD-INFO.json`
manifest when handing off or publishing the package set. Keep generated worlds out of
public distributions. Product acceptance and terms review are complete (C437).
The remaining unchecked hand-off items track publication itself, not defects or
unmet preparation requirements.
