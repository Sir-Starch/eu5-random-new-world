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

- [ ] **Product gates:** P1 dependencies R9, R10, U1, N0–N5 and L1 are accepted as described in the [roadmap](roadmap.md). The 1.0.0 product is complete and validated in game, as required by ADR 0003.
- [ ] **Game compatibility:** record the exact EU5 version and Steam build tested. Recheck the map-contract fingerprint and game-facing behavior for that build; a matching `1.4.*` metadata value alone is not compatibility evidence ([AGENTS.md](../AGENTS.md), [claims ledger](research/claims-ledger.md); [INFERRED C18]).
- [ ] **Languages:** run the L1 release check against every official language shipped by the target game build. Every player-visible string has a translation, and each translation is current against its English source ([roadmap L1](roadmap.md)).
- [ ] **Legal and file audit:** review [legal notes](legal.md) against the current package, confirm third-party notices and licences are present, and audit source and binary archives for game assets and derived map data. Generated worlds remain local ([ADR 0009](adr/0009-hub-mod-with-generator.md)).
- [ ] **Windows and Workshop route:** the owner-run Windows 11 generator smoke passed (C428); finish the remaining trust checks in [ADR 0009](adr/0009-hub-mod-with-generator.md) and verify Workshop acceptance, or state the verified limits plainly in player-facing text. Before upload, recheck and accept the current Steam and EU5 terms and confirm the rights to every file included; the current source review leaves the scope for this item [UNKNOWN C267] ([legal notes](legal.md)).
- [ ] **Player text:** prepare release notes from the changelog. Keep the README as product documentation, not release notes. Remove internal bracketed notes from the [Workshop description](workshop-description.md), and verify every feature, game-build, installation, removal, warning, and support statement against the candidate.
- [ ] **Images:** the screenshots of the generator's window in `docs/images/` may be published (owner, 2026-10-24; [legal notes](legal.md)). Take them again on a demo library, with the platform's plain light style and without paths or hardware of the machine, whenever the window changes. Game files, textures and rasters stay out; any upload to the Workshop is an owner action (P1 in the [roadmap](roadmap.md)).
- [ ] **Version and reproducibility:** check `pyproject.toml`, `uv.lock`, generated mod metadata and run records use the same version. Choose the version from the whole release relative to the previous stable release, not per commit. Update output goldens when needed; if a world's mod changes outside `.metadata`, freeze the cycle's pending algorithm epoch and final reference world. Do not rewrite frozen epochs ([ADR 0003](adr/0003-versioning.md); [ADR 0010](adr/0010-layered-worlds-and-a-generator-of-its-own.md)).

## Candidate artifact gate

Build pre-tag artifacts with `workflow_dispatch`: `tag` is the intended numeric target (for example `v1.0.0`) and `commit` is the full candidate SHA. The tag need not exist yet. With `commit` empty, the workflow requires the actual tag; tag pushes use this mode too. Both paths validate the package version and clean exact checkout, run `make check`, and pass the resolved SHA to both builders. Fix a failed pre-tag candidate at a new SHA under the same target. After acceptance, tag exactly the reviewed commit and verify the tagged build before publication. Keep stable tags immutable. For that candidate, verify:

- [ ] CI is green on the release commit for the required Linux and Windows checks (P1). A run on another commit is not evidence for this candidate.
- [ ] The release workflow's tag check matches `pyproject.toml`; package self-tests and archive audits pass ([release workflow](../.github/workflows/release.yml), [`packaging/release.py`](../packaging/release.py)).
- [ ] The source archive and every platform archive are present, and the published SHA-256 files cover every archive being handed off. Verify each checksum against the downloaded candidate files.
- [ ] The candidate contains the correct third-party notices and no game assets, generated-world files, local logs, saves, or unapproved screenshots. Approved documentation images may travel with the source archive.
- [ ] Keep the workflow artifacts as a candidate until the maintainer accepts them. The workflow uploads build artifacts for review; it does not create a GitHub release or publish to the Workshop.

## GitHub release hand-off

The maintainer performs the external publication after accepting the candidate:

- [ ] Create the GitHub release for the reviewed version tag and attach the matching source archive, application archives, and their checksum files.
- [ ] Use the prepared release notes and link to the source tag. Do not add generated worlds or derived game files.
- [ ] Download the posted assets once and recheck their checksums against the candidate.

## Steam Workshop hand-off

Workshop publication is a separate owner action and is gated on the tested delivery route and current legal review:

- [ ] Upload only the hub mod and generator package. Never upload a generated world or a package containing derived vanilla map data.
- [ ] Use the reviewed Workshop description (`docs/workshop/<language>.bbcode`, one per language, pasted without its first `source:` line), preview image, and approved screenshots. Remove every editorial bracketed note before upload.
- [ ] Confirm the item is free, the required dependency notices travel with it, and the installation/removal instructions match the published build.
- [ ] Verify the Workshop page and downloaded item after publication. Record the item identifier and exact product/game versions in the project notes.

## Current readiness

Preparation date: **2026-10-28**. **RNW 1.0.0 / epoch 59** is a local release
candidate for **EU5 1.4.5 / Steam build 26211608**, including Across the Pillars
adaptation. Publication is pending. This section supersedes the 0.13.23 audit
(C430); historical game observations keep their original versions.

| Area | Evidence and remaining boundary |
|---|---|
| Product and player text | [V-EXEC C431] Version/lockfile and stable classifier set to 1.0.0; dated changelog and release notes prepared. README, contribution/security policy, limitations and all eleven Workshop descriptions agree on the supported build and unsigned-Windows limitation. Eight current GUI screenshots use a demo copy of the existing EVXP library. Future roadmap expansion is not a 1.0.0 inclusion promise. |
| Local checks | [V-EXEC C431] Locked sync and full checks pass: 2,140 Python tests (14 optional skips), 23 Rust tests, formatting, lint and strict typing. The local reference test’s event expectation is corrected from 82 to 83 for the already adapted D009 diaspora gate; generator output is unchanged. The full installed-game suite with reproduction passes 13 tests; one opt-in layer check is skipped. |
| Languages | [V-EXEC C431] All player-visible catalog keys and fingerprints pass, as do all eleven Workshop texts and their byte limits. Official languages are also checked against the installed 1.4.5 game, rather than assumed from a static list. |
| World reproduction | [V-EXEC C431] The 1.0.0 exporter reproduces all **867** nonmetadata files of epoch 59, digest `23c0437734288ffa913061f627838855c97962185fe939da18b313ccb1bd9c85`. The reference code and frozen digest stay unchanged. Product version/GUI wording do not consume another epoch. |
| Packages | [V-EXEC C431] Fresh Windows standalone/Workshop and native Linux packages are built locally, audited and self-tested. The hub’s installed copy and Windows CLI run under isolated Wine; this is not a new native Windows owner test. Source archive and final checksum/build manifests are prepared from the clean source commit. Do not use the old `dist/rnw_exp_hub` 0.13.1 folder. |
| Local installation | [V-EXEC C431] The 1.0.0 generator hub is installed through the verified updater. Previous 0.13.23 hub retained at `.rnw-hub-backups/0.13.23-1793224526723633799`. Installed a separate 878-file world candidate with both library entries, preserving 6,002 prior-world files and nine profile-root files. Exact preservation checks are in [INSTALLED](../experiments/INSTALLED.md). No EU5 launch or control. |
| VirusTotal | [SOURCE / V-EXEC C432] At the owner’s explicit request, configured the official MCP endpoint with OAuth and submitted only the two distributable project Windows binaries. Both analyses completed: zero malicious/suspicious, 71 undetected and four unsupported engines each. Exact report links are in the [release notes](releases/1.0.0.md#windows-binary-scans). This is not an archive-wide, dependency-wide, signing or universal safety claim. |
| Game/platform limits | Existing owner acceptance, Windows 11 smoke C428 and campaign evidence remain valid at their recorded versions. Known wrap, DLC completion, balance and multiplayer limits remain disclosed; no further game sitting is requested. macOS remains unverified and is not included in the local package set. |
| Source/licences | [V-EXEC / SOURCE C431] Third-party notices and texts travel with the packages; no game assets or generated worlds belong in public archives. Rechecked current source terms and corrected README redistribution wording to match the existing MPL. C267’s item-specific legal uncertainty remains a publication boundary, not a new legal clearance. |
| External publication | **Pending:** push and successful CI on the exact candidate commit, final stable tag/remote artifacts, GitHub release and Workshop upload/download acceptance. No such action is inferred from local checks or performed without explicit owner authorization. No code-signing route has been configured; the unsigned state is stated in player text. |

The locally prepared candidate, source commit, package hashes and verification
record are handed off together. The [release notes](releases/1.0.0.md) are ready
to reuse. Keep the stable tag uncreated until the exact candidate is accepted;
pre-tag CI can use its full commit SHA under the same 1.0.0 target.
